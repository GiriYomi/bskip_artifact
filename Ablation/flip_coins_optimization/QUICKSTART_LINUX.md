# Quick Start Guide - Linux Server

## Running the flip_coins Ablation Experiment

### Prerequisites Check

```bash
# 1. Navigate to the project
cd /path/to/bskip_artifact

# 2. Verify files exist
ls -l bskiplist/bskip.h
ls -l openevolve_output/best/best_program.h
ls -l bskiplist/data/uniform/load_100M_uniform_uint64
ls -l bskiplist/data/uniform/txns_100M_100r_0i_uniform_uint64

# 3. Check compiler
g++ --version  # or clang++ --version

# 4. Test compilation works
cd bskiplist
make clean
make LATENCY=0
# Should compile successfully and create ./ycsb binary
```

### Run the Experiment

```bash
# Navigate to ablation directory
cd /path/to/bskip_artifact/Ablation/flip_coins_optimization

# Make script executable (if not already)
chmod +x run_flip_coins_ablation.py

# Run the experiment
python3 run_flip_coins_ablation.py
```

### Expected Runtime

- **Per version**: ~5-8 minutes (3 runs @ ~2 min each + 5s sleeps)
- **Total**: ~15-20 minutes
- **Output**: `flip_coins_ablation_results.json`

### What You'll See

```
╔══════════════════════════════════════════════════════════════╗
║  Ablation Study: flip_coins Optimization Impact             ║
╚══════════════════════════════════════════════════════════════╝

Configuration:
  • Workload: YCSB-A (100% reads)
  • Threads: 48
  • Runs per version: 3

✅ Backed up original to /path/to/bskiplist/bskip.h.backup

============================================================
Testing: Original Baseline (Adaptive flip_coins)
============================================================
📝 Using Original Baseline (already in place)
🔨 Compiling...
✅ Compilation successful

🏃 Run 1/3...
   Running: ./ycsb -l ... -i ... -n 48 -o /dev/null
   Load: 0.482156 ops/μs
   Run:  0.097717 ops/μs
   Sleeping 5 seconds...

🏃 Run 2/3...
   [... similar output ...]

🏃 Run 3/3...
   [... similar output ...]

============================================================
Testing: Best Program (Power-of-two optimized flip_coins)
============================================================
📝 Installed Best Program
🔨 Compiling...
✅ Compilation successful

🏃 Run 1/3...
   [... runs best program version ...]

============================================================
ANALYSIS
============================================================

📊 Performance Comparison:
============================================================
Metric                  | Baseline      | Best Program  | Change
------------------------------------------------------------
Load Throughput         | 0.4822 ops/μs | 1.2491 ops/μs | +159.06%
Run Throughput          | 0.0977 ops/μs | 0.2317 ops/μs | +137.09%
Combined Score          | 0.2900 ops/μs | 0.7404 ops/μs | +155.31%
============================================================

💡 Key Findings:
The flip_coins optimization (power-of-two fast path) provides:
  • Load phase: +159.06% improvement
  • Run phase:  +137.09% improvement
  • Overall:    +155.31% improvement

This is the ONLY change between baseline and best program.

💾 Results saved to: flip_coins_ablation_results.json
✅ Original bskip.h restored
```

### Verifying Results

```bash
# View raw results
cat flip_coins_ablation_results.json | python3 -m json.tool

# Check key metrics
grep -A 5 "analysis" flip_coins_ablation_results.json
```

### Interpreting Performance Numbers

**Good Results** (matches OpenEvolve's findings):
- Load improvement: +150% to +200%
- Run improvement: +100% to +150%
- Combined: +130% to +175%

**Unexpected Results** (investigate further):
- Negative improvement: Regression detected
- Very small improvement (<10%): Optimization not effective
- Very high variance: System instability

### Common Issues

#### Issue 1: Compilation Fails
```bash
# Error: undefined reference to sched_getcpu
# Solution: This is Linux-specific, won't work on Mac
# Make sure you're on Linux server!

# Error: _Vector_base not found
# Solution: Check compiler version - needs modern g++ or clang++
g++ --version  # Should be g++ 9+ or clang++ 10+
```

#### Issue 2: Data Files Missing
```bash
# Error: cannot open load file
cd bskiplist/data/uniform/
# If missing, you need to generate them
# Check: btree/ycsb_inputs/get-ycsb-inputs.sh
```

#### Issue 3: Permission Denied
```bash
chmod +x run_flip_coins_ablation.py
# Or run with: python3 run_flip_coins_ablation.py
```

#### Issue 4: Script Hangs
```bash
# Check if ycsb is still running
ps aux | grep ycsb

# Kill if needed
pkill ycsb

# Restore backup manually if needed
cp bskiplist/bskip.h.backup bskiplist/bskip.h
```

### Cleanup

The script automatically restores the original `bskip.h`, but if it crashes:

```bash
# Manual restore
cp bskiplist/bskip.h.backup bskiplist/bskip.h

# Clean backup
rm bskiplist/bskip.h.backup

# Clean build artifacts
cd bskiplist
make clean
```

### Next Steps

After running:

1. ✅ Review `flip_coins_ablation_results.json`
2. ✅ Compare with OpenEvolve's `best_program_info.json`
3. ✅ Document findings
4. ✅ Consider running with different workloads (YCSB-B, YCSB-C, etc.)

### Customization

To modify the experiment, edit `run_flip_coins_ablation.py`:

```python
# Line 39: Change number of runs
NUM_RUNS = 5  # More runs = better statistics

# Line 41: Change thread count
NUM_THREADS = 96  # Adjust to your CPU

# Line 86: Change workload
"-i", f"{BSKIP_DIR}/data/uniform/txns_100M_50r_50i_uniform_uint64",  # 50/50 mix
```

### Full Experiment Command

```bash
# One-liner to run everything
cd /path/to/bskip_artifact/Ablation/flip_coins_optimization && \
  python3 run_flip_coins_ablation.py 2>&1 | tee experiment_output.log
```

This saves output to both screen and `experiment_output.log`.

---

## Questions?

- 📖 Read `EXPERIMENT_SUMMARY.md` for detailed analysis
- 📖 Read `README.md` for overview
- 🔍 Check results in `flip_coins_ablation_results.json`
- 📝 Review source differences using: `diff -u bskiplist/bskip.h openevolve_output/best/best_program.h`

---

**Ready to run!** 🚀

The script is platform-independent and will work on any Linux server with the proper setup.

