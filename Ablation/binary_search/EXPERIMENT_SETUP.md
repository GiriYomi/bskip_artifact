# Binary Search Ablation Experiment Setup

## Purpose

Isolate and measure the performance impact of using binary search (O(log n)) vs linear search (O(n)) within B-Skiplist nodes.

## The Single Variable

**Only change**: The `BINARY_SEARCH` preprocessor define

| Version | BINARY_SEARCH | Search Method | File |
|---------|---------------|---------------|------|
| **Baseline** | 0 | Linear scan | `bskip_baseline_linear.h` |
| **Binary Only** | 1 | Binary search | `bskip_with_binary_search.h` |
| **Best Program** | 0 (linear!) | Linear scan + other opts | `best_program.h` |

## Code Difference

The change affects the `find_key()` method in `BSkipNodeLeaf`:

### Baseline (BINARY_SEARCH=0)
```cpp
uint32_t find_key(K k) {
    return find_index_linear(k);
}

uint32_t find_index_linear(K k) {
    for (uint32_t i = 0; i < n; ++i) {
        K key = blind_read_key(i);
        if (key == k) return i;
        if (key > k) return (i == 0) ? 0 : (i - 1);
    }
    return n - 1;
}
```

### Binary Search (BINARY_SEARCH=1)
```cpp
uint32_t find_key(K k) {
    return find_index_binary(k);
}

uint32_t find_index_binary(K k) {
    uint32_t left = 0;
    uint32_t right = num_elts - 1;
    while (left <= right) {
        int mid = left + (right - left) / 2;
        if (blind_read_key(mid) == k) {
            left = mid;
            break;
        }
        else if (blind_read_key(mid) < k) {
            left = mid + 1;
        }
        else {
            if (mid == 0) break;
            right = mid - 1;
        }
    }
    // ... adjust and return
}
```

## Why This Matters

**Theoretical Complexity:**
- Linear: O(n) where n ≤ 1024
- Binary: O(log n) = O(10) for n=1024

**But in practice:**
- Linear benefits from sequential memory access
- Binary has branch mispredictions and random access

## Test Methodology

```
For each version:
    1. Copy test file → bskiplist/bskip.h
    2. make clean && make -j
    3. Run YCSB benchmark 3 times
    4. Calculate average throughput
    
Compare:
    - Baseline vs Binary → Impact of the change
    - Baseline vs Best → Total possible improvement
    - Calculate contribution percentage
```

## Expected Outcomes

Based on existing analysis (ABLATION_ANALYSIS.md), we expect:

1. **Binary search provides NO benefit** (-0.1% to -0.5%)
2. **May actually hurt performance** due to:
   - Branch misprediction penalties
   - Cache miss penalties
   - Prefetcher disruption

3. **Best program improves ~5%** through OTHER optimizations

## Hardware Context

Modern CPUs have:
- **Large L1 caches** (32-64 KB)
- **Smart prefetchers** that detect sequential patterns
- **Branch predictors** that work well for linear scans
- **Out-of-order execution** that helps with sequential operations

This makes linear search surprisingly competitive even for large arrays.

## Algorithmic Insight

This is a classic example of how **micro-architecture matters more than asymptotic complexity** for:
- Small to medium n (< 1000)
- Modern CPU architectures
- Cache-friendly data structures

## Files in This Directory

- `bskip_baseline_linear.h` - BINARY_SEARCH=0
- `bskip_with_binary_search.h` - BINARY_SEARCH=1  
- `run_ablation_experiment.py` - Automated test script
- `binary_search_ablation_results.json` - Results (generated)
- `ABLATION_ANALYSIS.md` - Previous analysis with results
- `README.md` - Overview
- `QUICK_START.md` - Quick instructions
- `EXPERIMENT_SETUP.md` - This file

## Running

```bash
cd /home/yomi/0Projects/bskip_artifact/Ablation/binary_search
./run_ablation_experiment.py
```

## Analysis Questions

After running:
1. Is binary search faster or slower?
2. By how much (absolute and percentage)?
3. Does this match theoretical expectations?
4. What does this tell us about optimization on modern CPUs?

## Learning Objectives

- **Profile-guided optimization** > theoretical complexity
- **Measure, don't assume** performance characteristics
- **Modern CPUs** favor predictable, sequential patterns
- **Ablation studies** reveal surprising results

