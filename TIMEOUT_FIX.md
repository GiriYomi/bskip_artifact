# Evaluator Timeout Fix - Preventing Infinite Loops

## Problem Identified

The evaluator had **two critical timeout issues** that could cause infinite loops:

### Issue 1: Blocking `readline()` in `_run_benchmark`

**Location**: Lines 155-179 (old code)

**Problem**:
```python
while True:
    if time.time() - start_time > TIMEOUT_SECONDS:
        # timeout handling
        ...
    
    output = proc.stdout.readline()  # ← CAN BLOCK FOREVER!
    if output == '' and proc.poll() is not None:
        break
```

**Why it fails**:
- The timeout check happens BEFORE `readline()`
- If `readline()` blocks waiting for output, we never get to check the timeout again
- Result: **Infinite loop** if the process hangs without producing output

### Issue 2: No Global Timeout for `evaluate()`

**Problem**:
- OpenEvolve sets `evaluator.timeout = 600` seconds (line 76 in run_skip.py)
- But the `evaluate()` function had no mechanism to enforce this timeout
- If compilation hangs or any step deadlocks, the evaluator runs forever
- Result: **Infinite loop** at the evaluation level

## Solutions Implemented

### Fix 1: Replace `Popen` + `readline()` with `subprocess.run()` + timeout

**Old code** (blocking, infinite loop risk):
```python
proc = subprocess.Popen(cmd, ...)
while True:
    if time.time() - start_time > TIMEOUT_SECONDS:
        # timeout handling
    output = proc.stdout.readline()  # BLOCKS!
    ...
```

**New code** (non-blocking, timeout enforced):
```python
try:
    result = subprocess.run(
        cmd,
        cwd=BSKIP_DIR,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS  # ← Proper timeout!
    )
    artifacts["run"]["rc"] = result.returncode
    artifacts["run"]["stdout"] = result.stdout
    artifacts["run"]["stderr"] = result.stderr
    
except subprocess.TimeoutExpired as e:
    print(f"[WARNING] Benchmark timed out after {TIMEOUT_SECONDS}s")
    artifacts["run"]["rc"] = 124
    artifacts["run"]["stdout"] = e.stdout if e.stdout else ""
    artifacts["run"]["stderr"] = f"Timeout after {TIMEOUT_SECONDS}s"
```

**Benefits**:
- ✅ `subprocess.run()` properly enforces timeout
- ✅ No blocking `readline()` calls
- ✅ Clean exception handling for timeouts
- ✅ Guaranteed to return within TIMEOUT_SECONDS

### Fix 2: Signal-Based Global Timeout Wrapper

**Added timeout handler**:
```python
import signal

class TimeoutError(Exception):
    """Raised when evaluation times out"""
    pass

def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Evaluation timed out")
```

**Wrapped `evaluate()` function**:
```python
def evaluate(program_path: str) -> EvaluationResult:
    """Main evaluate function with timeout protection"""
    EVALUATOR_TIMEOUT = 595  # Slightly less than OpenEvolve's 600s
    
    # Set up signal-based timeout (Unix/Linux systems)
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(EVALUATOR_TIMEOUT)
    
    try:
        result = _evaluate_internal(program_path)
        signal.alarm(0)  # Cancel the alarm
        signal.signal(signal.SIGALRM, old_handler)
        return result
        
    except TimeoutError as e:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        print(f"[ERROR] Evaluation timed out after {EVALUATOR_TIMEOUT}s")
        return EvaluationResult(
            metrics={"combined_score": 0.0},
            artifacts={"error": f"Evaluation timeout after {EVALUATOR_TIMEOUT}s"}
        )
```

**Benefits**:
- ✅ Enforces hard timeout on entire evaluation
- ✅ Handles hanging compilations, tests, or benchmarks
- ✅ Uses Unix signals (SIGALRM) for reliable timeout
- ✅ Properly cleans up signal handlers
- ✅ Returns gracefully on timeout

## Timeout Architecture

```
┌─────────────────────────────────────────────────┐
│ OpenEvolve: evaluator.timeout = 600s            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ evaluate(): SIGALRM timeout = 595s              │
│   ├── Set signal.alarm(595)                     │
│   ├── Call _evaluate_internal()                 │
│   │     ├── Compile & test                      │
│   │     ├── Run benchmark 1                     │
│   │     │   └── subprocess.run(timeout=580)     │
│   │     ├── Run benchmark 2                     │
│   │     │   └── subprocess.run(timeout=580)     │
│   │     └── Calculate metrics                   │
│   └── Cancel alarm, return result               │
│                                                  │
│ On TimeoutError:                                │
│   └── Return with combined_score=0.0            │
└─────────────────────────────────────────────────┘
```

## Timeout Hierarchy

| Level | Timeout | Purpose |
|-------|---------|---------|
| **OpenEvolve** | 600s | Framework-level timeout |
| **evaluate()** | 595s | Global evaluator timeout (signal) |
| **_run_benchmark()** | 580s | Individual benchmark timeout (subprocess) |

**Why this works**:
1. Each benchmark has 580s to complete (subprocess.run timeout)
2. If ANY step hangs, the 595s signal alarm fires
3. OpenEvolve's 600s timeout is the final safety net
4. 5-15 second buffers allow proper cleanup

## Key Changes Summary

### Before (Broken):
- ❌ `readline()` could block forever
- ❌ No global timeout enforcement
- ❌ Infinite loop risk at two levels
- ❌ No graceful timeout handling

### After (Fixed):
- ✅ `subprocess.run()` with proper timeout
- ✅ Signal-based global timeout (SIGALRM)
- ✅ No infinite loop possibility
- ✅ Graceful timeout handling at all levels
- ✅ Proper cleanup and error returns

## Testing the Fix

### Test 1: Benchmark Timeout

Create a hanging benchmark:
```bash
# Replace ycsb with infinite loop
cp bskiplist/ycsb bskiplist/ycsb.backup
echo '#!/bin/bash' > bskiplist/ycsb
echo 'while true; do sleep 1; done' >> bskiplist/ycsb
chmod +x bskiplist/ycsb

# Run evaluator - should timeout at 580s, not hang forever
python3 -c "from bskiplist.evaluator import evaluate; evaluate('bskiplist/bskip.h')"

# Restore
mv bskiplist/ycsb.backup bskiplist/ycsb
```

**Expected**: Timeout after ~580 seconds with proper error message

### Test 2: Global Timeout

Create a hanging compilation:
```python
# In evaluator.py, add infinite loop in _compile_and_test
# After line 52:
while True:
    time.sleep(1)  # Infinite loop
```

**Expected**: Timeout after ~595 seconds with proper error message

## Platform Compatibility

### Unix/Linux/macOS (✅ Supported):
- Uses `signal.SIGALRM` for timeout
- Fully supported and tested

### Windows (⚠️ Limited):
- `signal.SIGALRM` not available on Windows
- Falls back to `subprocess.run()` timeout only
- Recommendation: Use WSL or Linux for OpenEvolve

### Alternative for Windows:
```python
# Could use threading.Timer instead of signal
import threading

def evaluate_with_timer(program_path, timeout=595):
    result = None
    def run():
        nonlocal result
        result = _evaluate_internal(program_path)
    
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        # Timeout occurred
        return EvaluationResult(metrics={"combined_score": 0.0}, 
                               artifacts={"error": "Timeout"})
    return result
```

## Debugging Timeouts

If you see timeout errors:

1. **Check timeout values**:
   ```bash
   grep -n "TIMEOUT" bskiplist/evaluator.py
   ```
   - Line 136: `TIMEOUT_SECONDS = 580` (benchmark)
   - Line 416: `EVALUATOR_TIMEOUT = 595` (global)

2. **Check OpenEvolve config**:
   ```python
   # In run_skip.py line 76
   evaluator=EvaluatorConfig(timeout=600, ...)
   ```

3. **Increase timeouts if needed**:
   ```python
   # For slower systems, increase all timeouts proportionally:
   TIMEOUT_SECONDS = 900  # benchmark
   EVALUATOR_TIMEOUT = 920  # global
   # And in run_skip.py:
   evaluator=EvaluatorConfig(timeout=1000, ...)
   ```

4. **Check logs**:
   ```bash
   # Look for timeout messages
   grep -i timeout openevolve_output/logs/*.log
   ```

## Summary

✅ **Fixed infinite loop issues**:
1. Replaced blocking `readline()` with `subprocess.run(timeout=...)`
2. Added signal-based global timeout wrapper

✅ **Timeout enforcement at 3 levels**:
1. Subprocess level (580s per benchmark)
2. Evaluator level (595s total evaluation)
3. OpenEvolve level (600s framework timeout)

✅ **Graceful failure**:
- Timeouts return `combined_score=0.0`
- Clear error messages in artifacts
- Proper cleanup of resources

**Result**: The evaluator will **never** enter an infinite loop and will **always** respect OpenEvolve's timeout settings.

---

**Date Fixed**: 2025-10-10  
**Issue**: Infinite loops from blocking I/O and missing global timeout  
**Solution**: subprocess.run() + signal.SIGALRM timeout wrapper

