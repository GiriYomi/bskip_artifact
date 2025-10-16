# Ablation Study for BSkip Optimizations

This directory contains scripts and results for an ablation study to measure the individual impact of each optimization in the evolved bskip.h version.

## Overview

The evolved version achieved a 10.48% performance improvement over the baseline. This ablation study isolates each optimization to determine its individual contribution to the overall performance gain.

## Optimizations Being Tested

1. **V1: Binary Search** - Enable `BINARY_SEARCH=1` in leaf nodes
2. **V2: Exponential Search** - Exponential + binary search strategy for large nodes
3. **V3: Thread-Local Hints** - Thread-local per-level hints for faster traversal
4. **V4: Bitops in flip_coins** - Bit operations optimization in promotion algorithm
5. **V5: Adaptive Split** - Adaptive split strategy and other micro-optimizations
6. **Evolved (Full)** - Complete evolved version with all optimizations

## Quick Start

### Step 1: Create Ablation Versions

```bash
cd Ablation
python3 create_ablation_versions.py
```

This will create 5 versions of bskip.h in the `versions/` subdirectory, each with a specific optimization applied.

### Step 2: Run Ablation Study

```bash
python3 run_ablation_study.py
```

This will:
1. Benchmark the baseline (original bskip.h)
2. Benchmark each ablation version (10 runs per version by default)
3. Generate a comparison report

The script automatically:
- Backs up the original bskip.h
- Switches between versions
- Compiles each version
- Runs benchmarks
- Restores the original bskip.h at the end

### Step 3: View Results

Results are saved in `ablation_results/run_TIMESTAMP/`:
- `ABLATION_REPORT.txt` - Human-readable comparison report
- `ablation_results.json` - Detailed JSON data for further analysis
- Individual run logs in subdirectories

## Usage Options

### Run with more iterations (for statistical significance)

```bash
python3 run_ablation_study.py -n 20
```

### Use different dataset

```bash
python3 run_ablation_study.py -d /path/to/dataset/uniform/
```

### Run with different number of threads

```bash
python3 run_ablation_study.py -t 64
```

### Full options

```bash
python3 run_ablation_study.py -h
```

## Expected Results

Based on our analysis, we expect:

| Optimization | Expected Impact |
|--------------|----------------|
| Binary Search | ~8-9% (largest contributor) |
| Exponential Search | ~1-1.5% |
| Thread-Local Hints | ~0.2-0.5% |
| Bitops in flip_coins | ~0.1-0.2% |
| Adaptive Split | <0.1% |

## File Structure

```
Ablation/
├── README.md                      # This file
├── create_ablation_versions.py   # Script to create ablation versions
├── run_ablation_study.py          # Script to run benchmarks
├── versions/                      # Ablation versions (created by script)
│   ├── bskip_v1_binary_search.h
│   ├── bskip_v2_exponential_search.h
│   ├── bskip_v3_thread_hints.h
│   ├── bskip_v4_bitops_flipcoins.h
│   ├── bskip_v5_adaptive_split.h
│   ├── README.md
│   └── versions_metadata.json
└── ablation_results/              # Benchmark results (created by script)
    └── run_TIMESTAMP/
        ├── ABLATION_REPORT.txt
        ├── ablation_results.json
        ├── baseline/
        ├── v1_binary_search/
        ├── v2_exponential_search/
        ├── v3_thread_hints/
        ├── v4_bitops_flipcoins/
        ├── v5_adaptive_split/
        └── evolved_full/
```

## Important Notes

1. **Backup**: The script automatically backs up your original `bskip.h` before running
2. **Restoration**: The original `bskip.h` is restored after all benchmarks complete
3. **Time**: Each version runs 10 benchmarks by default, so expect ~1-2 hours for complete study
4. **Dependencies**: Requires the same datasets as the main YCSB benchmark
5. **Clean Isolation**: Some optimizations (v2, v3, v5) currently use the full evolved version as cleanly isolating them requires significant refactoring

## Interpreting Results

The ablation report shows:
- **Load Δ%**: Performance change in load phase vs baseline
- **Run Δ%**: Performance change in run phase vs baseline
- **Combined Δ%**: Average of load and run improvements

Positive percentages indicate improvements, negative indicate regressions.

## Troubleshooting

### "Versions directory not found"
Run `python3 create_ablation_versions.py` first

### "Dataset files not found"
Ensure dataset files exist in the specified directory (default: `/mydata/skip_data/uniform/`)

### "Compilation failed"
Check compilation logs in the results directory for specific errors

### Script hangs
Some benchmarks may take time; default timeout is 600 seconds per run

## Advanced Usage

### Run only specific versions

Modify the `self.versions` list in `run_ablation_study.py` to include only the versions you want to test.

### Change benchmark parameters

Edit the YCSB parameters in the script:
- `workload`: Change to 'b', 'c', 'd', etc.
- `num_threads`: Adjust thread count
- `dataset_dir`: Point to different datasets

### Extract specific metrics

Parse the JSON file for detailed analysis:

```python
import json
with open('ablation_results/run_TIMESTAMP/ablation_results.json') as f:
    data = json.load(f)
    # Access baseline: data['baseline']
    # Access versions: data['versions']
```

## Citation

If you use this ablation study in your research, please cite the original BSkip paper and mention the OpenEvolve optimization framework.

