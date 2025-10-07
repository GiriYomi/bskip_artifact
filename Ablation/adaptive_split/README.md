# Adaptive Node Splitting Ablation Experiment

## Overview

This ablation experiment isolates the performance impact of the **Adaptive Node Splitting** optimization by comparing three versions of the B-Skiplist implementation.

## What is Adaptive Node Splitting?

When a node becomes full during insertion, it must be split into two nodes. The traditional approach splits at the midpoint. The **adaptive split** optimization biases the split point based on where the new key will be inserted:

- **If inserting on the left side**: Split slightly left of center to give the left node more space
- **If inserting on the right side**: Split slightly right of center to give the right node more space

This reduces the likelihood of immediate re-splits on the same side.

## Code Changes

The optimization modifies the split logic in the `insert()` function:

### Baseline (No Adaptive Split)
```cpp
// Simple midpoint split
int split_index = curr_node->num_elts / 2;
```

### With Adaptive Split
```cpp
// Adaptive split: bias based on insertion side
int split_index = curr_node->num_elts / 2;
if ((int)rank < split_index) {
    // insertion on left side: shift split left a bit
    split_index = std::max(1, split_index - (int)(curr_node->num_elts/16 + 1));
} else {
    // insertion on right side: shift split right a bit
    split_index = std::min((int)curr_node->num_elts - 1, split_index + (int)(curr_node->num_elts/16 + 1));
}
```

The split point is adjusted by approximately `num_elts/16` (about 6% for a node with 1024 elements).

## Test Configurations

1. **Baseline**: Original `bskip.h` with adaptive split removed (`bskip_baseline_no_adaptive.h`)
2. **Adaptive Only**: Original `bskip.h` with only the adaptive split optimization (`bskip_with_adaptive.h`)
3. **Best Program**: OpenEvolve-optimized version with all optimizations including adaptive split, thread-local hints, and binary search (`best_program.h`)

## Running the Experiment

```bash
cd /home/yomi/0Projects/bskip_artifact/Ablation/adaptive_split
chmod +x run_adaptive_split_ablation.py
./run_adaptive_split_ablation.py
```

The script will:
1. Build each version
2. Run YCSB workload A with uniform distribution
3. Measure load and run throughput
4. Compare results and calculate speedups
5. Save results to `adaptive_split_ablation_results.json`

## Expected Insights

This experiment will answer:
- **How much performance gain comes from adaptive splitting alone?**
- **What percentage of the total improvement is due to adaptive splitting vs other optimizations?**
- **Is adaptive splitting worth the added code complexity?**

## Files

- `bskip_baseline_no_adaptive.h` - Baseline without adaptive split
- `bskip_with_adaptive.h` - Original with adaptive split only
- `run_adaptive_split_ablation.py` - Automated test script
- `adaptive_split_ablation_results.json` - Raw results (generated after running)
- `ABLATION_ANALYSIS.md` - Detailed analysis (to be created after results)

## Hypothesis

The adaptive split optimization is expected to provide modest improvements by:
- Reducing the number of subsequent splits
- Improving cache locality by keeping related keys together
- Reducing memory allocation overhead

However, the impact may be small compared to other optimizations like thread-local hints and binary search within nodes.

