import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional

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

    # Determine target file based on extension
    candidate_is_header = candidate_program_path.endswith(".h") or candidate_program_path.endswith(".hpp")
    target_path = BSKIP_HEADER_PATH if candidate_is_header else YSCSB_CPP_PATH
    try:
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

    finally:
        # Always restore original source if we backed it up
        if original_backup_path and os.path.exists(original_backup_path):
            try:
                shutil.copy2(original_backup_path, target_path)
            finally:
                try:
                    os.remove(original_backup_path)
                except Exception:
                    pass

    return artifacts


def _run_benchmark(dataset_dir: str, workload: str, threads: int, output_file: str) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {"run": {}}
    cmd = ["./ycsb", dataset_dir, workload, str(threads), output_file]
    proc = subprocess.run(cmd, cwd=BSKIP_DIR, capture_output=True, text=True)
    artifacts["run"]["rc"] = proc.returncode
    artifacts["run"]["stdout"] = proc.stdout
    artifacts["run"]["stderr"] = proc.stderr
    artifacts["run"]["cmd"] = " ".join(cmd)
    return artifacts


def _parse_throughput(stdout: str, prefix: str = "candidate") -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    # Example lines from ycsb.cpp
    # "\tMedian Load throughput: %f ,ops/us"
    # "\tMedian Run throughput: %f ,ops/us"
    # "\tRun, throughput: %f ,ops/us"
    median_load_match = re.search(r"Median Load throughput: ([\d\.]+) ,ops/us", stdout)
    median_run_match = re.search(r"Median Run throughput: ([\d\.]+) ,ops/us", stdout)
    run_samples = re.findall(r"Run, throughput: ([\d\.]+) ,ops/us", stdout)

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

    dataset_dir = os.environ.get("BSKIP_DATASET_DIR", "/Users/girigiri_yomi/Udel_Proj/bskip_artifact/bskiplist/data/uniform")
    workload = os.environ.get("BSKIP_WORKLOAD", "a")
    threads = int(os.environ.get("BSKIP_THREADS", "16"))
    output_file = os.environ.get("BSKIP_OUTPUT", os.path.join("results", "tmp.txt"))
    enable_latency = os.environ.get("BSKIP_LATENCY", "0") == "1"

    if not dataset_dir:
        artifacts["error"] = "BSKIP_DATASET_DIR not set. Cannot run ycsb without dataset."
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
        return EvaluationResult(metrics={"combined_score": 0.0, "baseline_runs_successfully": 0.0, "candidate_runs_successfully": 0.0}, artifacts=artifacts)

    base_run_art = _run_benchmark(dataset_dir=dataset_dir, workload=workload, threads=threads, output_file=output_file)
    artifacts.update({"baseline_run": base_run_art.get("run", {})})
    if base_run_art.get("run", {}).get("rc", 1) != 0:
        metrics.update({"baseline_runs_successfully": 0.0, "candidate_runs_successfully": 0.0, "combined_score": 0.0})
        return EvaluationResult(metrics=metrics, artifacts=artifacts)

    baseline_stdout = base_run_art.get("run", {}).get("stdout", "")
    baseline_metrics = _parse_throughput(baseline_stdout, prefix="baseline")
    metrics.update(baseline_metrics)
    metrics["baseline_runs_successfully"] = 1.0

    # Compile candidate and run
    try:
        cand_build_art = _compile_candidate(program_path, make_env=make_env)
        artifacts.update(cand_build_art)
    except Exception as e:
        artifacts["candidate_compile_error"] = str(e)
        # If candidate cannot compile, treat as no improvement
        metrics.update({"candidate_runs_successfully": 0.0, "combined_score": 0.0})
        return EvaluationResult(metrics=metrics, artifacts=artifacts)

    cand_run_art = _run_benchmark(dataset_dir=dataset_dir, workload=workload, threads=threads, output_file=output_file)
    artifacts.update(cand_run_art)
    if cand_run_art.get("run", {}).get("rc", 1) != 0:
        metrics.update({"candidate_runs_successfully": 0.0, "combined_score": 0.0})
        return EvaluationResult(metrics=metrics, artifacts=artifacts)

    candidate_stdout = cand_run_art.get("run", {}).get("stdout", "")
    candidate_metrics = _parse_throughput(candidate_stdout, prefix="candidate")
    metrics.update(candidate_metrics)
    metrics["candidate_runs_successfully"] = 1.0

    # Compute percentage speedup based on median run throughput (fallback to avg run)
    eps = 1e-12
    base_key = "baseline_median_run_ops_per_us" if "baseline_median_run_ops_per_us" in metrics else "baseline_avg_run_ops_per_us"
    cand_key = "candidate_median_run_ops_per_us" if "candidate_median_run_ops_per_us" in metrics else "candidate_avg_run_ops_per_us"
    base_val = float(metrics.get(base_key, 0.0))
    cand_val = float(metrics.get(cand_key, 0.0))
    if base_val > eps:
        percent_speedup = (cand_val - base_val) / base_val * 100.0
    else:
        percent_speedup = 0.0
    metrics["combined_score"] = float(percent_speedup)
    metrics["percent_speedup_run_throughput"] = float(percent_speedup)

    return EvaluationResult(metrics=metrics, artifacts=artifacts)


def evaluate_stage1(program_path: str) -> EvaluationResult:
    return evaluate(program_path)


