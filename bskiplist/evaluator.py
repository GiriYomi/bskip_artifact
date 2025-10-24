import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional, List
import fcntl
import time
import json

from openevolve.evaluation_result import EvaluationResult


BSKIP_DIR = os.path.abspath(os.path.dirname(__file__))
BSKIP_HEADER_PATH = os.path.join(BSKIP_DIR, "bskip.h")
YSCSB_BIN_PATH = os.path.join(BSKIP_DIR, "ycsb")

# Baseline statistics from benchmark run (20 runs, collected data)
# These serve as the reference point for evaluating candidates
# Updated for current machine (run_20251015_091602)
BASELINE_STATS = {
    "load": {
        "mean": 16.3887327,
        "stdev": 0.06611527678556268,
        "median": 16.395864500000002,
        "min": 16.237138,
        "max": 16.496938
    },
    "run": {
        "mean": 16.78420905,
        "stdev": 0.02798818661784372,
        "median": 16.784672,
        "min": 16.726234,
        "max": 16.84221
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

        # Clean and build with timeout to prevent hangs
        clean_proc = subprocess.run(["make", "clean"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env, timeout=30)
        build_proc = subprocess.run(["make", "-j"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env, timeout=120)

        if build_proc.returncode != 0:
            print(f"[DEBUG] Build failed with return code {build_proc.returncode}")
            print(f"[DEBUG] Build stderr: {build_proc.stderr}")
            print(f"[DEBUG] Build stdout: {build_proc.stdout}")
            raise RuntimeError(f"Build failed with rc={build_proc.returncode}, stderr={build_proc.stderr}")

        if not os.path.exists(YSCSB_BIN_PATH):
            raise FileNotFoundError("Built binary 'ycsb' not found")

        # Run correctness test with timeout
        test_proc = subprocess.run(["make", "test"], cwd=BSKIP_DIR, capture_output=True, text=True, env=make_env, timeout=120)
        if test_proc.returncode != 0:
            print(f"[DEBUG] Test build failed with return code {test_proc.returncode}")
            print(f"[DEBUG] Test build stderr: {test_proc.stderr}")
            print(f"[DEBUG] Test build stdout: {test_proc.stdout}")
            raise RuntimeError(f"Test build failed with rc={test_proc.returncode}, stderr={test_proc.stderr}")

        test_bin_path = os.path.join(BSKIP_DIR, "test")
        if os.path.exists(test_bin_path):
            test_run_proc = subprocess.run(["./test"], cwd=BSKIP_DIR, capture_output=True, text=True, timeout=30)
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
    TIMEOUT_SECONDS = 580  # Each benchmark gets 280s (two runs = 560s total)
    
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


def _parse_throughput_samples(stdout: str) -> Dict[str, List[float]]:
    """Extract raw throughput samples for load and run phases from ycsb output."""
    run_samples = re.findall(r"Run, throughput: ([\d\.]+) ,ops/us", stdout)
    load_samples = re.findall(r"Load took \d+ us, throughput = ([\d\.]+) ops/us", stdout)
    try:
        run_vals = [float(x) for x in run_samples]
    except Exception:
        run_vals = []
    try:
        load_vals = [float(x) for x in load_samples]
    except Exception:
        load_vals = []
    return {"run": run_vals, "load": load_vals}


def _percentile(sorted_vals: List[float], q: float) -> float:
    """Nearest-rank percentile (q in [0,100]). Returns 0.0 for empty input."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if q <= 0:
        return sorted_vals[0]
    if q >= 100:
        return sorted_vals[-1]
    # Nearest-rank method
    import math
    rank = max(1, int(math.ceil((q / 100.0) * n)))
    return sorted_vals[rank - 1]


def _compute_stats(vals: List[float]) -> Dict[str, float]:
    """Compute descriptive stats for a list of floats. Returns zeros if empty."""
    if not vals:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "stdev": 0.0,
            "cv": 0.0,
        }
    n = len(vals)
    svals = sorted(vals)
    total = sum(vals)
    mean = total / n
    # Population stdev
    var = sum((x - mean) ** 2 for x in vals) / n
    import math
    stdev = math.sqrt(var)
    median = _percentile(svals, 50)
    p90 = _percentile(svals, 90)
    p95 = _percentile(svals, 95)
    p99 = _percentile(svals, 99)
    cv = (stdev / mean) if mean != 0 else 0.0
    return {
        "count": float(n),
        "min": svals[0],
        "max": svals[-1],
        "mean": mean,
        "median": median,
        "p90": p90,
        "p95": p95,
        "p99": p99,
        "stdev": stdev,
        "cv": cv,
    }


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
    
    workload = "e" # TODO change to a, b, c, d, e, x, y
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
        
        # Parse summary metrics and raw samples for run 1
        candidate_metrics_1 = _parse_throughput(candidate_result_1["run"]["stdout"], "candidate1")
        cand1_samples = _parse_throughput_samples(candidate_result_1["run"]["stdout"])
        cand1_load_stats = _compute_stats(cand1_samples["load"])  # ops/us
        cand1_run_stats = _compute_stats(cand1_samples["run"])    # ops/us
        # Prefix detailed stats for namespacing
        candidate_metrics_1.update({
            "candidate1_load_count": cand1_load_stats["count"],
            "candidate1_load_min": cand1_load_stats["min"],
            "candidate1_load_max": cand1_load_stats["max"],
            "candidate1_load_mean": cand1_load_stats["mean"],
            "candidate1_load_median": cand1_load_stats["median"],
            "candidate1_load_p90": cand1_load_stats["p90"],
            "candidate1_load_p95": cand1_load_stats["p95"],
            "candidate1_load_p99": cand1_load_stats["p99"],
            "candidate1_load_stdev": cand1_load_stats["stdev"],
            "candidate1_load_cv": cand1_load_stats["cv"],
            "candidate1_run_count": cand1_run_stats["count"],
            "candidate1_run_min": cand1_run_stats["min"],
            "candidate1_run_max": cand1_run_stats["max"],
            "candidate1_run_mean": cand1_run_stats["mean"],
            "candidate1_run_median": cand1_run_stats["median"],
            "candidate1_run_p90": cand1_run_stats["p90"],
            "candidate1_run_p95": cand1_run_stats["p95"],
            "candidate1_run_p99": cand1_run_stats["p99"],
            "candidate1_run_stdev": cand1_run_stats["stdev"],
            "candidate1_run_cv": cand1_run_stats["cv"],
        })
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
        
        # Parse summary metrics and raw samples for run 2
        candidate_metrics_2 = _parse_throughput(candidate_result_2["run"]["stdout"], "candidate2")
        cand2_samples = _parse_throughput_samples(candidate_result_2["run"]["stdout"])
        cand2_load_stats = _compute_stats(cand2_samples["load"])  # ops/us
        cand2_run_stats = _compute_stats(cand2_samples["run"])    # ops/us
        candidate_metrics_2.update({
            "candidate2_load_count": cand2_load_stats["count"],
            "candidate2_load_min": cand2_load_stats["min"],
            "candidate2_load_max": cand2_load_stats["max"],
            "candidate2_load_mean": cand2_load_stats["mean"],
            "candidate2_load_median": cand2_load_stats["median"],
            "candidate2_load_p90": cand2_load_stats["p90"],
            "candidate2_load_p95": cand2_load_stats["p95"],
            "candidate2_load_p99": cand2_load_stats["p99"],
            "candidate2_load_stdev": cand2_load_stats["stdev"],
            "candidate2_load_cv": cand2_load_stats["cv"],
            "candidate2_run_count": cand2_run_stats["count"],
            "candidate2_run_min": cand2_run_stats["min"],
            "candidate2_run_max": cand2_run_stats["max"],
            "candidate2_run_mean": cand2_run_stats["mean"],
            "candidate2_run_median": cand2_run_stats["median"],
            "candidate2_run_p90": cand2_run_stats["p90"],
            "candidate2_run_p95": cand2_run_stats["p95"],
            "candidate2_run_p99": cand2_run_stats["p99"],
            "candidate2_run_stdev": cand2_run_stats["stdev"],
            "candidate2_run_cv": cand2_run_stats["cv"],
        })
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
    
    # Compute combined per-phase stats across both runs for richer reporting
    combined_load_stats = _compute_stats(
        [
            *(_parse_throughput_samples(candidate_result_1["run"]["stdout"]) ["load"]),
            *(_parse_throughput_samples(candidate_result_2["run"]["stdout"]) ["load"]),
        ]
    )
    combined_run_stats = _compute_stats(
        [
            *(_parse_throughput_samples(candidate_result_1["run"]["stdout"]) ["run"]),
            *(_parse_throughput_samples(candidate_result_2["run"]["stdout"]) ["run"]),
        ]
    )

    # Store individual and averaged metrics
    metrics.update({
        "candidate1_median_load_ops_per_us": cand1_load,
        "candidate1_median_run_ops_per_us": cand1_run,
        "candidate2_median_load_ops_per_us": cand2_load,
        "candidate2_median_run_ops_per_us": cand2_run,
        "candidate_avg_load_ops_per_us": avg_cand_load,
        "candidate_avg_run_ops_per_us": avg_cand_run,
        # Combined stats across both runs (useful for stability and tails)
        "combined_load_count": combined_load_stats["count"],
        "combined_load_min": combined_load_stats["min"],
        "combined_load_max": combined_load_stats["max"],
        "combined_load_mean": combined_load_stats["mean"],
        "combined_load_median": combined_load_stats["median"],
        "combined_load_p90": combined_load_stats["p90"],
        "combined_load_p95": combined_load_stats["p95"],
        "combined_load_p99": combined_load_stats["p99"],
        "combined_load_stdev": combined_load_stats["stdev"],
        "combined_load_cv": combined_load_stats["cv"],
        "combined_run_count": combined_run_stats["count"],
        "combined_run_min": combined_run_stats["min"],
        "combined_run_max": combined_run_stats["max"],
        "combined_run_mean": combined_run_stats["mean"],
        "combined_run_median": combined_run_stats["median"],
        "combined_run_p90": combined_run_stats["p90"],
        "combined_run_p95": combined_run_stats["p95"],
        "combined_run_p99": combined_run_stats["p99"],
        "combined_run_stdev": combined_run_stats["stdev"],
        "combined_run_cv": combined_run_stats["cv"],
    })
    
    print(f"[DEBUG] Run 1: Load={cand1_load:.3f}, Run={cand1_run:.3f}")
    print(f"[DEBUG] Run 2: Load={cand2_load:.3f}, Run={cand2_run:.3f}")
    print(f"[DEBUG] Average: Load={avg_cand_load:.3f}, Run={avg_cand_run:.3f}")
    print(f"[DEBUG] Combined Load stats: p90={metrics['combined_load_p90']:.3f}, p95={metrics['combined_load_p95']:.3f}, p99={metrics['combined_load_p99']:.3f}, stdev={metrics['combined_load_stdev']:.3f}")
    print(f"[DEBUG] Combined Run stats:  p90={metrics['combined_run_p90']:.3f},  p95={metrics['combined_run_p95']:.3f},  p99={metrics['combined_run_p99']:.3f},  stdev={metrics['combined_run_stdev']:.3f}")
    
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
    Main evaluate function.
    
    OpenEvolve handles timeout at the framework level with asyncio.wait_for(timeout=600).
    We rely on:
    1. subprocess.run(timeout=...) for individual benchmark timeouts
    2. OpenEvolve's asyncio.wait_for for overall evaluation timeout
    
    This approach avoids multiprocessing pickling issues while still preventing hangs.
    """
    try:
        return _evaluate_internal(program_path)
    except Exception as e:
        print(f"[ERROR] Evaluation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return EvaluationResult(
            metrics={"combined_score": -999},
            artifacts={"error": str(e)}
        )


def evaluate_stage1(program_path: str) -> EvaluationResult:
    return evaluate(program_path)

