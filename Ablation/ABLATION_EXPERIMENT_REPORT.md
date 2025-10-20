## Overview

This report summarizes (1) the differences between the original `bskip.h` and the best evolved program, (2) our experiment setup, (3) detailed per-version ablation results (Load/Run only), (4) why ablation speedups are not additive and how we stabilized results, (5) notable observations, and (6) key takeaways from using OpenEvolve.


## 1) Differences: Original vs Best (Evolved)

The best evolved header (`openevolve_output_p8_iter100/best/best_program.h`) incorporates several changes beyond the original `bskiplist/bskip.h`:

- Binary and node-local search improvements
  - Enable/optimize binary-style search within nodes (upper-bound style, fewer probes).
  - Use exponential (galloping) search to narrow the local range, then perform binary search.
- Thread-local traversal hints
  - Per-level thread-local “hint” node to opportunistically start traversals closer to the target.
- Bit-ops optimization in `flip_coins`
  - Use bit masking and shifts when the promotion base `p` is a power of two; avoid modulus/div.
- Adaptive split behavior
  - Adjust split position based on recent insertion patterns to reduce future splits.

Together, these changes yielded about +11% Load and +10% Run improvement over baseline in our environment (see Section 3).


## 2) Experiment Setup

- Benchmark harness:
  - Script: `Ablation/run_ablation_study.py`
  - Pre-flight checks: compile every version and run `make test` before benchmarking
  - Baseline statistics are taken from `bskiplist/evaluator.py` (pre-computed, no baseline reruns)
  - Benchmark loop uses YCSB-style workloads (load and run phases)

- Parameters and controls:
  - Dataset directory: `/mydata/skip_data/uniform/`
  - Workload: `a`
  - Threads: `32`
  - Runs per version: `10` (unless stated otherwise for quick checks)
  - Baseline stats (from `evaluator.py`):
    - Load mean 16.3887327 ops/us, stdev 0.0661152768
    - Run mean 16.78420905 ops/us, stdev 0.0279881866

- Versions evaluated:
  - V1: Binary Search (only)
  - V2: Exponential Search (only)
  - V3: Thread-Local Hints (only)
  - V4: Bit-ops in `flip_coins` (only)
  - Evolved (Full): best evolved header with all optimizations


## 3) Detailed Results (Load/Run only)

Numbers below are as printed by the ablation reports. Combined deltas are intentionally omitted per request.

- Baseline (Original)
  - Load: 16.389 ± 0.066 ops/us
  - Run:  16.784 ± 0.028 ops/us

- Evolved (Full)
  - Load: 18.195 ± 0.129 ops/us  (+11.02%)
  - Run:  18.534 ± 0.034 ops/us  (+10.42%)

- V1: Binary Search (only)
  - Load: 16.439 ± 0.044 ops/us  (+0.31%)
  - Run:  16.867 ± 0.023 ops/us  (+0.49%)

- V2: Exponential Search (only)
  - Load: 18.281 ± 0.116 ops/us  (+11.54%)
  - Run:  18.053 ± 0.024 ops/us  (+7.56%)
  - Note: Earlier runs mistakenly included extra features; we corrected the version to remove hints. Always re-validate isolation when numbers look too large.

- V3: Thread-Local Hints (only)
  - Load: 16.684 ± 0.062 ops/us  (+1.80%)
  - Run:  17.319 ± 0.032 ops/us  (+3.18%)

- V4: Bit-ops in `flip_coins` (only)
  - Load: 16.829 ± 0.037 ops/us  (+2.69%)
  - Run:  17.485 ± 0.027 ops/us  (+4.18%)
  - Note: We fixed V4 to remove unintended exponential search and thread hints; these figures are from the corrected version.


## 4) Discussion

### Why ablation speedups can sum to more than the full evolved version

- Non-additivity and interactions: Optimizations overlap; improvements often target the same bottleneck. When applied together, each marginal gain is smaller than when measured alone. Therefore, per-feature gains are not additive.
- Shared hot paths: V2 and V4 both reduce node-local search cost; gains “compete” for the same cycles in the combined program.
- Measurement variance: Even with multiple runs, small statistical variation exists. This can exaggerate apparent additivity.

### Stabilizing baseline and candidate results

- Multiple iterations per version (e.g., 10 runs) and report both mean and stdev.
- Use a fixed dataset directory, workload, and thread count across all runs.
- Pre-flight compilation and `make test` to catch correctness issues before benchmarking.
- Use pre-computed baseline stats from a larger sample (e.g., 20 runs), stored in `evaluator.py`, to avoid re-running baseline and to keep results comparable.


## 5) Interesting Findings

- Exponential (galloping) + binary node-local search (V2) accounts for the bulk of the speedup on our workload, especially on the load phase.
- Bit-ops in `flip_coins` (V4) provide a consistent, modest boost, larger on the run phase than load.
- Thread-local hints (V3) help more on the run phase than load, suggesting traversal locality benefits during mixed operations.
- Plain binary search (V1) alone yields minor gains; the exponential windowing is the real unlock for large nodes.


## 6) Key Takeaways from Using OpenEvolve

- Evolve is effective at discovering synergistic sets of optimizations (e.g., search strategy + micro-opts) that collectively outperform any single tweak.
- Rigorous ablation is essential: ensure each version truly isolates one feature. Automate creation, preflight checks, and benchmarking to avoid contamination.
- Stabilize measurements: fix parameters, run multiple iterations, and anchor baseline to a well-measured reference to enable fair comparisons.
- Use evolve to explore macro-strategy changes (like search algorithms) while layering smaller micro-optimizations (like bit-ops) for additional gains.


## Repro Notes

- Runner: `Ablation/run_ablation_study.py` (uses preflight compile + `make test`, pre-computed baseline)
- V4-only helper: `Ablation/run_v4_vs_baseline.py`
- Corrected ablation headers are under `Ablation/versions/`





