#!/usr/bin/env python3
"""
Run V4 (Bitops in flip_coins) against baseline using the ablation runner.

This script:
- Reuses AblationStudy from run_ablation_study.py
- Filters the versions list to only include V4
- Uses pre-computed baseline stats from evaluator.py (runner handles this)

Usage examples:
  python run_v4_vs_baseline.py -n 10
  python run_v4_vs_baseline.py -d /mydata/skip_data/uniform/ -w a -t 32
"""

import argparse
from pathlib import Path

from run_ablation_study import AblationStudy


def main():
    parser = argparse.ArgumentParser(
        description="Run V4 (Bitops in flip_coins) vs Baseline"
    )
    parser.add_argument("-n", "--num-runs", type=int, default=10,
                        help="Number of runs for V4 (default: 10)")
    parser.add_argument("-o", "--output-dir", default="ablation_results_v4",
                        help="Output directory for results (default: ablation_results_v4)")
    parser.add_argument("-d", "--dataset-dir", default="/mydata/skip_data/uniform/",
                        help="Dataset directory path (default: /mydata/skip_data/uniform/)")
    parser.add_argument("-w", "--workload", default="a", choices=list("abcdexy"),
                        help="YCSB workload to run (default: a)")
    parser.add_argument("-t", "--threads", type=int, default=32,
                        help="Number of threads to use (default: 32)")

    args = parser.parse_args()

    study = AblationStudy(
        num_runs=args.num_runs,
        output_dir=args.output_dir,
        dataset_dir=args.dataset_dir,
        workload=args.workload,
        num_threads=args.threads,
    )

    # Restrict to V4 only
    v4_file = study.versions_dir / "bskip_v4_bitops_flipcoins.h"
    study.versions = [
        {
            "id": "v4_bitops_flipcoins",
            "name": "V4: Bitops in flip_coins",
            "file": v4_file,
            "description": "Bit operations optimization in flip_coins",
        }
    ]

    success = study.run()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())





