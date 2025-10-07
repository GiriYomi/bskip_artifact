# Adaptive Split Ablation Experiment - Complete Setup

## ✅ Created Files

All files have been successfully created in `/home/yomi/0Projects/bskip_artifact/Ablation/adaptive_split/`:

### Test Files (Header Files)
1. **`bskip_baseline_no_adaptive.h`**
   - Original bskip.h with adaptive split **removed**
   - Uses simple midpoint splitting: `split_index = curr_node->num_elts / 2`
   - Serves as baseline for comparison

2. **`bskip_with_adaptive.h`**
   - Copy of current bskip.h with adaptive split **present**
   - Uses biased splitting based on insertion position
   - Tests the impact of adaptive split alone

3. **Referenced: `../../openevolve_output/best/best_program.h`**
   - OpenEvolve's optimized version
   - Has ALL optimizations (adaptive split + hints + binary search, etc.)

### Automation & Documentation
4. **`run_adaptive_split_ablation.py`** ⭐ (Executable)
   - Main experiment script
   - Automatically builds and tests all three versions
   - Calculates speedups and contribution percentages
   - Saves results to JSON

5. **`README.md`**
   - Overview of the experiment
   - Explains what adaptive splitting is
   - Shows code differences
   - Expected insights

6. **`EXPERIMENT_SETUP.md`**
   - Detailed technical documentation
   - Explains experiment design
   - File creation process
   - Relation to other ablation studies

7. **`QUICK_START.md`** ⭐
   - Simple instructions to run the experiment
   - Example output
   - Troubleshooting tips

8. **`SUMMARY.md`** (This file)
   - Complete overview of all created files

## 🎯 The Optimization Being Tested

**Adaptive Node Splitting** changes this code in the `insert()` function:

### Before (Baseline)
```cpp
int split_index = curr_node->num_elts / 2;
```

### After (Adaptive)
```cpp
int split_index = curr_node->num_elts / 2;
if ((int)rank < split_index) {
    // insertion on left side: shift split left a bit  
    split_index = std::max(1, split_index - (int)(curr_node->num_elts/16 + 1));
} else {
    // insertion on right side: shift split right a bit
    split_index = std::min((int)curr_node->num_elts - 1, split_index + (int)(curr_node->num_elts/16 + 1));
}
```

**Goal**: Reduce future splits by giving more space to the side where insertions are happening.

## 🚀 How to Run

```bash
cd /home/yomi/0Projects/bskip_artifact/Ablation/adaptive_split
./run_adaptive_split_ablation.py
```

Expected runtime: ~10-15 minutes

## 📊 What Gets Measured

For each version, the script measures:
- **Load Throughput**: ops/μs during data loading
- **Run Throughput**: ops/μs during queries/updates  
- **Combined Score**: Average of load and run

Then calculates:
- Speedup of Adaptive vs Baseline
- Speedup of Best Program vs Baseline
- What % of total improvement comes from adaptive split

## 🔍 Expected Insights

After running, you'll know:
1. Does adaptive split improve performance?
2. By how much? (percentage and absolute ops/μs)
3. What portion of OpenEvolve's gain is from this optimization?
4. Is the added complexity justified?

## 📁 Directory Structure

```
Ablation/adaptive_split/
├── bskip_baseline_no_adaptive.h     # Test file: baseline
├── bskip_with_adaptive.h            # Test file: adaptive only
├── run_adaptive_split_ablation.py   # Experiment script ⭐
├── README.md                         # Overview
├── EXPERIMENT_SETUP.md               # Technical details
├── QUICK_START.md                    # Running instructions ⭐
├── SUMMARY.md                        # This file
└── (after running)
    ├── adaptive_split_ablation_results.json  # Raw results
    └── ABLATION_ANALYSIS.md                  # Analysis (to be created)
```

## 🔗 Related Experiments

This is part of a series of ablation studies:
- `/Ablation/binary_search/` - Tests binary search optimization
- `/Ablation/adaptive_split/` - Tests adaptive split (this experiment)

Each isolates one optimization to understand its contribution.

## ✨ Key Differences from Binary Search Ablation

The binary_search ablation tested **intra-node search methods**.
This experiment tests **inter-node split strategies**.

Both help understand what made `best_program.h` faster than the original.

## 📝 Next Steps After Running

1. Review `adaptive_split_ablation_results.json` for raw data
2. Create `ABLATION_ANALYSIS.md` with detailed interpretation
3. Compare results with other ablation experiments
4. Determine overall optimization strategy recommendations

## 🎓 Learning Objectives

This experiment teaches:
- How to isolate a single optimization in a complex system
- The importance of measuring actual impact vs theoretical benefit  
- How to quantify contribution of individual optimizations
- Scientific method applied to performance engineering

---

**Status**: ✅ All files created and ready to run
**Next Action**: Run `./run_adaptive_split_ablation.py` and analyze results

