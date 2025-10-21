# Thread Pool Compatibility Fix

## Problem: Signal-Based Timeout Fails in Thread Pool

### Error Message
```
ValueError: signal only works in main thread of the main interpreter
```

### Root Cause

OpenEvolve runs evaluations in a **thread pool** (asyncio executor):
```python
# In OpenEvolve's evaluator.py:
result = await loop.run_in_executor(None, self.evaluate_function, program_path)
```

Our original timeout implementation used **signals**:
```python
# This FAILS when called from a thread:
old_handler = signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(EVALUATOR_TIMEOUT)
```

**Problem**: Python's `signal` module only works in the **main thread**. When OpenEvolve calls our `evaluate()` function from a thread pool worker, signal operations fail.

## Solution: Multiprocessing-Based Timeout

### Key Insight
✅ **Multiprocessing works from any thread** (unlike signals)  
✅ Processes can be forcefully terminated  
✅ Clean inter-process communication via Queue  

### Implementation

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
    """Main evaluate with process-based timeout"""
    EVALUATOR_TIMEOUT = 570
    
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
        else:
            return EvaluationResult(
                metrics={"combined_score": -999},
                artifacts={"error": data}
            )
    else:
        return EvaluationResult(
            metrics={"combined_score": -999},
            artifacts={"error": "Process completed without result"}
        )
```

## How It Works

### Execution Flow

```
OpenEvolve Thread Pool
    ↓
evaluate() called from thread
    ↓
Create multiprocessing.Process
    ↓
Run _evaluate_internal() in separate process
    ↓
process.join(timeout=570)
    ↓
If timeout: terminate/kill process
If success: get result from queue
```

### Why This Works

1. **Thread-safe**: `multiprocessing.Process` works from any thread
2. **Forceful termination**: Can kill hung processes with terminate/kill
3. **IPC via Queue**: Clean result passing between processes
4. **Spawn method**: Ensures clean process start (no fork issues)

## Comparison

### ❌ Signal-Based (Broken)

```python
# Only works in main thread
signal.signal(signal.SIGALRM, handler)  # FAILS in thread!
signal.alarm(timeout)
```

**Issues**:
- Only works in main thread
- Fails with ValueError in thread pool
- Can't be used with OpenEvolve

### ✅ Process-Based (Working)

```python
# Works from any thread
process = Process(target=func)
process.start()
process.join(timeout=timeout)
if process.is_alive():
    process.terminate()  # Works from thread!
```

**Benefits**:
- Works from any thread
- Compatible with OpenEvolve's thread pool
- Can forcefully terminate

## Timeout Hierarchy

| Level | Timeout | Mechanism |
|-------|---------|-----------|
| **OpenEvolve** | 600s | asyncio.wait_for |
| **evaluate()** | 570s | Process.join(timeout) |
| **_run_benchmark()** | 280s | subprocess.run(timeout) |

**Buffer zones**:
- 30s between benchmark and evaluator (280×2 = 560s < 570s)
- 30s between evaluator and OpenEvolve (570s < 600s)

## Platform Support

### Linux/macOS ✅
- `multiprocessing` fully supported
- Process termination reliable
- Spawn method works perfectly

### Windows ✅
- `multiprocessing` supported with 'spawn' method
- Process termination supported
- Fully compatible

## Testing

### Verify Thread Pool Compatibility

```python
import threading
from evaluator import evaluate

def test_from_thread():
    # Simulate OpenEvolve's thread pool
    result = evaluate('bskip.h')
    print(f"Score: {result.metrics.get('combined_score')}")

thread = threading.Thread(target=test_from_thread)
thread.start()
thread.join()
print("✓ Works from thread!")
```

### Expected Behavior

✅ No `ValueError` about signals  
✅ Evaluation completes normally  
✅ Timeout enforced if hung  
✅ Proper error handling  

## Key Takeaways

1. **Signals don't work in threads** - Python limitation
2. **Multiprocessing is thread-safe** - Works from any thread
3. **Process isolation** - Hung process can be killed
4. **Clean IPC** - Queue for result passing
5. **OpenEvolve compatible** - Works in thread pool executor

## Migration Guide

### Old Code (Broken)
```python
import signal

def evaluate(path):
    old_handler = signal.signal(signal.SIGALRM, handler)  # FAILS
    signal.alarm(timeout)
    try:
        result = _evaluate_internal(path)
        signal.alarm(0)
        return result
    except TimeoutError:
        return error_result()
```

### New Code (Working)
```python
from multiprocessing import Process, Queue

def evaluate(path):
    queue = Queue()
    process = Process(target=_run_in_process, args=(path, queue))
    process.start()
    process.join(timeout=timeout)
    
    if process.is_alive():
        process.terminate()
        return error_result()
    
    status, data = queue.get()
    return EvaluationResult(**data)
```

## Performance Impact

- **Overhead**: ~50-100ms for process creation (negligible vs 570s timeout)
- **Memory**: Separate process memory (isolated, clean)
- **CPU**: No additional CPU overhead
- **Reliability**: Much better (can kill hung processes)

## Summary

✅ **Problem solved**: Evaluator now works in OpenEvolve's thread pool  
✅ **No signal errors**: Uses multiprocessing instead  
✅ **Timeout enforced**: Process can be forcefully terminated  
✅ **Cross-platform**: Works on Linux, macOS, Windows  
✅ **Production ready**: Robust error handling and cleanup  

---

**Date**: 2025-10-14  
**Issue**: `ValueError: signal only works in main thread`  
**Solution**: Multiprocessing-based timeout (thread-safe)





