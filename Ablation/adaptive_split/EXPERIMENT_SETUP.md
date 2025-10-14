# Adaptive Node Splitting Ablation Experiment Setup

## Purpose

This experiment isolates and measures the performance impact of **only** the Adaptive Node Splitting optimization in the B-Skiplist data structure. This is part of understanding what OpenEvolve actually optimized in the `best_program.h`.

## Experiment Design

### Three Test Cases

| Version | Description | File |
|---------|-------------|------|
| **Baseline** | Original B-Skiplist **without** adaptive split | `bskip_baseline_no_adaptive.h` |
| **Adaptive Only** | Original B-Skiplist **with** adaptive split only | `bskip_with_adaptive.h` |
| **Best Program** | OpenEvolve optimized with all improvements | `best_program.h` |

### The Single Variable Being Tested

The **only difference** between Baseline and Adaptive Only is this code change in the `insert()` function (around line 1303):

**Baseline:**
```cpp
int split_index = curr_node->num_elts / 2;
```

**Adaptive:**
```cpp
int split_index = curr_node->num_elts / 2;
if ((int)rank < split_index) {
    split_index = std::max(1, split_index - (int)(curr_node->num_elts/16 + 1));
} else {
    split_index = std::min((int)curr_node->num_elts - 1, split_index + (int)(curr_node->num_elts/16 + 1));
}
```

## How Files Were Created

1. **`bskip_baseline_no_adaptive.h`**: Copied from current `bskip.h` and removed adaptive split logic
2. **`bskip_with_adaptive.h`**: Direct copy of current `bskip.h` (which has adaptive split)
3. **`best_program.h`**: Already exists from OpenEvolve output

## Running the Experiment

```bash
# From the Ablation/adaptive_split directory
./run_adaptive_split_ablation.py
```

The script will:
1. For each version:
   - Copy the test file to `bskiplist/bskip.h`
   - Clean and rebuild
   - Run YCSB benchmark 3 times
   - Calculate average throughput
2. Compare results:
   - Baseline vs Adaptive Only → Impact of adaptive split alone
   - Baseline vs Best Program → Total improvement from all optimizations
   - Calculate adaptive split's contribution percentage

## Metrics Measured

- **Load Throughput**: Operations per microsecond during data loading phase
- **Run Throughput**: Operations per microsecond during query/update phase
- **Combined Score**: Average of load and run throughput

## Expected Results Format

```
Baseline (No Adaptive Split):
  Load: XX.XX ops/us
  Run: XX.XX ops/us
  Combined: XX.XX ops/us

Adaptive Split Only:
  Load: XX.XX ops/us (+X.X%)
  Run: XX.XX ops/us (+X.X%)
  Combined: XX.XX ops/us (+X.X%)

Best Program (All Optimizations):
  Load: XX.XX ops/us (+X.X%)
  Run: XX.XX ops/us (+X.X%)
  Combined: XX.XX ops/us (+X.X%)

Adaptive Split Contribution Analysis:
  Adaptive Split Improvement: X.XX ops/us
  Total Improvement (Best vs Baseline): X.XX ops/us
  Adaptive Split accounts for: XX.X% of total improvement
```

## Files in This Directory

- `README.md` - Overview of the experiment
- `EXPERIMENT_SETUP.md` - This file, detailed setup documentation
- `bskip_baseline_no_adaptive.h` - Test version without adaptive split
- `bskip_with_adaptive.h` - Test version with adaptive split only
- `run_adaptive_split_ablation.py` - Automated experiment script
- `adaptive_split_ablation_results.json` - Results (generated after running)
- `ABLATION_ANALYSIS.md` - Detailed analysis (to be created after results)

## Analysis Questions

After running the experiment, we'll answer:

1. **Does adaptive split provide measurable performance improvement?**
2. **How much of the total OpenEvolve improvement comes from adaptive split?**
3. **Is the added complexity worth the performance gain?**
4. **Does the benefit vary between load and run phases?**

## Relation to Other Optimizations

This experiment is part of a series of ablation studies:

- `/Ablation/binary_search/` - Tests binary search optimization impact
- `/Ablation/adaptive_split/` - Tests adaptive split optimization impact (this experiment)
- Future: Thread-local hints, combined optimizations, etc.

Each ablation isolates a single variable to understand the contribution of each optimization technique.





