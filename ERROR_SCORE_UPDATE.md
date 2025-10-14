# Error Score Update: 0.0 → -999

## Change Summary

All error and timeout cases now return `combined_score: -999` instead of `0.0` to clearly distinguish errors from actual performance measurements.

## Rationale

### Problem with 0.0:
- **Confusing**: 0.0 could mean "exactly at baseline performance" (0% improvement)
- **Ambiguous**: Small negative scores like -1% or -2% indicate slight regression, which is still meaningful data
- **Not filterable**: Hard to distinguish errors from real measurements programmatically

### Solution with -999:
- **Clear signal**: -999 is an obviously invalid performance score
- **Easy filtering**: `if score == -999: handle_error()`
- **Preserves meaningful negatives**: Small negative scores (-5% to -1%) still represent actual performance regressions

## Changed Cases

All 7 error/timeout cases now return `combined_score: -999`:

### 1. Compilation/Test Failures (Line 317)
```python
# Candidate failed to compile or pass correctness tests
return EvaluationResult(metrics={"combined_score": -999}, 
                       artifacts={"error": f"Candidate failed early: {e}"})
```

### 2. Candidate Run 1 Failed (Line 327)
```python
# First benchmark run failed (non-zero exit code)
return EvaluationResult(metrics={"combined_score": -999}, 
                       artifacts={"error": f"Candidate run 1 failed: {stderr}"})
```

### 3. Candidate Run 1 Exception (Line 335)
```python
# First benchmark run threw exception
return EvaluationResult(metrics={"combined_score": -999}, 
                       artifacts={"error": f"Candidate benchmark 1 failed: {e}"})
```

### 4. Candidate Run 2 Failed (Line 345)
```python
# Second benchmark run failed (non-zero exit code)
return EvaluationResult(metrics={"combined_score": -999}, 
                       artifacts={"error": f"Candidate run 2 failed: {stderr}"})
```

### 5. Candidate Run 2 Exception (Line 353)
```python
# Second benchmark run threw exception
return EvaluationResult(metrics={"combined_score": -999}, 
                       artifacts={"error": f"Candidate benchmark 2 failed: {e}"})
```

### 6. Evaluation Timeout (Line 433)
```python
# Entire evaluation timed out (580s global timeout)
return EvaluationResult(metrics={"combined_score": -999}, 
                       artifacts={"error": f"Evaluation timeout after {EVALUATOR_TIMEOUT}s"})
```

### 7. General Exception (Line 442)
```python
# Unexpected exception during evaluation
return EvaluationResult(metrics={"combined_score": -999}, 
                       artifacts={"error": str(e)})
```

## Score Interpretation

| Score Range | Meaning |
|-------------|---------|
| **-999** | Error/Timeout - Invalid measurement |
| **< -10** | Severe regression (>10% slower) |
| **-10 to -1** | Minor regression (1-10% slower) |
| **-1 to 0** | Slight regression (<1% slower) |
| **0** | Exactly at baseline |
| **0 to 1** | Slight improvement (<1% faster) |
| **1 to 10** | Good improvement (1-10% faster) |
| **> 10** | Excellent improvement (>10% faster) |

## Usage in Analysis

### Filtering Errors
```python
# Skip error cases in analysis
valid_results = [r for r in results if r.metrics.get('combined_score') != -999]

# Count errors
error_count = sum(1 for r in results if r.metrics.get('combined_score') == -999)
```

### Logging
```python
if result.metrics.get('combined_score') == -999:
    print(f"ERROR: {result.artifacts.get('error')}")
else:
    print(f"Score: {result.metrics.get('combined_score'):.2f}%")
```

### Statistics
```python
# Only calculate stats on valid results
valid_scores = [r.metrics['combined_score'] for r in results 
                if r.metrics.get('combined_score') != -999]

if valid_scores:
    mean_improvement = statistics.mean(valid_scores)
    print(f"Average improvement: {mean_improvement:.2f}%")
else:
    print("No valid results")
```

## OpenEvolve Integration

OpenEvolve's evolution loop will:
1. **Ignore -999 scores** when selecting top performers
2. **Not propagate errors** to next generation
3. **Log errors** for debugging but don't penalize evolution

Example from database selection:
```python
def select_top_programs(population):
    # Filter out errors
    valid_programs = [p for p in population 
                     if p.metrics.get('combined_score') != -999]
    
    # Sort by score
    return sorted(valid_programs, 
                 key=lambda p: p.metrics['combined_score'], 
                 reverse=True)[:k]
```

## Benefits

1. ✅ **Clear error detection**: Easy to identify failed evaluations
2. ✅ **Preserved semantics**: Negative scores still mean regression
3. ✅ **Better analytics**: Can separate errors from performance data
4. ✅ **Simpler filtering**: `!= -999` to get valid results
5. ✅ **Debugging friendly**: Obvious sentinel value

## Configuration

The error score is defined inline in each error return. To change it globally, you would need to define a constant:

```python
# At top of evaluator.py
ERROR_SCORE = -999

# Then use in all error returns
return EvaluationResult(metrics={"combined_score": ERROR_SCORE}, ...)
```

Current implementation uses literal `-999` for clarity and to avoid another constant.

---

**Updated**: 2025-10-10  
**Error Score**: -999 (was 0.0)  
**Reason**: Clear separation of errors from performance measurements

