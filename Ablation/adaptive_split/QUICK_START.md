# Quick Start: Adaptive Split Ablation Experiment

## What This Tests

This experiment measures the performance impact of **Adaptive Node Splitting** - a technique that biases node split points based on where keys are being inserted to reduce future splits.

## Three Versions Compared

1. **Baseline** (`bskip_baseline_no_adaptive.h`) - No adaptive split, always splits at midpoint
2. **Adaptive Only** (`bskip_with_adaptive.h`) - Has adaptive split, no other optimizations
3. **Best Program** (`../openevolve_output/best/best_program.h`) - All optimizations

## Run the Experiment

```bash
cd /home/yomi/0Projects/bskip_artifact/Ablation/adaptive_split
./run_adaptive_split_ablation.py
```

This will take approximately 10-15 minutes (3 runs × 3 versions × ~1-2 min each).

## What You'll See

The script will:
1. Test each version by building and running YCSB benchmarks
2. Print results showing throughput and speedup percentages
3. Calculate what percentage of total improvement comes from adaptive split
4. Save detailed results to `adaptive_split_ablation_results.json`

## Example Output

```
ADAPTIVE SPLIT ABLATION EXPERIMENT RESULTS
================================================================================

Baseline (No Adaptive Split):
  Load: 16.80 ops/us
  Run: 17.69 ops/us
  Combined: 17.25 ops/us

Adaptive Split Only:
  Load: 17.00 ops/us (+1.2%)
  Run: 17.85 ops/us (+0.9%)
  Combined: 17.43 ops/us (+1.0%)

Best Program (All Optimizations):
  Load: 17.85 ops/us (+6.3%)
  Run: 18.53 ops/us (+4.7%)
  Combined: 18.19 ops/us (+5.5%)

Adaptive Split Contribution Analysis:
  Adaptive Split Improvement: 0.18 ops/us
  Total Improvement (Best vs Baseline): 0.94 ops/us
  Adaptive Split accounts for: 19.1% of total improvement
```

## Understanding Results

- **Positive %** = Improvement (faster)
- **Negative %** = Regression (slower)
- **Contribution %** = How much of OpenEvolve's total gain comes from this one optimization

## Files Generated

After running:
- `adaptive_split_ablation_results.json` - Raw data for further analysis
- `results/ablation_adaptive_run_*.txt` - Individual benchmark outputs

## Next Steps

After getting results, you can:
1. Review the JSON file for detailed metrics
2. Create `ABLATION_ANALYSIS.md` with interpretation
3. Compare with other ablation experiments (binary_search, etc.)
4. Determine if adaptive splitting is worth the complexity

## Troubleshooting

**Build fails:**
- Make sure you're in the right directory
- Check that `bskiplist/` has all dependencies
- Verify YCSB data exists at `/home/yomi/0Projects/skip_data/uniform/`

**No results:**
- Check that YCSB executable exists in `bskiplist/`
- Verify all three test files exist
- Look at stderr output for specific errors

**Inconsistent results:**
- Run with more iterations (edit `num_runs=5` in the script)
- Make sure no other processes are using CPU
- Let system cool down between runs



