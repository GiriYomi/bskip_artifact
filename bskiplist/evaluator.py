import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional
import fcntl
import time
import json
import signal

from openevolve.evaluation_result import EvaluationResult


class TimeoutError(Exception):
    """Raised when evaluation times out"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Evaluation timed out")


BSKIP_DIR = os.path.abspath(os.path.dirname(__file__))
BSKIP_HEADER_PATH = os.path.join(BSKIP_DIR, "bskip.h")
YSCSB_BIN_PATH = os.path.join(BSKIP_DIR, "ycsb")

# Baseline statistics from benchmark run (20 runs, collected data)
# These serve as the reference point for evaluating candidates
BASELINE_STATS = {
    "load": {
        "mean": 17.891957,
        "stdev": 0.664131,
        "median": 17.649551,
        "min": 16.925838,
        "max": 19.184535
    },
    "run": {
        "mean": 18.648723,
        "stdev": 0.994040,
        "median": 18.336922,
        "min": 17.108713,
        "max": 20.639950
    }
}

# Significance threshold: candidate must exceed baseline mean + 1 std dev
# to be considered a real improvement (not noise)
SIGNIFICANCE_THRESHOLD_SIGMA = 1.0


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
    """Run benchmark and return results with proper timeout handling"""
    artifacts: Dict[str, Any] = {"run": {}}
    TIMEOUT_SECONDS = 580
    
    if not os.path.exists(YSCSB_BIN_PATH):
        artifacts["run"]["rc"] = 1
        artifacts["run"]["stdout"] = ""
        artifacts["run"]["stderr"] = f"Binary {YSCSB_BIN_PATH} not found"
        return artifacts
        
    cmd = ["./ycsb", dataset_dir, workload, str(threads), output_file]
    print(f"[DEBUG] Running command: {' '.join(cmd)}")
    
    try:
        # Use subprocess.run() with timeout for proper timeout handling
        # This prevents the infinite loop issue with readline()
        result = subprocess.run(
            cmd,
            cwd=BSKIP_DIR,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS
        )
        
        # Print output in real-time (or at least after completion)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"[STDERR] {result.stderr}")
        
        artifacts["run"]["rc"] = result.returncode
        artifacts["run"]["stdout"] = result.stdout
        artifacts["run"]["stderr"] = result.stderr
        artifacts["run"]["cmd"] = " ".join(cmd)
        
    except subprocess.TimeoutExpired as e:
        print(f"[WARNING] Benchmark timed out after {TIMEOUT_SECONDS}s")
        artifacts["run"]["rc"] = 124
        artifacts["run"]["stdout"] = e.stdout if e.stdout else ""
        artifacts["run"]["stderr"] = f"Timeout after {TIMEOUT_SECONDS}s"
        artifacts["run"]["cmd"] = " ".join(cmd)
    
    except Exception as e:
        print(f"[ERROR] Benchmark failed with exception: {e}")
        artifacts["run"]["rc"] = 1
        artifacts["run"]["stdout"] = ""
        artifacts["run"]["stderr"] = str(e)
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


def _is_significant_improvement(candidate_value: float, baseline_mean: float, baseline_stdev: float) -> bool:
    """Check if candidate value significantly exceeds baseline (mean + 1*sigma)"""
    threshold = baseline_mean + (SIGNIFICANCE_THRESHOLD_SIGMA * baseline_stdev)
    return candidate_value > threshold


def _calculate_improvement_metrics(cand_load: float, cand_run: float) -> Dict[str, Any]:
    """Calculate improvement metrics and check significance against baseline"""
    
    # Calculate raw improvements
    base_load_mean = BASELINE_STATS["load"]["mean"]
    base_load_stdev = BASELINE_STATS["load"]["stdev"]
    base_run_mean = BASELINE_STATS["run"]["mean"]
    base_run_stdev = BASELINE_STATS["run"]["stdev"]
    
    # Calculate percentage improvements
    load_improvement_pct = ((cand_load - base_load_mean) / base_load_mean * 100.0) if base_load_mean > 0 else 0.0
    run_improvement_pct = ((cand_run - base_run_mean) / base_run_mean * 100.0) if base_run_mean > 0 else 0.0
    
    # Check if improvements are statistically significant
    load_is_significant = _is_significant_improvement(cand_load, base_load_mean, base_load_stdev)
    run_is_significant = _is_significant_improvement(cand_run, base_run_mean, base_run_stdev)
    
    # Calculate thresholds for reference
    load_threshold = base_load_mean + (SIGNIFICANCE_THRESHOLD_SIGMA * base_load_stdev)
    run_threshold = base_run_mean + (SIGNIFICANCE_THRESHOLD_SIGMA * base_run_stdev)
    
    # Combined score: only positive if BOTH metrics show significant improvement
    # This ensures we don't accept candidates that improve one metric while regressing another
    if load_is_significant and run_is_significant:
        combined_score = 0.5 * load_improvement_pct + 0.5 * run_improvement_pct
    else:
        # Penalize if not both significant
        combined_score = min(load_improvement_pct, run_improvement_pct)
    
    return {
        "load_improvement_pct": load_improvement_pct,
        "run_improvement_pct": run_improvement_pct,
        "combined_score": combined_score,
        "load_is_significant": load_is_significant,
        "run_is_significant": run_is_significant,
        "load_threshold": load_threshold,
        "run_threshold": run_threshold,
        "baseline_load_mean": base_load_mean,
        "baseline_load_stdev": base_load_stdev,
        "baseline_run_mean": base_run_mean,
        "baseline_run_stdev": base_run_stdev
    }


def _evaluate_internal(program_path: str) -> EvaluationResult:
    """
    Internal evaluation function (wrapped by evaluate() with timeout)
    
    New evaluation strategy:
    1. Test candidate (compilation + correctness tests)
    2. Run candidate benchmark TWICE for stability
    3. Average the two runs
    4. Compare against pre-collected baseline statistics
    5. Require statistical significance (exceeds baseline mean + 1 std dev)
    """
    print(f"[DEBUG] Evaluating program: {program_path}")
    print(f"[DEBUG] Using pre-collected baseline: Load={BASELINE_STATS['load']['mean']:.3f}±{BASELINE_STATS['load']['stdev']:.3f}, Run={BASELINE_STATS['run']['mean']:.3f}±{BASELINE_STATS['run']['stdev']:.3f}")
    
    # Setup
    if os.path.exists('/home/yomi/0Projects/skip_data/uniform/'):
        dataset_dir = "/home/yomi/0Projects/skip_data/uniform/"
    else:
        dataset_dir = "/mydata/skip_data/uniform/"  # skip_data stays at /mydata
    
    workload = "a"
    threads = 32
    output_file = "results/tmp.txt"
    make_env = os.environ.copy()
    
    print(f"[DEBUG] Dataset directory: {dataset_dir}")
    
    artifacts = {}
    metrics = {}
    
    # Step 1: Test candidate compilation and basic functionality
    print("[DEBUG] Step 1: Compiling CANDIDATE and running correctness tests...")
    try:
        cand_artifacts = _compile_and_test(program_path, make_env)
        print("[DEBUG] ✓ Candidate compiled successfully and passed tests!")
        
    except Exception as e:
        print(f"[DEBUG] ✗ Candidate failed early (compilation/tests): {e}")
        return EvaluationResult(metrics={"combined_score": -999}, artifacts={"error": f"Candidate failed early: {e}"})
    
    # Step 2: Run candidate benchmark FIRST time
    print("[DEBUG] Step 2: Running CANDIDATE benchmark (run 1/2)...")
    try:
        candidate_result_1 = _run_benchmark(dataset_dir, workload, threads, f"{output_file}.candidate1")
        
        if candidate_result_1["run"]["rc"] != 0:
            print(f"[DEBUG] Candidate run 1 failed with return code {candidate_result_1['run']['rc']}")
            _restore_original(cand_artifacts)
            return EvaluationResult(metrics={"combined_score": -999}, artifacts={"error": f"Candidate run 1 failed: {candidate_result_1['run']['stderr']}"})
        
        candidate_metrics_1 = _parse_throughput(candidate_result_1["run"]["stdout"], "candidate1")
        print(f"[DEBUG] Candidate run 1 metrics: {candidate_metrics_1}")
        
    except Exception as e:
        print(f"[DEBUG] Candidate benchmark run 1 failed with exception: {e}")
        _restore_original(cand_artifacts)
        return EvaluationResult(metrics={"combined_score": -999}, artifacts={"error": f"Candidate benchmark 1 failed: {e}"})
    
    # Step 3: Run candidate benchmark SECOND time (for stability)
    print("[DEBUG] Step 3: Running CANDIDATE benchmark (run 2/2)...")
    try:
        candidate_result_2 = _run_benchmark(dataset_dir, workload, threads, f"{output_file}.candidate2")
        
        if candidate_result_2["run"]["rc"] != 0:
            print(f"[DEBUG] Candidate run 2 failed with return code {candidate_result_2['run']['rc']}")
            _restore_original(cand_artifacts)
            return EvaluationResult(metrics={"combined_score": -999}, artifacts={"error": f"Candidate run 2 failed: {candidate_result_2['run']['stderr']}"})
        
        candidate_metrics_2 = _parse_throughput(candidate_result_2["run"]["stdout"], "candidate2")
        print(f"[DEBUG] Candidate run 2 metrics: {candidate_metrics_2}")
        
    except Exception as e:
        print(f"[DEBUG] Candidate benchmark run 2 failed with exception: {e}")
        _restore_original(cand_artifacts)
        return EvaluationResult(metrics={"combined_score": -999}, artifacts={"error": f"Candidate benchmark 2 failed: {e}"})
    
    # Restore original bskip.h
    _restore_original(cand_artifacts)
    
    # Step 4: Average the two candidate runs for stable measurement
    print("[DEBUG] Step 4: Averaging candidate runs for stability...")
    cand1_load = candidate_metrics_1.get("candidate1_median_load_ops_per_us", 0.0)
    cand2_load = candidate_metrics_2.get("candidate2_median_load_ops_per_us", 0.0)
    cand1_run = candidate_metrics_1.get("candidate1_median_run_ops_per_us", 0.0)
    cand2_run = candidate_metrics_2.get("candidate2_median_run_ops_per_us", 0.0)
    
    # Average of two runs
    avg_cand_load = (cand1_load + cand2_load) / 2.0
    avg_cand_run = (cand1_run + cand2_run) / 2.0
    
    # Store individual and averaged metrics
    metrics.update({
        "candidate1_median_load_ops_per_us": cand1_load,
        "candidate1_median_run_ops_per_us": cand1_run,
        "candidate2_median_load_ops_per_us": cand2_load,
        "candidate2_median_run_ops_per_us": cand2_run,
        "candidate_avg_load_ops_per_us": avg_cand_load,
        "candidate_avg_run_ops_per_us": avg_cand_run
    })
    
    print(f"[DEBUG] Run 1: Load={cand1_load:.3f}, Run={cand1_run:.3f}")
    print(f"[DEBUG] Run 2: Load={cand2_load:.3f}, Run={cand2_run:.3f}")
    print(f"[DEBUG] Average: Load={avg_cand_load:.3f}, Run={avg_cand_run:.3f}")
    
    # Step 5: Compare against baseline and check significance
    print("[DEBUG] Step 5: Comparing against baseline and checking statistical significance...")
    improvement_metrics = _calculate_improvement_metrics(avg_cand_load, avg_cand_run)
    metrics.update(improvement_metrics)
    
    # Print detailed comparison
    print(f"[DEBUG] Baseline Load: {improvement_metrics['baseline_load_mean']:.3f} ± {improvement_metrics['baseline_load_stdev']:.3f} ops/us")
    print(f"[DEBUG] Candidate Load: {avg_cand_load:.3f} ops/us (threshold: {improvement_metrics['load_threshold']:.3f})")
    print(f"[DEBUG] Load improvement: {improvement_metrics['load_improvement_pct']:.2f}% - {'✓ SIGNIFICANT' if improvement_metrics['load_is_significant'] else '✗ NOT SIGNIFICANT'}")
    
    print(f"[DEBUG] Baseline Run: {improvement_metrics['baseline_run_mean']:.3f} ± {improvement_metrics['baseline_run_stdev']:.3f} ops/us")
    print(f"[DEBUG] Candidate Run: {avg_cand_run:.3f} ops/us (threshold: {improvement_metrics['run_threshold']:.3f})")
    print(f"[DEBUG] Run improvement: {improvement_metrics['run_improvement_pct']:.2f}% - {'✓ SIGNIFICANT' if improvement_metrics['run_is_significant'] else '✗ NOT SIGNIFICANT'}")
    
    print(f"[DEBUG] Combined score: {improvement_metrics['combined_score']:.2f}%")
    
    if improvement_metrics['load_is_significant'] and improvement_metrics['run_is_significant']:
        print("[DEBUG] ✓✓ BOTH metrics show significant improvement!")
    else:
        print("[DEBUG] ✗ Not both metrics significant - likely noise or regression")
    
    return EvaluationResult(metrics=metrics, artifacts=artifacts)


def evaluate(program_path: str) -> EvaluationResult:
    """
    Main evaluate function with timeout protection.
    
    This wrapper ensures the evaluation respects OpenEvolve's timeout setting (600s).
    It prevents infinite loops by using signal-based timeout.
    """
    # OpenEvolve sets evaluator timeout to 600 seconds
    # Set our timeout slightly less (595s) to allow cleanup
    EVALUATOR_TIMEOUT = 580
    
    # Set up signal-based timeout (Unix/Linux systems)
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(EVALUATOR_TIMEOUT)
    
    try:
        result = _evaluate_internal(program_path)
        signal.alarm(0)  # Cancel the alarm
        signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
        return result
        
    except TimeoutError as e:
        signal.alarm(0)  # Cancel the alarm
        signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
        print(f"[ERROR] Evaluation timed out after {EVALUATOR_TIMEOUT}s")
        return EvaluationResult(
            metrics={"combined_score": -999},
            artifacts={"error": f"Evaluation timeout after {EVALUATOR_TIMEOUT}s"}
        )
        
    except Exception as e:
        signal.alarm(0)  # Cancel the alarm
        signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
        print(f"[ERROR] Evaluation failed with exception: {e}")
        return EvaluationResult(
            metrics={"combined_score": -999},
            artifacts={"error": str(e)}
        )


def evaluate_stage1(program_path: str) -> EvaluationResult:
    return evaluate(program_path)

