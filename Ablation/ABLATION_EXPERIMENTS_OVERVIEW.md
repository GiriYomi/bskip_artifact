# B-Skiplist Ablation Experiments Overview

## Purpose

This directory contains ablation experiments designed to isolate and measure the performance impact of individual optimizations in the B-Skiplist data structure. Each experiment changes **only one variable** to understand its contribution to overall performance.

## Available Experiments

### 1. Binary Search Within Nodes (`binary_search/`)

**Question**: Is binary search (O(log n)) faster than linear search (O(n)) within nodes?

**Variable Tested**: `BINARY_SEARCH` preprocessor define (0 vs 1)

**Key Finding**: Binary search is **SLOWER** (~0.4% regression) due to:
- Branch misprediction penalties
- Cache-unfriendly random access
- Hardware prefetcher disruption

**Lesson**: Algorithmic complexity doesn't always predict real-world performance on modern CPUs.

---

### 2. Adaptive Node Splitting (`adaptive_split/`)

**Question**: Does biasing split points based on insertion patterns reduce future splits?

**Variable Tested**: Split index calculation in insert()
- Baseline: `split_index = num_elts / 2` (always middle)
- Adaptive: Shift split point ~6% toward insertion side

**Expected**: To be determined by running experiment

**Lesson**: To be determined after running

---

## Experiment Structure

Each experiment follows the same pattern:

```
experiment_name/
├── bskip_baseline_*.h           # Version without optimization
├── bskip_with_*.h               # Version with ONLY this optimization
├── run_*_ablation.py            # Automated test script ⭐
├── *_ablation_results.json      # Results (generated)
├── README.md                    # Overview
├── QUICK_START.md               # Running instructions ⭐
├── EXPERIMENT_SETUP.md          # Technical details
├── SUMMARY.md                   # Complete file listing
└── ABLATION_ANALYSIS.md         # Detailed results analysis
```

## How to Run an Experiment

```bash
# Choose an experiment
cd /home/yomi/0Projects/bskip_artifact/Ablation/[experiment_name]

# Read the quick start
cat QUICK_START.md

# Run the experiment
./run_*_ablation.py

# Review results
cat *_ablation_results.json
```

## Understanding Results

Each experiment measures:
- **Load Throughput**: ops/μs during data loading phase
- **Run Throughput**: ops/μs during query/update phase
- **Combined Score**: Average of load and run

And calculates:
1. **Optimization Impact**: How much does this single change help/hurt?
2. **Total Improvement**: What's the gap between baseline and best program?
3. **Contribution Percentage**: What % of total improvement comes from this optimization?

## Results Summary Table

| Experiment | Optimization Impact | Best vs Baseline | Contribution % | Recommendation |
|------------|-------------------|------------------|----------------|----------------|
| **Binary Search** | -0.4% (regression) | +5.5% | -7% (hurts!) | ❌ Don't use |
| **Adaptive Split** | TBD | +5.5% | TBD | TBD |

## Key Insights

### 1. Binary Search (Completed)

✅ **Finding**: Binary search within nodes hurts performance

**Why it matters**: 
- Challenges the assumption that O(log n) > O(n)
- Shows importance of cache locality and branch prediction
- Demonstrates that modern CPU microarchitecture can trump algorithmic complexity

**Implication**: OpenEvolve's best_program.h correctly keeps linear search (BINARY_SEARCH=0)

### 2. Adaptive Split (Pending)

❓ **Finding**: To be determined

**Why it matters**:
- Tests if predictive heuristics help or hurt
- Measures impact of adaptive strategies
- Determines if added complexity is worth it

**Implication**: Will inform whether to keep adaptive splitting in production

## Methodology

### Controlled Variables
- Same hardware
- Same workload (YCSB-A, uniform distribution)
- Same compiler flags
- Same number of runs (3)

### Single Variable Testing
Each experiment changes ONLY ONE thing:
- Binary Search: One #define
- Adaptive Split: ~10 lines of code

This isolates causation and prevents confounding factors.

### Reproducibility
- All test files are checked in
- Scripts are automated
- Documentation explains exact changes
- Results are saved to JSON

## Comparison with OpenEvolve's Best Program

OpenEvolve's `best_program.h` includes multiple optimizations:
1. Thread-local hints for traversal ✅
2. Adaptive node splitting ✅
3. Optimized range query loops ✅
4. Binary search within nodes ❌ (not used!)

These ablation experiments help us understand:
- Which optimizations actually matter
- How much each contributes
- Whether to adopt them in production

## Future Experiments

Potential additional ablations:
- [ ] Thread-local hints impact
- [ ] Range query loop optimizations
- [ ] Combined effect of multiple optimizations
- [ ] Interaction effects between optimizations

## Statistical Considerations

- **3 runs per version**: Balances thoroughput and statistical power
- **Sleep between runs**: Reduces thermal throttling effects
- **Percentage changes**: More meaningful than absolute values
- **Multiple metrics**: Load + Run captures different workload phases

## How to Add a New Experiment

1. Create directory: `/Ablation/new_experiment/`
2. Create test files (baseline + optimized)
3. Copy and adapt `run_*_ablation.py` script
4. Create documentation (README, QUICK_START, etc.)
5. Run experiment
6. Document results in ABLATION_ANALYSIS.md
7. Update this overview

## Directory Navigation

```
Ablation/
├── ABLATION_EXPERIMENTS_OVERVIEW.md  ← You are here
├── binary_search/
│   ├── QUICK_START.md               ← Start here for this experiment
│   ├── run_ablation_experiment.py   ← Run this
│   └── ... (see SUMMARY.md)
└── adaptive_split/
    ├── QUICK_START.md               ← Start here for this experiment
    ├── run_adaptive_split_ablation.py ← Run this
    └── ... (see SUMMARY.md)
```

## Related Documentation

- `/HEURISTIC_ANALYSIS.md` - Analysis of OpenEvolve's heuristics
- `/EVALUATOR_FLOW_VERIFICATION.md` - How evaluator works
- `/extract_evolve_program/DETAILED_COMPARISON_REPORT.md` - Program comparison

## Contact & Contribution

These experiments are designed to be:
- **Reproducible**: Anyone can run them
- **Documented**: Clear explanations of what and why
- **Extensible**: Easy to add new experiments
- **Educational**: Teaches ablation study methodology

---

**Last Updated**: 2025-10-06
**Status**: 
- ✅ Binary Search: Complete with results
- 🚧 Adaptive Split: Ready to run



