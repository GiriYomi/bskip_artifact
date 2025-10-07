import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional
import fcntl
import time

from openevolve.evaluation_result import EvaluationResult


BSKIP_DIR = os.path.abspath(os.path.dirname(__file__))
BSKIP_HEADER_PATH = os.path.join(BSKIP_DIR, "bskip.h")
YSCSB_BIN_PATH = os.path.join(BSKIP_DIR, "ycsb")


def _compile_and_test(candidate_program_path: str, make_env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Compile candidate program and run tests"""
    artifacts: Dict[str, Any] = {"compile": {}}
    original_backup_path: Optional[str] = None
    temp_candidate_path: Optional[str] = None

    try:
        # Backup original bskip.h
        if os.path.exists(BSKIP_HEADER_PATH):
            fd, original_backup_path = tempfile.mkstemp(suffix=".h", prefix="bskip_backup_")
            os.close(fd)
            shutil.copy2(BSKIP_HEADER_PATH, original_backup_path)

        # Handle candidate program - could be a .h file or a JSON file
        if candidate_program_path.endswith('.json'):
            # Extract code from JSON file
            import json
            with open(candidate_program_path, 'r') as f:
                candidate_data = json.load(f)
            candidate_code = candidate_data.get('code', '')
            
            # Create temporary .h file
            fd, temp_candidate_path = tempfile.mkstemp(suffix=".h", prefix="candidate_")
            os.close(fd)
            with open(temp_candidate_path, 'w') as f:
                f.write(candidate_code)
            
            # Replace with candidate
            shutil.copy2(temp_candidate_path, BSKIP_HEADER_PATH)
        else:
            # Direct .h file
            shutil.copy2(candidate_program_path, BSKIP_HEADER_PATH)

        # Clean and build
        clean_proc = subprocess.run(["make", "clean"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)
        build_proc = subprocess.run(["make", "-j"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)

        if build_proc.returncode != 0:
            print(f"[DEBUG] Build failed with return code {build_proc.returncode}")
            print(f"[DEBUG] Build stderr: {build_proc.stderr}")
            print(f"[DEBUG] Build stdout: {build_proc.stdout}")
            raise RuntimeError(f"Build failed with rc={build_proc.returncode}, stderr={build_proc.stderr}")

        if not os.path.exists(YSCSB_BIN_PATH):
            raise FileNotFoundError("Built binary 'ycsb' not found")

        # Run correctness test
        test_proc = subprocess.run(["make", "test"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)
        if test_proc.returncode != 0:
            print(f"[DEBUG] Test build failed with return code {test_proc.returncode}")
            print(f"[DEBUG] Test build stderr: {test_proc.stderr}")
            print(f"[DEBUG] Test build stdout: {test_proc.stdout}")
            raise RuntimeError(f"Test build failed with rc={test_proc.returncode}, stderr={test_proc.stderr}")

        test_bin_path = os.path.join(BSKIP_DIR, "test")
        if os.path.exists(test_bin_path):
            test_run_proc = subprocess.run(["./test"], cwd=BSKIP_DIR, capture_output=True, text=True, timeout=60)
            if test_run_proc.returncode != 0 or "success" not in test_run_proc.stdout:
                print(f"[DEBUG] Correctness test failed with return code {test_run_proc.returncode}")
                print(f"[DEBUG] Test stderr: {test_run_proc.stderr}")
                print(f"[DEBUG] Test stdout: {test_run_proc.stdout}")
                raise RuntimeError(f"Correctness test failed with rc={test_run_proc.returncode}, stderr={test_run_proc.stderr}, stdout={test_run_proc.stdout}")

        artifacts["restore_info"] = {"original_backup_path": original_backup_path, "temp_candidate_path": temp_candidate_path}

    except Exception as e:
        # Restore on error
        if original_backup_path and os.path.exists(original_backup_path):
            shutil.copy2(original_backup_path, BSKIP_HEADER_PATH)
            os.remove(original_backup_path)
        if temp_candidate_path and os.path.exists(temp_candidate_path):
            os.remove(temp_candidate_path)
        raise

    return artifacts


def _restore_original(artifacts: Dict[str, Any]) -> None:
    """Restore original files"""
    restore_info = artifacts.get("restore_info", {})
    original_backup_path = restore_info.get("original_backup_path")
    temp_candidate_path = restore_info.get("temp_candidate_path")
    
    if original_backup_path and os.path.exists(original_backup_path):
        shutil.copy2(original_backup_path, BSKIP_HEADER_PATH)
        os.remove(original_backup_path)
    
    if temp_candidate_path and os.path.exists(temp_candidate_path):
        os.remove(temp_candidate_path)


def _run_benchmark(dataset_dir: str, workload: str, threads: int, output_file: str) -> Dict[str, Any]:
    """Run benchmark and return results"""
    artifacts: Dict[str, Any] = {"run": {}}
    TIMEOUT_SECONDS = 580
    
    if not os.path.exists(YSCSB_BIN_PATH):
        artifacts["run"]["rc"] = 1
        artifacts["run"]["stdout"] = ""
        artifacts["run"]["stderr"] = f"Binary {YSCSB_BIN_PATH} not found"
        return artifacts
        
    cmd = ["./ycsb", dataset_dir, workload, str(threads), output_file]
    print(f"[DEBUG] Running command: {' '.join(cmd)}")
    
    # Run with output to console but also capture for parsing
    proc = subprocess.Popen(cmd, cwd=BSKIP_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
    
    stdout_lines = []
    stderr_lines = []
    start_time = time.time()
    
    # Stream output to console in real-time
    while True:
        # Check timeout first
        if time.time() - start_time > TIMEOUT_SECONDS:
            print(f"[WARNING] Benchmark timed out after {TIMEOUT_SECONDS}s. Terminating...")
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass

            artifacts["run"]["rc"] = 124
            artifacts["run"]["stdout"] = "\n".join(stdout_lines)
            artifacts["run"]["stderr"] = "timeout after {TIMEOUT_SECONDS}s"
            artifacts["run"]["cmd"] = " ".join(cmd)
            return artifacts

        output = proc.stdout.readline()
        if output == '' and proc.poll() is not None:
            break
        if output:
            print(output.strip())
            stdout_lines.append(output.strip())
    
    # Get any remaining stderr
    stderr_output = proc.stderr.read()
    if stderr_output:
        print(f"[STDERR] {stderr_output.strip()}")
        stderr_lines.append(stderr_output.strip())
    
    proc.wait()
    
    artifacts["run"]["rc"] = proc.returncode
    artifacts["run"]["stdout"] = "\n".join(stdout_lines)
    artifacts["run"]["stderr"] = "\n".join(stderr_lines)
    artifacts["run"]["cmd"] = " ".join(cmd)
    
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
    """Compile baseline (original) version"""
    print("[DEBUG] Compiling baseline...")
    
    clean_proc = subprocess.run(["make", "clean"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)
    build_proc = subprocess.run(["make", "-j"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)
    
    if build_proc.returncode != 0:
        raise RuntimeError("Baseline build failed")
    if not os.path.exists(YSCSB_BIN_PATH):
        raise FileNotFoundError("Built binary 'ycsb' not found for baseline")
    
    return {"baseline_compiled": True}


def evaluate(program_path: str) -> EvaluationResult:
    """Optimized evaluator: test candidate first, then baseline only if candidate passes"""
    print(f"[DEBUG] Evaluating program: {program_path}")
    
    # Setup
    if os.path.exists('/home/yomi/0Projects/skip_data/uniform/'):
        dataset_dir = "/home/yomi/0Projects/skip_data/uniform/"
    else:
        dataset_dir = "/mydata/skip_data/uniform/"
    
    workload = "a"
    threads = 32
    output_file = "results/tmp.txt"
    make_env = os.environ.copy()
    
    print(f"[DEBUG] Dataset directory: {dataset_dir}")
    
    artifacts = {}
    metrics = {}
    
    # Step 1: Test candidate compilation and basic functionality first
    print("[DEBUG] Step 1: Compiling CANDIDATE and running tests...")
    try:
        cand_artifacts = _compile_and_test(program_path, make_env)
        print("[DEBUG] ✓ Candidate compiled successfully and passed tests!")
        
    except Exception as e:
        print(f"[DEBUG] ✗ Candidate failed early (compilation/tests): {e}")
        return EvaluationResult(metrics={"combined_score": 0.0}, artifacts={"error": f"Candidate failed early: {e}"})
    
    # Step 2: Run candidate benchmark
    print("[DEBUG] Step 2: Running CANDIDATE benchmark (ycsb binary contains candidate code)...")
    try:
        candidate_result = _run_benchmark(dataset_dir, workload, threads, f"{output_file}.candidate")
        
        if candidate_result["run"]["rc"] != 0:
            print(f"[DEBUG] Candidate run failed with return code {candidate_result['run']['rc']}")
            print(f"[DEBUG] Candidate stderr: {candidate_result['run']['stderr']}")
            print(f"[DEBUG] Candidate stdout: {candidate_result['run']['stdout']}")
            _restore_original(cand_artifacts)
            return EvaluationResult(metrics={"combined_score": 0.0}, artifacts={"error": f"Candidate run failed with rc={candidate_result['run']['rc']}, stderr={candidate_result['run']['stderr']}"})
        
        candidate_metrics = _parse_throughput(candidate_result["run"]["stdout"], "candidate")
        metrics.update(candidate_metrics)
        print(f"[DEBUG] Candidate metrics: {candidate_metrics}")
        
    except Exception as e:
        print(f"[DEBUG] Candidate benchmark failed with exception: {e}")
        _restore_original(cand_artifacts)
        return EvaluationResult(metrics={"combined_score": 0.0}, artifacts={"error": f"Candidate benchmark failed: {e}"})
    
    # Step 3: Only now run baseline (candidate passed all tests)
    print("[DEBUG] Step 3: Restoring ORIGINAL bskip.h and running BASELINE...")
    try:
        # Restore original for baseline
        _restore_original(cand_artifacts)
        print("[DEBUG] ✓ Original bskip.h restored")
        
        # Ensure we start with clean baseline
        subprocess.run(["make", "clean"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env)
        _compile_baseline(make_env)
        print("[DEBUG] ✓ Baseline compiled (ycsb binary now contains original code)")
        baseline_result = _run_benchmark(dataset_dir, workload, threads, f"{output_file}.baseline")
        
        if baseline_result["run"]["rc"] != 0:
            return EvaluationResult(metrics={"combined_score": 0.0}, artifacts={"error": "Baseline run failed"})
        
        baseline_metrics = _parse_throughput(baseline_result["run"]["stdout"], "baseline")
        metrics.update(baseline_metrics)
        print(f"[DEBUG] Baseline metrics: {baseline_metrics}")
        
    except Exception as e:
        return EvaluationResult(metrics={"combined_score": 0.0}, artifacts={"error": f"Baseline failed: {e}"})
    
    # Step 4: Calculate speedup
    print("[DEBUG] Step 4: Calculating speedup...")
    base_load = metrics.get("baseline_median_load_ops_per_us", 0.0)
    cand_load = metrics.get("candidate_median_load_ops_per_us", 0.0)
    base_run = metrics.get("baseline_median_run_ops_per_us", 0.0)
    cand_run = metrics.get("candidate_median_run_ops_per_us", 0.0)
    
    load_speedup = ((cand_load - base_load) / base_load * 100.0) if base_load > 0 else 0.0
    run_speedup = ((cand_run - base_run) / base_run * 100.0) if base_run > 0 else 0.0
    combined_score = 0.5 * load_speedup + 0.5 * run_speedup
    
    metrics.update({
        "load_speedup": load_speedup,
        "run_speedup": run_speedup,
        "combined_score": combined_score
    })
    
    print(f"[DEBUG] Final metrics: load_speedup={load_speedup:.2f}%, run_speedup={run_speedup:.2f}%, combined={combined_score:.2f}%")
    
    return EvaluationResult(metrics=metrics, artifacts=artifacts)


def evaluate_stage1(program_path: str) -> EvaluationResult:
    return evaluate(program_path)

