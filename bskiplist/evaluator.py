import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional
import fcntl

from openevolve.evaluation_result import EvaluationResult


BSKIP_DIR = os.path.abspath(os.path.dirname(__file__))
YSCSB_CPP_PATH = os.path.join(BSKIP_DIR, "ycsb.cpp")
BSKIP_HEADER_PATH = os.path.join(BSKIP_DIR, "bskip.h")
YSCSB_BIN_PATH = os.path.join(BSKIP_DIR, "ycsb")


def _compile_candidate(candidate_program_path: str, make_env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Replace the repository's bskip.h (if candidate is a header) or ycsb.cpp (if candidate is cpp)
    with the candidate program, build the binary via Makefile, and then restore the original file.
    Returns build artifacts.
    """
    artifacts: Dict[str, Any] = {"compile": {}}
    original_backup_path: Optional[str] = None

    # FIXED: Always treat as header file for bskip project since OpenEvolve creates .py temp files
    # but we're always working with C++ header code
    candidate_is_header = True  # Force header detection for bskip.h replacement
    target_path = BSKIP_HEADER_PATH if candidate_is_header else YSCSB_CPP_PATH
    
    # Create process-safe lock file to prevent parallel evaluation conflicts
    lock_file_path = os.path.join(BSKIP_DIR, ".evaluation_lock")
    lock_file = None
    try:
        # Acquire exclusive lock to prevent parallel evaluation conflicts
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        
        # Backup original source
        if os.path.exists(target_path):
            fd, original_backup_path = tempfile.mkstemp(
                prefix=("bskip_h_backup_" if candidate_is_header else "ycsb_cpp_backup_"),
                suffix=(".h" if candidate_is_header else ".cpp"),
            )
            os.close(fd)
            shutil.copy2(target_path, original_backup_path)
            artifacts["compile"]["backup"] = original_backup_path

        # Overwrite with candidate
        shutil.copy2(candidate_program_path, target_path)

        # Clean and build
        clean_proc = subprocess.run(
            ["make", "clean"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env
        )
        artifacts["compile"]["clean_rc"] = clean_proc.returncode
        artifacts["compile"]["clean_stdout"] = clean_proc.stdout
        artifacts["compile"]["clean_stderr"] = clean_proc.stderr

        build_proc = subprocess.run(
            ["make", "-j"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env
        )
        artifacts["compile"]["build_rc"] = build_proc.returncode
        artifacts["compile"]["build_stdout"] = build_proc.stdout
        artifacts["compile"]["build_stderr"] = build_proc.stderr

        if build_proc.returncode != 0:
            raise RuntimeError("Build failed")

        if not os.path.exists(YSCSB_BIN_PATH):
            raise FileNotFoundError("Built binary 'ycsb' not found")

        # Build and run correctness test before benchmarking
        test_proc = subprocess.run(
            ["make", "test"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env
        )
        artifacts["compile"]["test_build_rc"] = test_proc.returncode
        artifacts["compile"]["test_build_stdout"] = test_proc.stdout
        artifacts["compile"]["test_build_stderr"] = test_proc.stderr

        if test_proc.returncode != 0:
            raise RuntimeError("Test build failed")

        # Run correctness test
        test_bin_path = os.path.join(BSKIP_DIR, "test")
        if os.path.exists(test_bin_path):
            test_run_proc = subprocess.run(
                ["./test"], cwd=BSKIP_DIR, capture_output=True, text=True, timeout=60
            )
            artifacts["compile"]["test_run_rc"] = test_run_proc.returncode
            artifacts["compile"]["test_run_stdout"] = test_run_proc.stdout
            artifacts["compile"]["test_run_stderr"] = test_run_proc.stderr

            if test_run_proc.returncode != 0:
                raise RuntimeError("Correctness test failed")
            
            # Check for "success" in output
            if "success" not in test_run_proc.stdout:
                raise RuntimeError("Correctness test did not report success")
            
            # Check for violations
            if "violations = 0" not in test_run_proc.stdout:
                raise RuntimeError("Correctness test found violations")

        # Store restoration info but don't restore yet - let caller handle it
        artifacts["restore_info"] = {
            "original_backup_path": original_backup_path,
            "target_path": target_path,
            "lock_file": lock_file,
            "lock_file_path": lock_file_path
        }

    except Exception as e:
        # On error, restore immediately
        if original_backup_path and os.path.exists(original_backup_path):
            try:
                shutil.copy2(original_backup_path, target_path)
                os.remove(original_backup_path)
            except Exception:
                pass
        
        # Release lock on error
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                os.remove(lock_file_path)
            except Exception:
                pass
        raise

    return artifacts


def _restore_original(restore_info: Dict[str, Any]) -> None:
    """Restore original files and release locks"""
    original_backup_path = restore_info.get("original_backup_path")
    target_path = restore_info.get("target_path")
    lock_file = restore_info.get("lock_file")
    lock_file_path = restore_info.get("lock_file_path")
    
    # Restore original source
    if original_backup_path and os.path.exists(original_backup_path):
        try:
            shutil.copy2(original_backup_path, target_path)
            os.remove(original_backup_path)
        except Exception:
            pass
    
    # Release lock
    if lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            if os.path.exists(lock_file_path):
                os.remove(lock_file_path)
        except Exception:
            pass


def _run_benchmark(dataset_dir: str, workload: str, threads: int, output_file: str, num_runs: int = 1) -> Dict[str, Any]:
    """Run benchmark multiple times and return aggregated results for stability"""
    artifacts: Dict[str, Any] = {"run": {}}
    all_stdout = []
    all_stderr = []
    
    # Verify binary exists before running
    if not os.path.exists(YSCSB_BIN_PATH):
        artifacts["run"]["rc"] = 1
        artifacts["run"]["stdout"] = ""
        artifacts["run"]["stderr"] = f"Binary {YSCSB_BIN_PATH} not found"
        artifacts["run"]["cmd"] = f"Binary check failed"
        return artifacts
    
    for run_i in range(num_runs):
        # Check binary exists for each run (in case of race conditions)
        if not os.path.exists(YSCSB_BIN_PATH):
            artifacts["run"]["rc"] = 1
            artifacts["run"]["stdout"] = ""
            artifacts["run"]["stderr"] = f"Binary {YSCSB_BIN_PATH} disappeared during run {run_i}"
            artifacts["run"]["cmd"] = f"Run {run_i} binary check failed"
            return artifacts
            
        cmd = ["./ycsb", dataset_dir, workload, str(threads), f"{output_file}.run{run_i}"]
        proc = subprocess.run(cmd, cwd=BSKIP_DIR, capture_output=True, text=True)
        
        if proc.returncode != 0:
            artifacts["run"]["rc"] = proc.returncode
            artifacts["run"]["stdout"] = proc.stdout
            artifacts["run"]["stderr"] = proc.stderr
            artifacts["run"]["cmd"] = " ".join(cmd)
            return artifacts
            
        all_stdout.append(proc.stdout)
        all_stderr.append(proc.stderr)
    
    # Combine all outputs
    artifacts["run"]["rc"] = 0
    artifacts["run"]["stdout"] = "\n".join(all_stdout)
    artifacts["run"]["stderr"] = "\n".join(all_stderr)
    artifacts["run"]["cmd"] = f"Multiple runs: {num_runs}"
    artifacts["run"]["num_runs"] = num_runs
    return artifacts


def _parse_throughput(stdout: str, prefix: str = "candidate") -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    # Example lines from ycsb.cpp
    # "\tMedian Load throughput: %f ,ops/us"
    # "\tMedian Run throughput: %f ,ops/us"
    # "\tRun, throughput: %f ,ops/us"
    # "\tLoad took %lu us, throughput = %f ops/us"
    median_load_match = re.search(r"Median Load throughput: ([\d\.]+) ,ops/us", stdout)
    median_run_match = re.search(r"Median Run throughput: ([\d\.]+) ,ops/us", stdout)
    run_samples = re.findall(r"Run, throughput: ([\d\.]+) ,ops/us", stdout)
    load_samples = re.findall(r"Load took \d+ us, throughput = ([\d\.]+) ops/us", stdout)

    if median_load_match:
        metrics[f"{prefix}_median_load_ops_per_us"] = float(median_load_match.group(1))
    if median_run_match:
        metrics[f"{prefix}_median_run_ops_per_us"] = float(median_run_match.group(1))
    if run_samples:
        try:
            vals = [float(x) for x in run_samples]
            metrics[f"{prefix}_avg_run_ops_per_us"] = sum(vals) / max(len(vals), 1)
        except Exception:
            pass
    if load_samples:
        try:
            vals = [float(x) for x in load_samples]
            metrics[f"{prefix}_avg_load_ops_per_us"] = sum(vals) / max(len(vals), 1)
        except Exception:
            pass

    return metrics


def _compile_baseline(make_env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {"compile_baseline": {}}
    clean_proc = subprocess.run(["make", "clean"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)
    artifacts["compile_baseline"]["clean_rc"] = clean_proc.returncode
    artifacts["compile_baseline"]["clean_stdout"] = clean_proc.stdout
    artifacts["compile_baseline"]["clean_stderr"] = clean_proc.stderr

    build_proc = subprocess.run(["make", "-j"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)
    artifacts["compile_baseline"]["build_rc"] = build_proc.returncode
    artifacts["compile_baseline"]["build_stdout"] = build_proc.stdout
    artifacts["compile_baseline"]["build_stderr"] = build_proc.stderr
    if build_proc.returncode != 0:
        raise RuntimeError("Baseline build failed")
    if not os.path.exists(YSCSB_BIN_PATH):
        raise FileNotFoundError("Built binary 'ycsb' not found for baseline")
    return artifacts


def evaluate(program_path: str) -> EvaluationResult:
    """
    Build the candidate C++ benchmark (ycsb) with the provided ycsb.cpp,
    run it against the provided dataset directory, and parse throughput metrics.

    Required env:
      - BSKIP_DATASET_DIR: Directory containing workload files (uniform|zipfian) with load*/txns* files.
    Optional env:
      - BSKIP_WORKLOAD: one of a,b,c,d,e,x,y (default: c)
      - BSKIP_THREADS: integer thread count (default: 4)
      - BSKIP_OUTPUT: output filename (default: results/tmp.txt)
      - BSKIP_LATENCY: if "1", builds with LATENCY=1 to emit latency percentiles
    """
    artifacts: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}

    dataset_dir = os.environ.get("BSKIP_DATASET_DIR", "/mydata/skip_data/uniform/")
    workload = os.environ.get("BSKIP_WORKLOAD", "a")
    threads = int(os.environ.get("BSKIP_THREADS", "32"))
    output_file = os.environ.get("BSKIP_OUTPUT", os.path.join("results", "tmp.txt"))
    enable_latency = os.environ.get("BSKIP_LATENCY", "0") == "1"

    # Debug: Print dataset directory and check if it exists
    print(f"[DEBUG] Dataset directory: {dataset_dir}")
    if os.path.exists(dataset_dir):
        files = os.listdir(dataset_dir)
        print(f"[DEBUG] Files in dataset directory: {files[:10]}...")  # Show first 10 files
    else:
        print(f"[DEBUG] Dataset directory does not exist!")

    if not dataset_dir:
        artifacts["error"] = "BSKIP_DATASET_DIR not set. Cannot run ycsb without dataset."
        print("[candidate Eval Error] BSKIP_DATASET_DIR not set. Cannot run ycsb without dataset.")
        return EvaluationResult(metrics={"combined_score": 0.0, "candidate_runs_successfully": 0.0}, artifacts=artifacts)

    # Optionally set LATENCY via environment for make
    make_env = os.environ.copy()
    if enable_latency:
        make_env["LATENCY"] = "1"

    # Build and run baseline first (original code)
    try:
        base_build_art = _compile_baseline(make_env=make_env)
        artifacts.update(base_build_art)
    except Exception as e:
        artifacts["baseline_compile_error"] = str(e)
        print("[baseline Eval Error] Baseline compile failed")
        return EvaluationResult(metrics={"combined_score": 0.0, "baseline_runs_successfully": 0.0, "candidate_runs_successfully": 0.0}, artifacts=artifacts)

    # Run baseline once
    base_run_art = _run_benchmark(dataset_dir=dataset_dir, workload=workload, threads=threads, output_file=output_file, num_runs=1)
    artifacts.update({"baseline_run": base_run_art.get("run", {})})
    if base_run_art.get("run", {}).get("rc", 1) != 0:
        print("[baseline Eval Error] Baseline run failed")
        metrics.update({"baseline_runs_successfully": 0.0, "candidate_runs_successfully": 0.0, "combined_score": 0.0})
        return EvaluationResult(metrics=metrics, artifacts=artifacts)

    baseline_stdout = base_run_art.get("run", {}).get("stdout", "")
    baseline_metrics = _parse_throughput(baseline_stdout, prefix="baseline")
    metrics.update(baseline_metrics)
    metrics["baseline_runs_successfully"] = 1.0

    # Compile candidate and run
    restore_info = None
    try:
        cand_build_art = _compile_candidate(program_path, make_env=make_env)
        artifacts.update(cand_build_art)
        restore_info = cand_build_art.get("restore_info")
    except Exception as e:
        artifacts["candidate_compile_error"] = str(e)
        # If candidate cannot compile, treat as no improvement
        print("[candidate Eval Error] Candidate compile failed")
        metrics.update({"candidate_runs_successfully": 0.0, "combined_score": 0.0})
        return EvaluationResult(metrics=metrics, artifacts=artifacts)

    try:
        # Run candidate once
        cand_run_art = _run_benchmark(dataset_dir=dataset_dir, workload=workload, threads=threads, output_file=output_file, num_runs=1)
        artifacts.update(cand_run_art)
        if cand_run_art.get("run", {}).get("rc", 1) != 0:
            print("[candidate Eval Error] Candidate run failed")
            metrics.update({"candidate_runs_successfully": 0.0, "combined_score": 0.0})
            return EvaluationResult(metrics=metrics, artifacts=artifacts)
    finally:
        # Always restore original files after benchmarking
        if restore_info:
            _restore_original(restore_info)

    candidate_stdout = cand_run_art.get("run", {}).get("stdout", "")
    candidate_metrics = _parse_throughput(candidate_stdout, prefix="candidate")
    metrics.update(candidate_metrics)
    metrics["candidate_runs_successfully"] = 1.0

    # Compute percentage speedup for both load and run throughput
    eps = 1e-12
    
    # Calculate load speedup (median load throughput, fallback to avg load)
    base_load_key = "baseline_median_load_ops_per_us" if "baseline_median_load_ops_per_us" in metrics else "baseline_avg_load_ops_per_us"
    cand_load_key = "candidate_median_load_ops_per_us" if "candidate_median_load_ops_per_us" in metrics else "candidate_avg_load_ops_per_us"
    base_load_val = float(metrics.get(base_load_key, 0.0))
    cand_load_val = float(metrics.get(cand_load_key, 0.0))
    if base_load_val > eps:
        load_speedup = (cand_load_val - base_load_val) / base_load_val * 100.0
    else:
        load_speedup = 0.0
    
    # Calculate run speedup (median run throughput, fallback to avg run)
    base_run_key = "baseline_median_run_ops_per_us" if "baseline_median_run_ops_per_us" in metrics else "baseline_avg_run_ops_per_us"
    cand_run_key = "candidate_median_run_ops_per_us" if "candidate_median_run_ops_per_us" in metrics else "candidate_avg_run_ops_per_us"
    base_run_val = float(metrics.get(base_run_key, 0.0))
    cand_run_val = float(metrics.get(cand_run_key, 0.0))
    if base_run_val > eps:
        run_speedup = (cand_run_val - base_run_val) / base_run_val * 100.0
    else:
        run_speedup = 0.0
    
    # Combined score: equal weighting of load and run speedup
    combined_score = 0.5 * load_speedup + 0.5 * run_speedup
    
    # Store all metrics
    metrics["load_speedup"] = float(load_speedup)
    metrics["run_speedup"] = float(run_speedup)
    metrics["combined_score"] = float(combined_score)
    #metrics["percent_speedup_run_throughput"] = float(run_speedup)  # Keep for compatibility

    return EvaluationResult(metrics=metrics, artifacts=artifacts)


def evaluate_stage1(program_path: str) -> EvaluationResult:
    return evaluate(program_path)


