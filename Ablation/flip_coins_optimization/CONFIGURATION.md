# Configuration for Your Linux Server

## Current Configuration

The script is configured with the following settings for your Linux server:

### Data Location
```python
DATA_DIR = "/mydata/skip_data/uniform/"
```

### Command Format
```bash
./ycsb <data_dir> <workload> <num_threads> <output_file>
```

**Example**:
```bash
./ycsb /mydata/skip_data/uniform/ a 32 ablation_flip_coins_run.txt
```

### Test Configuration
```python
NUM_RUNS = 3              # 3 runs per version
WORKLOAD = "a"            # YCSB-A workload (100% reads)
NUM_THREADS = 32          # 32 threads
```

### File Paths
```python
# Paths are auto-detected from script location
BSKIP_DIR = PROJECT_ROOT / "bskiplist"
ORIGINAL_BSKIP = BSKIP_DIR / "bskip.h"
BEST_PROGRAM = PROJECT_ROOT / "bskiplist" / "openevolve_output" / "best" / "best_program.h"
```

## Required Files

### Source Files
- ✅ `bskiplist/bskip.h` (original baseline)
- ✅ `bskiplist/openevolve_output/best/best_program.h` (evolved version)

### Data Files (at `/mydata/skip_data/uniform/`)
Your ycsb binary expects data files in this directory. The workload parameter `a` will be used by the binary to load the appropriate files.

## Modifying Configuration

### Change Thread Count
Edit line 42 in `run_flip_coins_ablation.py`:
```python
NUM_THREADS = 64  # Change to your CPU core count
```

### Change Workload
Edit line 41:
```python
WORKLOAD = "b"  # For YCSB-B (read-modify-write)
WORKLOAD = "c"  # For YCSB-C (read-only)
# etc.
```

### Change Number of Runs
Edit line 40:
```python
NUM_RUNS = 5  # More runs = better statistics
```

### Change Data Directory
Edit line 34:
```python
DATA_DIR = "/different/path/to/data/"
```

## Verification Before Running

### 1. Check Data Directory
```bash
ls -l /mydata/skip_data/uniform/
# Should show your YCSB data files
```

### 2. Check Source Files
```bash
ls -l bskiplist/bskip.h
ls -l bskiplist/openevolve_output/best/best_program.h
```

### 3. Test Compilation
```bash
cd bskiplist
make clean
make LATENCY=0
# Should create ./ycsb binary
```

### 4. Test Command Format
```bash
cd bskiplist
./ycsb /mydata/skip_data/uniform/ a 32 test_output.txt
# Should run successfully
```

## Expected Output

The script will produce output like:

```
Running: ./ycsb /mydata/skip_data/uniform/ a 32 ablation_flip_coins_run.txt
   Load: 0.482156 ops/μs
   Run:  0.097717 ops/μs
```

## Output Files

Each run creates:
- `ablation_flip_coins_run.txt` - Detailed output from current run
- `flip_coins_ablation_results.json` - Final aggregated results

## Command Line Override

You can also modify settings via environment variables:

```bash
# Set custom thread count
export NUM_THREADS=64
python3 run_flip_coins_ablation.py

# Or modify the script directly before running
```

## Troubleshooting

### Issue: Data directory not found
```
Error: cannot open load file
```
**Solution**: Check that `/mydata/skip_data/uniform/` exists and contains data files

### Issue: Wrong command format
```
Error: invalid arguments
```
**Solution**: Verify your ycsb binary expects: `./ycsb <data_dir> <workload> <threads> <output>`

### Issue: Different ycsb interface
If your ycsb uses different arguments (like `-l`, `-i`, `-n`, `-o`), modify the `run_benchmark()` function:

```python
cmd = [
    "./ycsb",
    "-l", f"{DATA_DIR}/load_file",
    "-i", f"{DATA_DIR}/txn_file", 
    "-n", str(NUM_THREADS),
    "-o", "output.txt"
]
```

---

**Status**: ✅ Configured for your Linux server with the correct command format

