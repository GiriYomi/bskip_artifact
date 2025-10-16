# Ablation Study Setup - Complete Guide

## Summary

This document describes the complete automated ablation study setup for measuring individual optimization impacts in the BSkip data structure.

**Status**: ✅ Setup Complete and Ready to Run

## What Has Been Created

### 1. Ablation Versions (5 + Baseline + Full Evolved = 7 versions)

Located in `Ablation/versions/`:

| Version | File | Description | Expected Impact |
|---------|------|-------------|----------------|
| **Baseline** | `../bskiplist/bskip.h` | Original unoptimized version | Reference (0%) |
| **V1** | `bskip_v1_binary_search.h` | Binary search enabled | ~8-9% |
| **V2** | `bskip_v2_exponential_search.h` | Exponential + binary search | ~9-10% |
| **V3** | `bskip_v3_thread_hints.h` | Thread-local hints | ~9-10% |
| **V4** | `bskip_v4_bitops_flipcoins.h` | Bit operations in flip_coins | ~0.1-0.2% |
| **V5** | `bskip_v5_adaptive_split.h` | Adaptive split strategy | ~9-10% |
| **Evolved** | `../../openevolve_output_p8_iter100/best/best_program.h` | Full evolved version | 10.48% |

### 2. Automation Scripts

#### `create_ablation_versions.py`
- **Purpose**: Automatically generates all ablation versions
- **Usage**: `python3 create_ablation_versions.py`
- **Output**: Creates 5 version files in `versions/` directory

#### `run_ablation_study.py`
- **Purpose**: Automated benchmark runner for all versions
- **Features**:
  - Automatically switches between versions
  - Compiles each version
  - Runs benchmarks (default: 10 runs per version)
  - Generates comparison reports
  - Restores original bskip.h when complete
- **Usage**: `python3 run_ablation_study.py [options]`

#### `test_ablation_setup.py`
- **Purpose**: Validates setup without running benchmarks
- **Usage**: `python3 test_ablation_setup.py`

### 3. Documentation

- `README.md` - Main ablation study documentation
- `versions/README.md` - Version-specific documentation
- `ABLATION_STUDY_SETUP.md` - This file

## How to Run

### Quick Start (Default Settings)

```bash
cd Ablation
python3 run_ablation_study.py
```

This will:
1. Benchmark baseline: 10 runs
2. Benchmark V1 (binary search): 10 runs
3. Benchmark V2 (exponential search): 10 runs
4. Benchmark V3 (thread hints): 10 runs
5. Benchmark V4 (bitops): 10 runs
6. Benchmark V5 (adaptive split): 10 runs
7. Benchmark evolved (full): 10 runs
8. Generate comparison report

**Expected Time**: ~1-2 hours for 7 versions × 10 runs

### Custom Run Options

```bash
# Run with more iterations for better statistics
python3 run_ablation_study.py -n 20

# Run with fewer iterations for quick test
python3 run_ablation_study.py -n 3

# Use different dataset directory
python3 run_ablation_study.py -d /path/to/dataset/

# Change number of threads
python3 run_ablation_study.py -t 64

# Combine options
python3 run_ablation_study.py -n 15 -t 48
```

### All Command-Line Options

```
-n, --num-runs      Number of runs per version (default: 10)
-o, --output-dir    Output directory (default: ablation_results)
-d, --dataset-dir   Dataset directory (default: /mydata/skip_data/uniform/)
-w, --workload      YCSB workload [a,b,c,d,e,x,y] (default: a)
-t, --threads       Number of threads (default: 32)
```

## Output Structure

```
Ablation/
├── ablation_results/
│   └── run_YYYYMMDD_HHMMSS/
│       ├── ABLATION_REPORT.txt          # Main comparison report
│       ├── ablation_results.json        # JSON data for analysis
│       ├── baseline/
│       │   ├── run_01.txt
│       │   ├── run_01_metrics.json
│       │   └── ... (10 runs)
│       ├── v1_binary_search/
│       │   └── ... (10 runs)
│       ├── v2_exponential_search/
│       │   └── ... (10 runs)
│       ├── v3_thread_hints/
│       │   └── ... (10 runs)
│       ├── v4_bitops_flipcoins/
│       │   └── ... (10 runs)
│       ├── v5_adaptive_split/
│       │   └── ... (10 runs)
│       └── evolved_full/
│           └── ... (10 runs)
```

## Understanding Results

### Ablation Report Format

The `ABLATION_REPORT.txt` contains:

1. **Configuration** - Run parameters
2. **Baseline Performance** - Original bskip.h metrics
3. **Optimization Impact** - Sorted by improvement

Example output:
```
Version                          Load (ops/us)         Run (ops/us)          Load Δ%      Run Δ%       Combined Δ%
==============================================================================================================
Baseline (Original)              16.389 ± 0.066       16.784 ± 0.028       0.00%        0.00%        0.00%
--------------------------------------------------------------------------------------------------------------
V1: Binary Search                17.856 ± 0.089       18.123 ± 0.045       +8.95%       +7.98%       +8.46%
V2: Exponential Search           18.097 ± 0.101       18.552 ± 0.052       +10.42%      +10.53%      +10.48%
...
```

### Interpreting Percentages

- **Positive %** = Improvement over baseline
- **Negative %** = Regression from baseline
- **Load Δ%** = Improvement in load phase (initial data loading)
- **Run Δ%** = Improvement in run phase (workload execution)
- **Combined Δ%** = Average of load and run improvements

## Important Notes

### Safety Features

1. **Automatic Backup**: Original `bskip.h` is backed up before any changes
2. **Automatic Restoration**: Original `bskip.h` is restored after completion
3. **Error Handling**: If script fails, original is still restored
4. **Clean Compilation**: Each version starts with `make clean`

### What Gets Modified

The script temporarily modifies **only**:
- `bskiplist/bskip.h` (switched between versions)
- Compilation artifacts (cleaned each time)

**Everything else remains unchanged.**

### Requirements

Before running, ensure:
1. ✅ Ablation versions created (`create_ablation_versions.py`)
2. ✅ Dataset files exist in specified directory
3. ✅ Sufficient disk space (~1GB for results)
4. ✅ Time available (1-2 hours for full study)

## Troubleshooting

### "Versions directory not found"
```bash
python3 create_ablation_versions.py
```

### "Dataset files not found"
- Update dataset path: `python3 run_ablation_study.py -d /your/path/`
- Or place datasets in `/mydata/skip_data/uniform/`

### "Compilation failed"
- Check: `ablation_results/run_TIMESTAMP/VERSION_compilation_error.log`
- Ensure original `bskip.h` compiles: `cd ../bskiplist && make ycsb`

### Script hangs
- Each benchmark run has 600-second timeout
- Normal for each run to take 30-60 seconds
- Monitor progress in output

### Partial results
- Script saves results after each run
- If interrupted, partial results are in `ablation_results/run_TIMESTAMP/`
- Can extract data from individual run JSON files

## Advanced Usage

### Run Specific Versions Only

Edit `run_ablation_study.py` and modify the `self.versions` list:

```python
self.versions = [
    {"id": "baseline", ...},
    {"id": "v1_binary_search", ...},
    # Comment out versions you don't want to test
]
```

### Extract Data Programmatically

```python
import json

with open('ablation_results/run_TIMESTAMP/ablation_results.json') as f:
    data = json.load(f)
    
# Get baseline
baseline = data['baseline']
print(f"Baseline load: {baseline['load_mean']}")

# Get all versions
for version in data['versions']:
    print(f"{version['version_name']}: {version['combined_improvement_pct']:.2f}%")
```

### Run Different Workloads

```bash
# Test with workload C (100% reads)
python3 run_ablation_study.py -w c

# Test with workload B (95% reads, 5% writes)
python3 run_ablation_study.py -w b
```

## Expected Timeline

For default settings (10 runs per version):

- **Version creation**: ~5 seconds
- **Setup validation**: ~2 seconds
- **Per benchmark run**: ~30-60 seconds
- **Per version** (10 runs): ~5-10 minutes
- **Total for 7 versions**: ~1-2 hours

## Next Steps After Results

1. **Analyze Results**: Review `ABLATION_REPORT.txt`
2. **Statistical Analysis**: Use `ablation_results.json` for deeper analysis
3. **Visualize**: Create graphs from JSON data
4. **Document Findings**: Update research notes with discoveries
5. **Iterate**: Test additional optimizations if needed

## Files Created

The complete ablation study creates these files:

```
Ablation/
├── README.md                              # Main documentation
├── ABLATION_STUDY_SETUP.md               # This file
├── create_ablation_versions.py            # Version generator
├── run_ablation_study.py                  # Benchmark runner
├── test_ablation_setup.py                 # Setup validator
├── versions/                              # Ablation versions
│   ├── README.md
│   ├── bskip_v1_binary_search.h          (~88 KB)
│   ├── bskip_v2_exponential_search.h     (~89 KB)
│   ├── bskip_v3_thread_hints.h           (~89 KB)
│   ├── bskip_v4_bitops_flipcoins.h       (~88 KB)
│   ├── bskip_v5_adaptive_split.h         (~89 KB)
│   └── versions_metadata.json
└── ablation_results/                      # Results (after running)
    └── run_TIMESTAMP/
        └── ... (detailed results)
```

## Support

If you encounter issues:

1. Check this document
2. Run `python3 test_ablation_setup.py`
3. Review error logs in `ablation_results/run_TIMESTAMP/`
4. Check compilation logs: `VERSION_compilation.log`

## Summary Checklist

Before running the full ablation study:

- [ ] Ablation versions created (`create_ablation_versions.py` run)
- [ ] Setup validated (`test_ablation_setup.py` passed)
- [ ] Dataset files available
- [ ] Original `bskip.h` backed up (automatic)
- [ ] Sufficient time allocated (~1-2 hours)
- [ ] Disk space available (~1GB)

Then run:
```bash
python3 run_ablation_study.py
```

## Automation Benefits

This automated ablation study provides:

✅ **Consistency**: All versions tested with identical parameters  
✅ **Reproducibility**: Easy to re-run with different settings  
✅ **Safety**: Automatic backup and restoration  
✅ **Completeness**: Comprehensive comparison reports  
✅ **Efficiency**: Fully automated, minimal manual intervention  
✅ **Documentation**: Self-documenting results and logs  

---

**Ready to Run**: Everything is set up and automated. Just ensure datasets are available and execute `run_ablation_study.py`!

