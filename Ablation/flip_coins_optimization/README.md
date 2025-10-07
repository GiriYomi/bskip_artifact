# Ablation Study: flip_coins Optimization

## Overview

This experiment measures the **isolated performance impact** of the `flip_coins` optimization discovered by OpenEvolve's evolutionary search.

## What Changed?

The `flip_coins` function determines the height/level of nodes in the B-Skiplist. OpenEvolve replaced the original adaptive implementation with a power-of-two optimized version.

### Original Version (Adaptive Density-Based)
```cpp
// Adaptive probabilistic height selection with thread-local density hints
uint32_t flip_coins(K k) {
    // Hash-based baseline
    size_t h = std::hash<K>{}(k);
    uint64_t flip = h % traits::p;
    while (flip == 0) {
        result++;
        h /= traits::p;
        flip = h % traits::p;
    }
    
    // Apply density-based bias
    // If recent leaf is dense, promote more aggressively
    // to reduce future contention/splits
    static thread_local BSkipNode<traits>* tl_last_leaf[MAX_HEIGHT];
    double bias = 0.0;
    if (leaf density > 0.80) bias = 1.0;
    else if (leaf density > 0.60) bias = 0.5;
    
    if (bias > 0.0) result = min(result + 1, MAX_HEIGHT - 1);
    
    return result;
}
```

### Evolved Version (Power-of-Two Optimized)
```cpp
// Fast, mathematically-equivalent height selection for power-of-two p
uint32_t flip_coins(K k) {
    size_t h = std::hash<K>{}(k);
    
    // If p is power-of-two, use fast bit-counting intrinsic
    if constexpr ((traits::p & (traits::p - 1)) == 0) {
        const unsigned lg = __builtin_ctz((unsigned)traits::p);
        if (h == 0) {
            result = MAX_HEIGHT - 1;
        } else {
            unsigned tz = __builtin_ctzll((unsigned long long)h);
            result = tz / lg;
            if (result > MAX_HEIGHT - 1) result = MAX_HEIGHT - 1;
        }
    } else {
        // Fallback: classic base-p digit counting
        // (same as original without density bias)
    }
    
    return result;
}
```

## Key Differences

| Aspect | Original | Evolved |
|--------|----------|---------|
| **Algorithm** | Loop-based digit counting | Bit intrinsic (`__builtin_ctzll`) |
| **Complexity** | O(log n) loop iterations | O(1) CPU instruction |
| **Adaptivity** | Density-based bias | None - purely deterministic |
| **Thread-local state** | Yes (density hints) | No |
| **Power-of-two optimization** | No | Yes (fast path) |

## Why This Matters

This is the **ONLY** change between the original `bskip.h` and the evolved `best_program.h`. This makes it a **perfect ablation study** because:

1. ✅ Single variable changed
2. ✅ No confounding factors
3. ✅ Direct causal attribution
4. ✅ Clear performance delta

## Expected Performance Impact

### Hypothesis

The evolved version should be **faster** because:
1. **CPU intrinsics** (`__builtin_ctzll`) are single-cycle instructions
2. **No loops** - constant time instead of O(log n)
3. **No thread-local access** - simpler memory model
4. **Fewer branches** - better for CPU pipeline

However, the original's **adaptive density bias** might help in certain workloads by reducing future splits.

### Counter-hypothesis

The original might perform better if:
- The density-based bias significantly reduces node splits
- The adaptive behavior helps with non-uniform workloads
- The loop overhead is negligible compared to other operations

## How to Run

### Quick Start
```bash
cd /Users/girigiri_yomi/Udel_Proj/bskip_artifact/Ablation/flip_coins_optimization
python3 run_flip_coins_ablation.py
```

### What It Does
1. Backs up original `bskip.h`
2. Tests **Original Baseline** (3 runs)
3. Tests **Best Program** (3 runs)
4. Compares performance metrics
5. Restores original `bskip.h`
6. Saves results to JSON

### Requirements
- Compiled `ycsb` binary
- YCSB workload files in `bskiplist/data/uniform/`
- Python 3.6+

## Results Interpretation

The script will output:

```
Performance Comparison:
==============================================================
Metric                  | Baseline      | Best Program  | Change
--------------------------------------------------------------
Load Throughput         | X.XXXX ops/μs | X.XXXX ops/μs | +XX.XX%
Run Throughput          | X.XXXX ops/μs | X.XXXX ops/μs | +XX.XX%
Combined Score          | X.XXXX ops/μs | X.XXXX ops/μs | +XX.XX%
==============================================================

Key Findings:
The flip_coins optimization (power-of-two fast path) provides:
  • Load phase: +X.XX% improvement
  • Run phase:  +X.XX% improvement
  • Overall:    +X.XX% improvement
```

### Metrics Explained

- **Load Throughput**: Insert operations during initial loading
- **Run Throughput**: Mixed read/write operations during queries
- **Combined Score**: Average of load and run
- **Change %**: Percentage improvement (positive = faster)

## Statistical Considerations

- **3 runs per version**: Balances speed and reliability
- **5-second sleep**: Reduces thermal throttling effects
- **Median throughput**: Reported by benchmark (reduces outlier impact)
- **Checksum validation**: Ensures correctness

## Relation to OpenEvolve

This experiment validates OpenEvolve's evolutionary search results:

- **OpenEvolve found**: This optimization through automated search
- **This experiment measures**: The actual performance impact
- **Validates**: Whether the evolution was beneficial

## Files

```
flip_coins_optimization/
├── README.md                        ← You are here
├── run_flip_coins_ablation.py       ← Automated test script
├── flip_coins_ablation_results.json ← Results (after running)
└── ANALYSIS.md                      ← Detailed results analysis (after running)
```

## Next Steps

After running:
1. Review `flip_coins_ablation_results.json`
2. Compare with OpenEvolve's reported improvements
3. Determine if the optimization should be adopted
4. Document findings in `ANALYSIS.md`

## Questions Answered

- ✅ Is the power-of-two optimization actually faster?
- ✅ How much performance gain does it provide?
- ✅ Is adaptive density bias helpful or harmful?
- ✅ Is the code simpler or more complex?

## Limitations

- Tests only YCSB-A (100% reads) workload
- Single hardware configuration
- May not represent all use cases
- No stress testing with extreme contention

## Related Experiments

- `binary_search/` - Binary vs linear search within nodes
- `adaptive_split/` - Adaptive node splitting impact

---

**Last Updated**: 2025-10-07  
**Status**: Ready to run  
**Expected Runtime**: ~5-10 minutes

