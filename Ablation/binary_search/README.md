# Binary Search Within Nodes Ablation Experiment

## Overview

This ablation experiment isolates the performance impact of using **binary search vs linear search within nodes** in the B-Skiplist implementation.

## What is Binary Search Within Nodes?

B-Skiplist nodes can contain up to `MAX_KEYS` (default 1024) elements. When searching for a key within a node, there are two strategies:

1. **Linear Search** (BINARY_SEARCH=0): Scan elements sequentially from left to right
2. **Binary Search** (BINARY_SEARCH=1): Use binary search algorithm within the node

## The Code Change

This experiment tests the impact of a single preprocessor define:

### Baseline (Linear Search)
```cpp
#define BINARY_SEARCH 0

uint32_t find_key(K k) {
    return find_index_linear(k);  // O(n) within node
}
```

### With Binary Search
```cpp
#define BINARY_SEARCH 1

uint32_t find_key(K k) {
    return find_index_binary(k);  // O(log n) within node
}
```

## Why Linear Might Be Better

Despite binary search being O(log n), linear search can be faster for modern CPUs because:

1. **Cache Locality**: Sequential memory access is cache-friendly
2. **Branch Prediction**: Modern CPUs predict linear scan branches well
3. **Prefetching**: Hardware prefetchers work better with sequential access
4. **Small N**: For typical node sizes, the constant factors matter more

## Test Configurations

1. **Baseline**: `BINARY_SEARCH=0` - Linear search within nodes (`bskip_baseline_linear.h`)
2. **Binary Only**: `BINARY_SEARCH=1` - Binary search within nodes (`bskip_with_binary_search.h`)
3. **Best Program**: OpenEvolve optimized with all features (`best_program.h`)

## Running the Experiment

```bash
cd /home/yomi/0Projects/bskip_artifact/Ablation/binary_search
chmod +x run_ablation_experiment.py
./run_ablation_experiment.py
```

The script will:
1. Build each version
2. Run YCSB workload A with uniform distribution
3. Measure load and run throughput
4. Compare results and calculate contribution percentage
5. Save results to `binary_search_ablation_results.json`

## Expected Insights

This experiment answers:
- **Does binary search within nodes help or hurt performance?**
- **What percentage of total improvement comes from this optimization?**
- **Are modern CPU optimizations making algorithmic complexity less important?**

## Files

- `bskip_baseline_linear.h` - Baseline with linear search (BINARY_SEARCH=0)
- `bskip_with_binary_search.h` - With binary search (BINARY_SEARCH=1)
- `run_ablation_experiment.py` - Automated test script
- `binary_search_ablation_results.json` - Raw results (generated after running)
- `ABLATION_ANALYSIS.md` - Existing analysis with previous results
- `README.md` - This file

## Hypothesis

Based on the existing ABLATION_ANALYSIS.md, binary search within nodes provides:
- **Minimal or negative performance impact** due to:
  - Branch misprediction penalties
  - Poor cache utilization
  - Hardware prefetcher disruption
- **Linear search is better** for typical workloads on modern CPUs

## Relation to OpenEvolve Optimizations

The best_program.h doesn't actually change BINARY_SEARCH - it keeps it at 0 (linear search). The performance gains come from OTHER optimizations like:
- Thread-local hints for faster traversal
- Adaptive node splitting
- Optimized range query loops

This experiment proves that the "obvious" optimization (binary search) is actually not beneficial.

