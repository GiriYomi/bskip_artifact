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

### Fix 2: Multiprocessing-Based Global Timeout (Thread-Safe)

**Problem with signals**: OpenEvolve runs evaluations in thread pool, but `signal.SIGALRM` only works in main thread
- Error: `ValueError: signal only works in main thread of the main interpreter`

**Solution**: Use `multiprocessing` to run evaluation in separate process

**Implementation**:
```python
import multiprocessing
from multiprocessing import Process, Queue

# Set spawn method for clean process start
multiprocessing.set_start_method('spawn', force=True)

def _run_in_process(program_path: str, result_queue: Queue, timeout: int):
    """Run evaluation in separate process"""
    try:
        result = _evaluate_internal(program_path)
        result_queue.put(('success', {
            'metrics': result.metrics,
            'artifacts': result.artifacts
        }))
    except Exception as e:
        result_queue.put(('error', str(e)))

def evaluate(program_path: str) -> EvaluationResult:
    """Main evaluate with multiprocessing timeout"""
    EVALUATOR_TIMEOUT = 570  # Slightly less than OpenEvolve's 600s
    
    result_queue = Queue()
    process = Process(target=_run_in_process, 
                     args=(program_path, result_queue, EVALUATOR_TIMEOUT))
    process.start()
    process.join(timeout=EVALUATOR_TIMEOUT)
    
    if process.is_alive():
        # Timeout - terminate forcefully
        process.terminate()
        process.join(timeout=5)
        if process.is_alive():
            process.kill()
        return EvaluationResult(
            metrics={"combined_score": -999},
            artifacts={"error": f"Timeout after {EVALUATOR_TIMEOUT}s"}
        )
    
    # Get result from queue
    if not result_queue.empty():
        status, data = result_queue.get()
        if status == 'success':
            return EvaluationResult(metrics=data['metrics'], 
                                   artifacts=data['artifacts'])
    ...
```

**Benefits**:
- ✅ Works from any thread (no signal restrictions)
- ✅ Can forcefully terminate hung processes
- ✅ Clean inter-process communication via Queue
- ✅ Proper cleanup with terminate/kill fallback
- ✅ Compatible with OpenEvolve's thread pool

## Timeout Architecture

```
┌─────────────────────────────────────────────────┐
│ OpenEvolve: evaluator.timeout = 600s            │
│   ├── Runs in thread pool (asyncio executor)   │
│   └── asyncio.wait_for(timeout=600)            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ evaluate(): Process-based timeout = 570s        │
│   ├── Create multiprocessing.Process            │
│   ├── Run _evaluate_internal() in process      │
│   │     ├── Compile & test (~30s)               │
│   │     ├── Run benchmark 1                     │
│   │     │   └── subprocess.run(timeout=280s)    │
│   │     ├── Run benchmark 2                     │
│   │     │   └── subprocess.run(timeout=280s)    │
│   │     └── Calculate metrics (~1s)             │
│   ├── process.join(timeout=570)                │
│   │                                              │
│   └── If timeout:                               │
│       ├── process.terminate()                   │
│       ├── process.kill() if needed              │
│       └── Return combined_score=-999            │
└─────────────────────────────────────────────────┘
```

## Timeout Hierarchy

| Level | Timeout | Mechanism | Purpose |
|-------|---------|-----------|---------|
| **OpenEvolve** | 600s | asyncio.wait_for | Framework timeout |
| **evaluate()** | 570s | Process.join(timeout) | Global evaluator timeout |
| **_run_benchmark()** | 280s | subprocess.run(timeout) | Individual benchmark timeout |

**Why this works**:
1. Each benchmark has 280s to complete (subprocess.run timeout)
2. Two benchmarks = 560s total (fits within 570s process timeout)
3. If ANY step hangs, process.join(570s) times out
4. Process can be forcefully terminated (terminate/kill)
5. OpenEvolve's 600s asyncio timeout is the final safety net
6. 10-30 second buffers allow proper cleanup
7. **Works from threads** - no signal restrictions!

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

### Unix/Linux/macOS (✅ Fully Supported):
- Uses `multiprocessing` for timeout (works from any thread)
- Process can be forcefully terminated
- Fully compatible with OpenEvolve's thread pool

### Windows (✅ Supported):
- `multiprocessing` works on Windows with 'spawn' start method
- Process termination supported
- Fully compatible

### Why Multiprocessing Instead of Signals:

**Problem with signal.SIGALRM**:
```python
# This FAILS when called from thread pool:
old_handler = signal.signal(signal.SIGALRM, timeout_handler)
# ValueError: signal only works in main thread of the main interpreter
```

**Solution with multiprocessing**:
```python
# This WORKS from any thread:
process = Process(target=_run_in_process, args=(...))
process.start()
process.join(timeout=570)
if process.is_alive():
    process.terminate()  # Works from any thread!
```

### Key Advantage:
- ✅ **Thread-safe**: Works when OpenEvolve runs evaluations in thread pool
- ✅ **Cross-platform**: Works on Linux, macOS, and Windows
- ✅ **Forceful termination**: Can kill hung processes
- ✅ **Clean IPC**: Uses Queue for result passing

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
2. Added **multiprocessing-based** global timeout (thread-safe!)

✅ **Timeout enforcement at 3 levels**:
1. Subprocess level (280s per benchmark, 2 benchmarks = 560s)
2. Evaluator level (570s total, using multiprocessing)
3. OpenEvolve level (600s framework timeout)

✅ **Thread-safe implementation**:
- Uses `multiprocessing.Process` instead of signals
- Works correctly when called from OpenEvolve's thread pool
- No "signal only works in main thread" errors

✅ **Graceful failure**:
- Timeouts return `combined_score=-999`
- Clear error messages in artifacts
- Proper cleanup of resources (terminate/kill processes)

**Result**: The evaluator will **never** enter an infinite loop and will **always** respect OpenEvolve's timeout settings, even when running in thread pool.

---

**Date Fixed**: 2025-10-10 (Updated: 2025-10-14)  
**Issue**: Infinite loops from blocking I/O and thread pool incompatibility  
**Solution**: subprocess.run() + multiprocessing.Process timeout wrapper

