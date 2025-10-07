# Quick Start: Binary Search Ablation Experiment

## What This Tests

This experiment measures whether **binary search within nodes** (BINARY_SEARCH=1) is faster than **linear search** (BINARY_SEARCH=0) for B-Skiplist.

## Three Versions Compared

1. **Baseline** (`bskip_baseline_linear.h`) - Linear search, BINARY_SEARCH=0
2. **Binary Only** (`bskip_with_binary_search.h`) - Binary search, BINARY_SEARCH=1
3. **Best Program** (`../openevolve_output/best/best_program.h`) - All optimizations

## Run the Experiment

```bash
cd /home/yomi/0Projects/bskip_artifact/Ablation/binary_search
./run_ablation_experiment.py
```

Expected runtime: ~10-15 minutes

## What You'll See

```
ABLATION EXPERIMENT RESULTS
================================================================================

Baseline (Linear Search):
  Load: 16.80 ops/us
  Run: 17.69 ops/us
  Combined: 17.25 ops/us

Binary Search Only:
  Load: 16.75 ops/us (-0.3%)
  Run: 17.60 ops/us (-0.5%)
  Combined: 17.18 ops/us (-0.4%)

Best Program (All Optimizations):
  Load: 17.85 ops/us (+6.3%)
  Run: 18.53 ops/us (+4.7%)
  Combined: 18.19 ops/us (+5.5%)

Binary Search Contribution Analysis:
  Binary Search Improvement: -0.07 ops/us
  Total Improvement (Best vs Baseline): 0.94 ops/us
  Binary Search accounts for: -7.4% of total improvement
```

## Understanding Results

- **Negative %** = Binary search is SLOWER than linear (regression)
- **Positive %** = Improvement
- **Contribution %** = If negative, binary search hurts performance

## Key Finding

Binary search within nodes is typically **slower** than linear search for this data structure due to:
- Cache locality benefits of sequential access
- Branch prediction working well for linear scans
- Modern CPU prefetchers

This is a counter-intuitive result that highlights the importance of empirical testing!

## Files Generated

- `binary_search_ablation_results.json` - Raw data
- `results/ablation_run_*.txt` - Individual benchmark outputs

## Troubleshooting

**Build fails:**
- Verify you're in `/home/yomi/0Projects/bskip_artifact/bskiplist`
- Check all dependencies exist

**Different results than ABLATION_ANALYSIS.md:**
- System load varies
- Run multiple times for confidence
- Check that you're using the same workload (YCSB-A uniform)

## Related Experiments

- `/Ablation/adaptive_split/` - Tests adaptive split optimization
- Both experiments help understand what makes best_program.h faster

