#!/usr/bin/env python3
"""
Test V4 (Bit-ops in flip_coins) vs Baseline
Similar to run_ycsb_benchmark.py but focused on single version comparison
"""

import os
import subprocess
import re
import json
import statistics
import shutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class BenchmarkMetrics:
    """Store benchmark metrics for a single run"""
    median_load: float
    median_run: float
    load_samples: List[float]
    run_samples: List[float]


@dataclass
class VersionStats:
    """Statistics for a version"""
    version_id: str
    version_name: str
    num_runs: int
    load_mean: float
    load_median: float
    load_stdev: float
    run_mean: float
    run_median: float
    run_stdev: float
    all_load_samples: List[float]
    all_run_samples: List[float]


class V4BitopsTester:
    def __init__(self, num_runs=10, output_dir="v4_test_results",
                 dataset_dir="/mydata/skip_data/uniform/", workload="a", num_threads=32):
        self.num_runs = num_runs
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.timestamp}"
        
        # YCSB configuration
        self.dataset_dir = dataset_dir
        self.workload = workload
        self.num_threads = num_threads
        
        # Paths
        self.script_dir = Path(__file__).parent
        self.base_dir = self.script_dir.parent
        self.bskiplist_dir = self.base_dir / "bskiplist"
        self.versions_dir = self.script_dir / "versions"
        
        # Create output directories
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Baseline data from evaluator.py
        self.baseline_stats = {
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
        
        # V4 version info
        self.v4_file = self.versions_dir / "bskip_v4_bitops_flipcoins.h"
        
        # Storage for results
        self.results = {}
    
    def check_prerequisites(self):
        """Check if all necessary files exist"""
        print("=" * 80)
        print("Checking Prerequisites")
        print("=" * 80)
        
        # Check V4 file exists
        if not self.v4_file.exists():
            print(f"❌ V4 file not found: {self.v4_file}")
            return False
        print(f"✓ V4 file found: {self.v4_file}")
        
        # Check dataset files
        load_file = Path(self.dataset_dir) / f"load{self.workload}_unif_int.dat"
        txn_file = Path(self.dataset_dir) / f"txns{self.workload}_unif_int.dat"
        
        if not load_file.exists():
            print(f"❌ Load dataset not found: {load_file}")
            return False
        if not txn_file.exists():
            print(f"❌ Transaction dataset not found: {txn_file}")
            return False
            
        print(f"✓ Dataset files found")
        print(f"  {load_file}")
        print(f"  {txn_file}")
        
        return True
    
    def backup_original_bskip(self):
        """Backup original bskip.h"""
        original_file = self.bskiplist_dir / "bskip.h"
        backup_file = self.bskiplist_dir / "bskip_original_backup.h"
        
        if not backup_file.exists():
            shutil.copy2(original_file, backup_file)
            print(f"✓ Backed up original bskip.h to: {backup_file}")
        else:
            print(f"✓ Backup already exists: {backup_file}")
    
    def switch_to_v4(self):
        """Switch to V4 version"""
        target_file = self.bskiplist_dir / "bskip.h"
        
        # Resolve paths to handle symlinks and relative paths
        v4_file_resolved = self.v4_file.resolve()
        target_file_resolved = target_file.resolve()
        
        # Skip copy if source and target are the same
        if v4_file_resolved == target_file_resolved:
            print(f"  (Already using V4 version, no copy needed)")
            return
        
        shutil.copy2(self.v4_file, target_file)
        print(f"✓ Switched to V4: {self.v4_file.name}")
    
    def compile_version(self):
        """Compile the current version"""
        print(f"  Compiling...")
        try:
            result = subprocess.run(
                "make clean && make -j4",
                cwd=self.bskiplist_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"  ✓ Compilation successful")
                return True
            else:
                print(f"  ✗ Compilation failed:")
                print(f"    stdout: {result.stdout}")
                print(f"    stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ✗ Compilation timed out")
            return False
        except Exception as e:
            print(f"  ✗ Compilation error: {e}")
            return False
    
    def run_single_benchmark(self, run_num):
        """Run a single benchmark iteration"""
        print(f"  Run {run_num}/{self.num_runs}...", end=" ")
        
        try:
            # Run YCSB benchmark
            cmd = [
                str(self.bskiplist_dir / "ycsb"),
                "-load_file", str(Path(self.dataset_dir) / f"load{self.workload}_unif_int.dat"),
                "-run_file", str(Path(self.dataset_dir) / f"txns{self.workload}_unif_int.dat"),
                "-threads", str(self.num_threads)
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.bskiplist_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                print(f"✗ Failed (exit code {result.returncode})")
                print(f"    stderr: {result.stderr}")
                return None
            
            # Parse output for performance metrics
            output = result.stdout
            
            # Extract load performance
            load_match = re.search(r'Load: (\d+\.\d+) ops/us', output)
            if not load_match:
                print(f"✗ Could not parse load performance")
                return None
            load_ops = float(load_match.group(1))
            
            # Extract run performance  
            run_match = re.search(r'Run: (\d+\.\d+) ops/us', output)
            if not run_match:
                print(f"✗ Could not parse run performance")
                return None
            run_ops = float(run_match.group(1))
            
            print(f"✓ Load: {load_ops:.3f}, Run: {run_ops:.3f} ops/us")
            return BenchmarkMetrics(load_ops, run_ops, [load_ops], [run_ops])
            
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout")
            return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
    
    def benchmark_v4(self):
        """Run benchmarks for V4"""
        print("\n" + "=" * 80)
        print("Benchmarking V4: Bit-ops in flip_coins")
        print("=" * 80)
        
        # Switch to V4
        self.switch_to_v4()
        
        # Compile
        if not self.compile_version():
            print("❌ Compilation failed. Aborting.")
            return None
        
        # Run benchmarks
        print(f"\nRunning {self.num_runs} benchmark iterations:")
        all_load_samples = []
        all_run_samples = []
        
        for i in range(1, self.num_runs + 1):
            metrics = self.run_single_benchmark(i)
            if metrics:
                all_load_samples.extend(metrics.load_samples)
                all_run_samples.extend(metrics.run_samples)
            else:
                print(f"Warning: Run {i} failed, skipping")
        
        if not all_load_samples:
            print("❌ All benchmark runs failed")
            return None
        
        # Calculate statistics
        load_mean = statistics.mean(all_load_samples)
        load_median = statistics.median(all_load_samples)
        load_stdev = statistics.stdev(all_load_samples) if len(all_load_samples) > 1 else 0.0
        
        run_mean = statistics.mean(all_run_samples)
        run_median = statistics.median(all_run_samples)
        run_stdev = statistics.stdev(all_run_samples) if len(all_run_samples) > 1 else 0.0
        
        stats = VersionStats(
            version_id="v4_bitops_flipcoins",
            version_name="V4: Bit-ops in flip_coins",
            num_runs=len(all_load_samples),
            load_mean=load_mean,
            load_median=load_median,
            load_stdev=load_stdev,
            run_mean=run_mean,
            run_median=run_median,
            run_stdev=run_stdev,
            all_load_samples=all_load_samples,
            all_run_samples=all_run_samples
        )
        
        print(f"\n✓ V4: Bit-ops in flip_coins completed:")
        print(f"  Load:  {stats.load_mean:.3f} ± {stats.load_stdev:.3f} ops/us")
        print(f"  Run:   {stats.run_mean:.3f} ± {stats.run_stdev:.3f} ops/us")
        
        return stats
    
    def generate_comparison_report(self, v4_stats):
        """Generate comparison report between V4 and baseline"""
        print("\n" + "=" * 80)
        print("Generating Comparison Report")
        print("=" * 80)
        
        # Calculate improvements
        load_improvement = ((v4_stats.load_mean - self.baseline_stats['load']['mean']) / 
                           self.baseline_stats['load']['mean']) * 100
        run_improvement = ((v4_stats.run_mean - self.baseline_stats['run']['mean']) / 
                          self.baseline_stats['run']['mean']) * 100
        combined_improvement = (load_improvement + run_improvement) / 2
        
        # Generate report
        report_lines = [
            "V4 Bit-ops in flip_coins vs Baseline Comparison",
            "=" * 60,
            "",
            f"Baseline (Original):",
            f"  Load: {self.baseline_stats['load']['mean']:.6f} ± {self.baseline_stats['load']['stdev']:.6f} ops/us",
            f"  Run:  {self.baseline_stats['run']['mean']:.6f} ± {self.baseline_stats['run']['stdev']:.6f} ops/us",
            "",
            f"V4 (Bit-ops in flip_coins):",
            f"  Load: {v4_stats.load_mean:.6f} ± {v4_stats.load_stdev:.6f} ops/us",
            f"  Run:  {v4_stats.run_mean:.6f} ± {v4_stats.run_stdev:.6f} ops/us",
            "",
            "Performance Improvement:",
            f"  Load:  {load_improvement:+.2f}%",
            f"  Run:   {run_improvement:+.2f}%", 
            f"  Combined: {combined_improvement:+.2f}%",
            "",
            f"Runs: {v4_stats.num_runs}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        # Save report
        report_file = self.run_dir / "V4_COMPARISON_REPORT.txt"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"✓ Report saved to: {report_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)
        print(f"{'Version':<25} {'Load (ops/us)':<20} {'Run (ops/us)':<20} {'Load Δ%':<10} {'Run Δ%':<10}")
        print("-" * 60)
        print(f"{'Baseline (Original)':<25} {self.baseline_stats['load']['mean']:.3f} ± {self.baseline_stats['load']['stdev']:.3f} {self.baseline_stats['run']['mean']:.3f} ± {self.baseline_stats['run']['stdev']:.3f} {'0.00%':<10} {'0.00%':<10}")
        print(f"{'V4: Bit-ops in flip_coins':<25} {v4_stats.load_mean:.3f} ± {v4_stats.load_stdev:.3f} {v4_stats.run_mean:.3f} ± {v4_stats.run_stdev:.3f} {load_improvement:+.2f}% {run_improvement:+.2f}%")
        print("=" * 60)
        
        # Save JSON data
        json_data = {
            "baseline": self.baseline_stats,
            "v4_bitops": {
                "load_mean": v4_stats.load_mean,
                "load_median": v4_stats.load_median,
                "load_stdev": v4_stats.load_stdev,
                "run_mean": v4_stats.run_mean,
                "run_median": v4_stats.run_median,
                "run_stdev": v4_stats.run_stdev,
                "num_runs": v4_stats.num_runs,
                "load_samples": v4_stats.all_load_samples,
                "run_samples": v4_stats.all_run_samples
            },
            "improvements": {
                "load_improvement_pct": load_improvement,
                "run_improvement_pct": run_improvement,
                "combined_improvement_pct": combined_improvement
            },
            "metadata": {
                "timestamp": self.timestamp,
                "num_runs": v4_stats.num_runs,
                "workload": self.workload,
                "threads": self.num_threads
            }
        }
        
        json_file = self.run_dir / "v4_comparison.json"
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"✓ JSON data saved to: {json_file}")
        
        return {
            "load_improvement": load_improvement,
            "run_improvement": run_improvement,
            "combined_improvement": combined_improvement
        }
    
    def restore_original(self):
        """Restore original bskip.h"""
        backup_file = self.bskiplist_dir / "bskip_original_backup.h"
        target_file = self.bskiplist_dir / "bskip.h"
        
        if backup_file.exists():
            shutil.copy2(backup_file, target_file)
            print(f"✓ Restored original bskip.h from backup")
        else:
            print(f"⚠️  No backup found, original bskip.h may be modified")
    
    def run(self):
        """Main execution flow"""
        print("\n" + "=" * 80)
        print("V4 BIT-OPS IN FLIP_COINS TESTER")
        print("=" * 80)
        print(f"Configuration:")
        print(f"  Runs: {self.num_runs}")
        print(f"  Dataset: {self.dataset_dir}")
        print(f"  Workload: {self.workload}")
        print(f"  Threads: {self.num_threads}")
        print(f"  Output directory: {self.run_dir}")
        print("=" * 80)
        
        try:
            # Check prerequisites
            if not self.check_prerequisites():
                print("\n✗ Prerequisites check failed. Exiting.")
                return False
            
            # Backup original
            self.backup_original_bskip()
            
            # Benchmark V4
            v4_stats = self.benchmark_v4()
            if not v4_stats:
                print("\n✗ V4 benchmarking failed. Exiting.")
                return False
            
            # Generate comparison report
            comparison = self.generate_comparison_report(v4_stats)
            
            print("\n" + "=" * 80)
            print("✓ V4 TESTING COMPLETE")
            print("=" * 80)
            print(f"Combined improvement: {comparison['combined_improvement']:+.2f}%")
            print(f"All results saved in: {self.run_dir}")
            
            return True
            
        finally:
            # Always restore original
            print(f"\n{'=' * 80}")
            print("Restoring original bskip.h...")
            self.restore_original()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test V4 (Bit-ops in flip_coins) vs Baseline')
    parser.add_argument('-n', '--num-runs', type=int, default=10,
                        help='Number of runs (default: 10)')
    parser.add_argument('-o', '--output-dir', default='v4_test_results',
                        help='Output directory for results (default: v4_test_results)')
    parser.add_argument('-d', '--dataset-dir', default='/mydata/skip_data/uniform/',
                        help='Dataset directory path (default: /mydata/skip_data/uniform/)')
    parser.add_argument('-w', '--workload', choices=['a', 'b', 'c', 'd', 'e', 'x', 'y'], default='a',
                        help='YCSB workload to run (default: a)')
    parser.add_argument('-t', '--threads', type=int, default=32,
                        help='Number of threads to use (default: 32)')
    
    args = parser.parse_args()
    
    tester = V4BitopsTester(
        num_runs=args.num_runs,
        output_dir=args.output_dir,
        dataset_dir=args.dataset_dir,
        workload=args.workload,
        num_threads=args.threads
    )
    
    success = tester.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
