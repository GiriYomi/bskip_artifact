#!/usr/bin/env python3
"""
Run YCSB for workloads a, b, c, e (3 times each) and report statistics.

Command executed per run (from bskiplist directory):
  ./ycsb /mydata/skip_data/uniform/ <workload> 32 out.txt

Statistics computed:
- For each workload: per-run medians, per-workload aggregates across all runs and samples
- Factors: count, min, max, mean, median, stdev, CV, p90, p95, p99

Notes:
- Baseline comparison has been removed to avoid using stale/incorrect references.
- Use --tag to annotate output directories per variant (e.g., original, p8A, p8E).
"""

import os
import re
import json
import statistics
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


BSKIPLIST_DIR = Path(__file__).parent / "bskiplist"
YCSB_BIN = BSKIPLIST_DIR / "ycsb"
DATASET_DIR = "/mydata/skip_data/uniform/"
WORKLOADS = ["a", "b", "c", "e"]
THREADS = 32

# Baseline comparison removed.


def compile_ycsb() -> None:
    print("=" * 80)
    print("Compiling YCSB once...")
    print("=" * 80)
    try:
        subprocess.run(["make", "clean"], cwd=BSKIPLIST_DIR, check=True, capture_output=True, text=True)
        subprocess.run(["make", "ycsb"], cwd=BSKIPLIST_DIR, check=True, capture_output=True, text=True)
        print("✓ Compilation successful")
    except subprocess.CalledProcessError as e:
        print("✗ Compilation failed")
        print("STDOUT:\n" + (e.stdout or ""))
        print("STDERR:\n" + (e.stderr or ""))
        raise


def _parse_output(stdout: str) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {
        "median_load": None,
        "median_run": None,
        "load_samples": [],
        "run_samples": [],
    }
    # Medians printed by ycsb.cpp
    m_load = re.search(r"Median Load throughput: ([\\d\\.]+) ,ops/us", stdout)
    m_run = re.search(r"Median Run throughput: ([\\d\\.]+) ,ops/us", stdout)
    if m_load:
        metrics["median_load"] = float(m_load.group(1))
    if m_run:
        metrics["median_run"] = float(m_run.group(1))

    # Samples printed per phase
    load_samples = re.findall(r"Load took \\d+ us, throughput = ([\\d\\.]+) ops/us", stdout)
    run_samples = re.findall(r"Run, throughput: ([\\d\\.]+) ,ops/us", stdout)
    metrics["load_samples"] = [float(x) for x in load_samples]
    metrics["run_samples"] = [float(x) for x in run_samples]
    return metrics


def _percentiles(sorted_vals: List[float]) -> Dict[str, float]:
    if not sorted_vals:
        return {"p90": 0.0, "p95": 0.0, "p99": 0.0}
    n = len(sorted_vals)
    def pct(p: float) -> float:
        if n == 0:
            return 0.0
        if p <= 0:
            return sorted_vals[0]
        if p >= 100:
            return sorted_vals[-1]
        import math
        rank = max(1, int(math.ceil((p / 100.0) * n)))
        return sorted_vals[rank - 1]
    return {
        "p90": pct(90),
        "p95": pct(95),
        "p99": pct(99),
    }


def compute_stats(vals: List[float]) -> Dict[str, float]:
    if not vals:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "stdev": 0.0,
            "cv": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }
    s = sorted(vals)
    count = len(vals)
    mean = statistics.fmean(vals)
    stdev = statistics.pstdev(vals)  # population stdev
    cv = (stdev / mean) if mean != 0 else 0.0
    pct = _percentiles(s)
    return {
        "count": float(count),
        "min": s[0],
        "max": s[-1],
        "mean": mean,
        "median": statistics.median(vals),
        "stdev": stdev,
        "cv": cv,
        **pct,
    }


def run_once(workload: str, run_idx: int, tag: str) -> Dict[str, Any]:
    out_txt = f"out_{workload}_{run_idx}.txt"
    cmd = [
        str(YCSB_BIN),
        DATASET_DIR,
        workload,
        str(THREADS),
        out_txt,
    ]
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=BSKIPLIST_DIR,
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.CalledProcessError as e:
        print(f"✗ Workload {workload} run {run_idx} failed")
        print("STDOUT:\n" + (e.stdout or ""))
        print("STDERR:\n" + (e.stderr or ""))
        return {}

    # Save raw output for inspection
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    tag_prefix = (tag.strip().replace(' ', '_') + "_") if tag else ""
    run_dir = Path("ycsb_benchmark_results") / f"{tag_prefix}run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / f"workload_{workload}_run_{run_idx:02d}.txt"
    with open(out_path, "w") as f:
        f.write("STDOUT\n")
        f.write(result.stdout)
        f.write("\n\nSTDERR\n")
        f.write(result.stderr)

    return _parse_output(result.stdout)


# Baseline comparison function removed.


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-workload YCSB benchmarks and summarize results.")
    parser.add_argument("--tag", default="", help="Optional tag used to prefix output directories (e.g., original, p8A, p8E).")
    args = parser.parse_args()
    # Ensure binary exists or compile
    if not YCSB_BIN.exists():
        compile_ycsb()
    else:
        print("YCSB binary found - skipping compilation. (Use 'make clean && make ycsb' to rebuild)")

    summary: Dict[str, Any] = {"workloads": {}, "timestamp": datetime.now().isoformat(), "tag": args.tag}

    for wl in WORKLOADS:
        print("\n" + "=" * 80)
        print(f"Workload {wl}: running 3 times")
        print("=" * 80)
        runs: List[Dict[str, Any]] = []
        median_loads: List[float] = []
        median_runs: List[float] = []
        all_load_samples: List[float] = []
        all_run_samples: List[float] = []

        for i in range(1, 4):
            res = run_once(wl, i, args.tag)
            if not res:
                continue
            runs.append(res)
            if res.get("median_load") is not None:
                median_loads.append(res["median_load"])
            if res.get("median_run") is not None:
                median_runs.append(res["median_run"])
            all_load_samples.extend(res.get("load_samples", []))
            all_run_samples.extend(res.get("run_samples", []))

        load_median_stats = compute_stats(median_loads)
        run_median_stats = compute_stats(median_runs)
        load_sample_stats = compute_stats(all_load_samples)
        run_sample_stats = compute_stats(all_run_samples)

        summary["workloads"][wl] = {
            "runs": runs,
            "median_per_run": {
                "load": load_median_stats,
                "run": run_median_stats,
            },
            "all_samples": {
                "load": load_sample_stats,
                "run": run_sample_stats,
            },
        }

        print(f"Load (samples): mean={load_sample_stats['mean']:.6f} ops/us, p95={load_sample_stats['p95']:.6f}, p99={load_sample_stats['p99']:.6f}")
        print(f"Run  (samples): mean={run_sample_stats['mean']:.6f} ops/us, p95={run_sample_stats['p95']:.6f}, p99={run_sample_stats['p99']:.6f}")

    # Save summary JSON
    ts2 = datetime.now().strftime('%Y%m%d_%H%M%S')
    tag_prefix2 = (summary.get("tag", "").strip().replace(' ', '_') + "_") if summary.get("tag") else ""
    out_dir = Path("ycsb_benchmark_results") / f"{tag_prefix2}multi_{ts2}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "summary.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print("\n" + "=" * 80)
    print(f"✓ Summary saved to: {out_json}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


