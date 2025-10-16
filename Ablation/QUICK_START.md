# Ablation Study - Quick Start Guide

## ✅ Setup Complete!

All ablation study components have been created and are ready to use.

## 📁 What You Have

```
Ablation/
├── 🔧 Scripts (Executable)
│   ├── create_ablation_versions.py  ✅ Creates ablation versions
│   ├── run_ablation_study.py        ✅ Runs automated benchmarks  
│   └── test_ablation_setup.py       ✅ Validates setup
│
├── 📄 Documentation
│   ├── README.md                     📖 Main documentation
│   ├── ABLATION_STUDY_SETUP.md      📖 Complete setup guide
│   └── QUICK_START.md               📖 This file
│
└── 🗂️  Versions (5 ablation versions)
    ├── bskip_v1_binary_search.h
    ├── bskip_v2_exponential_search.h
    ├── bskip_v3_thread_hints.h
    ├── bskip_v4_bitops_flipcoins.h
    └── bskip_v5_adaptive_split.h
```

## 🚀 How to Run (3 Steps)

### Step 1: Verify Setup (Optional but Recommended)

```bash
cd Ablation
python3 test_ablation_setup.py
```

**Expected output**: All checks pass ✅ (except dataset check if files not in default location)

### Step 2: Ensure Dataset Files Exist

The script needs these files (for workload 'a'):
- `loada_unif_int.dat`
- `txnsa_unif_int.dat`

Default location: `/mydata/skip_data/uniform/`

**If your datasets are elsewhere**, use the `-d` flag (see below).

### Step 3: Run the Ablation Study

```bash
python3 run_ablation_study.py
```

**That's it!** The script will:
1. ✅ Test 7 versions (baseline + 5 ablations + full evolved)
2. ✅ Run 10 benchmarks per version (70 total runs)
3. ✅ Generate comparison report
4. ✅ Save detailed results

**Time**: ~1-2 hours

## ⚙️ Common Options

### Quick Test (3 runs per version)
```bash
python3 run_ablation_study.py -n 3
```
⏱️ Time: ~15-20 minutes

### Better Statistics (20 runs)
```bash
python3 run_ablation_study.py -n 20
```
⏱️ Time: ~3-4 hours

### Custom Dataset Directory
```bash
python3 run_ablation_study.py -d /your/path/to/dataset/
```

### Different Thread Count
```bash
python3 run_ablation_study.py -t 64
```

### Combine Options
```bash
python3 run_ablation_study.py -n 5 -t 48 -d /custom/path/
```

## 📊 Understanding Results

After completion, find results in:
```
ablation_results/run_YYYYMMDD_HHMMSS/
├── ABLATION_REPORT.txt      ← Read this first!
├── ablation_results.json    ← For detailed analysis
└── [version directories]    ← Individual run logs
```

### Sample Report Output

```
Performance Comparison vs Baseline
====================================================================
Version                  Load (ops/us)    Run (ops/us)     Δ%
====================================================================
Baseline (Original)      16.389 ± 0.066   16.784 ± 0.028   0.00%
--------------------------------------------------------------------
V1: Binary Search        17.856 ± 0.089   18.123 ± 0.045   +8.46%
V2: Exponential Search   18.097 ± 0.101   18.552 ± 0.052   +10.48%
...
====================================================================
```

## ❓ FAQ

### Q: Do I need to modify bskip.h manually?
**A:** No! The script handles everything automatically.

### Q: What if the script fails?
**A:** Your original `bskip.h` is automatically restored. Check error logs in the results directory.

### Q: Can I run specific versions only?
**A:** Yes, edit `self.versions` list in `run_ablation_study.py`.

### Q: How do I know it's working?
**A:** You'll see progress output like:
```
Benchmarking: V1: Binary Search
  Run 1/10... ✓ Load: 17.856, Run: 18.123 ops/us
  Run 2/10... ✓ Load: 17.892, Run: 18.145 ops/us
  ...
```

### Q: Can I stop and resume?
**A:** No, but partial results are saved. You can analyze completed runs.

## 🔍 What Gets Tested

| Version | Optimization | Expected Impact |
|---------|--------------|----------------|
| Baseline | None (original) | 0% (reference) |
| V1 | Binary search enabled | ~8-9% |
| V2 | Exponential+binary search | ~9-10% |
| V3 | Thread-local hints | ~9-10% |
| V4 | Bit operations in flip_coins | ~0.1-0.2% |
| V5 | Adaptive split strategy | ~9-10% |
| Evolved | All optimizations | 10.48% |

## 🛡️ Safety Features

✅ Original `bskip.h` is automatically backed up  
✅ Original is restored after completion (even if script fails)  
✅ Each compilation starts clean (`make clean`)  
✅ All changes are temporary  
✅ Results are timestamped (won't overwrite)  

## 📞 Need Help?

1. Read `ABLATION_STUDY_SETUP.md` for detailed information
2. Run `python3 test_ablation_setup.py` to diagnose issues
3. Check error logs in `ablation_results/run_TIMESTAMP/`

## 🎯 Next Steps After Results

1. **Review**: Read `ABLATION_REPORT.txt`
2. **Analyze**: Use `ablation_results.json` for deeper analysis
3. **Compare**: Match results with expected impacts
4. **Document**: Update research notes

## 📝 Full Documentation

For complete details, see:
- `README.md` - Main documentation
- `ABLATION_STUDY_SETUP.md` - Comprehensive guide
- `versions/README.md` - Version descriptions

---

## 🚀 Ready to Start?

```bash
cd Ablation
python3 run_ablation_study.py
```

**That's all you need!** The rest is automated. ✨

