# ✅ Fixes Applied for Linux Server

## Issues Fixed

### 1. ✅ Data Directory Path
**Before**: `BSKIP_DIR/data/uniform/`  
**After**: `/mydata/skip_data/uniform/`  
**Reason**: Data is stored in a different location on your Linux server

### 2. ✅ Command Format
**Before**:
```python
cmd = [
    "./ycsb",
    "-l", f"{BSKIP_DIR}/data/uniform/load_100M_uniform_uint64",
    "-i", f"{BSKIP_DIR}/data/uniform/txns_100M_100r_0i_uniform_uint64",
    "-n", str(NUM_THREADS),
    "-o", "/dev/null"
]
```

**After**:
```python
cmd = [
    "./ycsb",
    DATA_DIR,                    # "/mydata/skip_data/uniform/"
    WORKLOAD,                    # "a"
    str(NUM_THREADS),           # "32"
    "ablation_flip_coins_run.txt"
]
```

**Reason**: Your ycsb binary uses the format: `./ycsb <data_dir> <workload> <threads> <output>`

### 3. ✅ Best Program Path
**Before**: `PROJECT_ROOT / "openevolve_output" / "best" / "best_program.h"`  
**After**: `PROJECT_ROOT / "bskiplist" / "openevolve_output" / "best" / "best_program.h"`  
**Reason**: The openevolve_output is inside the bskiplist directory

### 4. ✅ Thread Count
**Before**: `NUM_THREADS = 48`  
**After**: `NUM_THREADS = 32`  
**Reason**: Adjusted to match your server configuration

## Current Configuration

```python
# Data location
DATA_DIR = "/mydata/skip_data/uniform/"

# Test parameters
NUM_RUNS = 3
WORKLOAD = "a"        # YCSB-A (100% reads)
NUM_THREADS = 32      # 32 threads

# Command that will be executed
./ycsb /mydata/skip_data/uniform/ a 32 ablation_flip_coins_run.txt
```

## Verification

### Script Syntax
```bash
✅ Python syntax validated
✅ All imports correct
✅ Command format matches your ycsb binary
```

### Required Files
```bash
✅ bskiplist/bskip.h (original)
✅ bskiplist/openevolve_output/best/best_program.h (evolved)
⚠️ /mydata/skip_data/uniform/ (verify on Linux server)
```

## What Was Preserved

The following features remain unchanged:
- ✅ Automatic backup/restore of bskip.h
- ✅ Clean compilation between versions
- ✅ 3 runs per version with 5s sleep
- ✅ Statistical analysis and JSON output
- ✅ Error handling and cleanup
- ✅ Auto-detection of project paths

## Testing on Linux Server

### Quick Test
```bash
# 1. Verify data directory
ls -l /mydata/skip_data/uniform/

# 2. Test ycsb command format
cd bskiplist
./ycsb /mydata/skip_data/uniform/ a 32 test.txt

# 3. If successful, run full ablation
cd ../Ablation/flip_coins_optimization
python3 run_flip_coins_ablation.py
```

### Expected Command Execution

During the experiment, you should see:
```
Running: ./ycsb /mydata/skip_data/uniform/ a 32 ablation_flip_coins_run.txt
```

This matches your specified format: `./ycsb /mydata/skip_data/uniform/ a 32 out.txt`

## Files Updated

1. **run_flip_coins_ablation.py** - Main script with fixes applied
2. **CONFIGURATION.md** - New file documenting the configuration
3. **FIXES_APPLIED.md** - This file

## Ready to Run

✅ All directory issues fixed  
✅ Command format corrected  
✅ Paths adjusted for your server  
✅ Configuration documented  
✅ Script validated  

**The ablation experiment is now ready to run on your Linux server!**

---

## Quick Start

```bash
cd /path/to/bskip_artifact/Ablation/flip_coins_optimization
python3 run_flip_coins_ablation.py
```

Results will be saved to: `flip_coins_ablation_results.json`

---

**Last Updated**: 2025-10-07  
**Status**: ✅ Fixed and ready for Linux server

