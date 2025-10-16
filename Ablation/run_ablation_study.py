#!/usr/bin/env python3
"""
Ablation Study Runner for BSkip Optimizations
Runs benchmarks for each ablation version and compares against baseline.
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


class AblationStudy:
    def __init__(self, num_runs=10, output_dir="ablation_results",
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
        
        # Define versions to test
        self.versions = [
            {
                "id": "baseline",
                "name": "Baseline (Original)",
                "file": self.bskiplist_dir / "bskip.h",
                "description": "Original bskip.h without any optimizations"
            },
            {
                "id": "v1_binary_search",
                "name": "V1: Binary Search",
                "file": self.versions_dir / "bskip_v1_binary_search.h",
                "description": "Enable BINARY_SEARCH=1"
            },
            {
                "id": "v2_exponential_search",
                "name": "V2: Exponential Search",
                "file": self.versions_dir / "bskip_v2_exponential_search.h",
                "description": "Exponential + binary search strategy"
            },
            {
                "id": "v3_thread_hints",
                "name": "V3: Thread-Local Hints",
                "file": self.versions_dir / "bskip_v3_thread_hints.h",
                "description": "Thread-local hints for traversal"
            },
            {
                "id": "v4_bitops_flipcoins",
                "name": "V4: Bitops in flip_coins",
                "file": self.versions_dir / "bskip_v4_bitops_flipcoins.h",
                "description": "Bit operations optimization in flip_coins"
            },
            {
                "id": "v5_adaptive_split",
                "name": "V5: Adaptive Split",
                "file": self.versions_dir / "bskip_v5_adaptive_split.h",
                "description": "Adaptive split + other micro-opts"
            },
            {
                "id": "evolved_full",
                "name": "Evolved (Full)",
                "file": self.base_dir / "openevolve_output_p8_iter100" / "best" / "best_program.h",
                "description": "Full evolved version with all optimizations"
            }
        ]
        
        # Storage for results
        self.results = {}
    
    def check_prerequisites(self):
        """Check if all necessary files exist"""
        print("=" * 80)
        print("Step 1: Checking Prerequisites")
        print("=" * 80)
        
        # Check versions directory exists
        if not self.versions_dir.exists():
            print(f"✗ Versions directory not found: {self.versions_dir}")
            print(f"\nPlease run 'python create_ablation_versions.py' first!")
            return False
        
        print(f"✓ Versions directory found: {self.versions_dir}")
        
        # Check each version file exists
        missing_files = []
        for version in self.versions:
            if not version["file"].exists():
                print(f"  ✗ {version['id']}: {version['file']} - NOT FOUND")
                missing_files.append(version["id"])
            else:
                print(f"  ✓ {version['id']}: {version['name']}")
        
        if missing_files:
            print(f"\n✗ Missing version files!")
            print(f"\nPlease run 'python create_ablation_versions.py' to generate them.")
            return False
        
        # Check dataset files
        dataset_path = Path(self.dataset_dir)
        if not dataset_path.is_absolute():
            dataset_path = self.bskiplist_dir / self.dataset_dir
        
        workload_files = {
            'a': ('loada_unif_int.dat', 'txnsa_unif_int.dat'),
        }
        
        load_file, txn_file = workload_files.get(self.workload, (None, None))
        if not load_file:
            print(f"✗ Unknown workload: {self.workload}")
            return False
        
        load_path = dataset_path / load_file
        txn_path = dataset_path / txn_file
        
        if not load_path.exists() or not txn_path.exists():
            print(f"\n✗ Dataset files not found:")
            print(f"  {load_path}")
            print(f"  {txn_path}")
            return False
        
        print(f"\n✓ Dataset files found")
        print(f"  {load_path}")
        print(f"  {txn_path}")
        
        return True
    
    def backup_original_bskip(self):
        """Backup the original bskip.h"""
        backup_file = self.bskiplist_dir / "bskip_original_backup.h"
        original_file = self.bskiplist_dir / "bskip.h"
        
        if not backup_file.exists():
            shutil.copy2(original_file, backup_file)
            print(f"✓ Backed up original bskip.h to: {backup_file}")
        else:
            print(f"✓ Backup already exists: {backup_file}")
    
    def restore_original_bskip(self):
        """Restore the original bskip.h"""
        backup_file = self.bskiplist_dir / "bskip_original_backup.h"
        original_file = self.bskiplist_dir / "bskip.h"
        
        if backup_file.exists():
            shutil.copy2(backup_file, original_file)
            print(f"✓ Restored original bskip.h from backup")
    
    def switch_to_version(self, version_file):
        """Switch bskip.h to a specific version"""
        target_file = self.bskiplist_dir / "bskip.h"
        shutil.copy2(version_file, target_file)
    
    def compile_ycsb(self, version_id):
        """Compile YCSB for current version"""
        try:
            # Clean
            subprocess.run(
                ["make", "clean"],
                cwd=self.bskiplist_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Compile
            result = subprocess.run(
                ["make", "ycsb"],
                cwd=self.bskiplist_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Save compilation log
            compile_log = self.run_dir / f"{version_id}_compilation.log"
            with open(compile_log, 'w') as f:
                f.write(f"Compilation for {version_id}\n")
                f.write("=" * 80 + "\n\n")
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Compilation failed!")
            error_log = self.run_dir / f"{version_id}_compilation_error.log"
            with open(error_log, 'w') as f:
                f.write(f"Compilation failed for {version_id}\n")
                f.write(f"Error: {e}\n")
                f.write(f"\nSTDOUT:\n{e.stdout}\n")
                f.write(f"\nSTDERR:\n{e.stderr}\n")
            return False
        
        except subprocess.TimeoutExpired:
            print(f"  ✗ Compilation timeout!")
            return False
    
    def parse_ycsb_output(self, output):
        """Parse YCSB output to extract metrics"""
        metrics = {
            'median_load': None,
            'median_run': None,
            'load_samples': [],
            'run_samples': []
        }
        
        # Extract median throughputs
        median_load_match = re.search(r"Median Load throughput: ([\d\.]+) ,ops/us", output)
        median_run_match = re.search(r"Median Run throughput: ([\d\.]+) ,ops/us", output)
        
        if median_load_match:
            metrics['median_load'] = float(median_load_match.group(1))
        
        if median_run_match:
            metrics['median_run'] = float(median_run_match.group(1))
        
        # Extract all samples
        load_samples = re.findall(r"Load took \d+ us, throughput = ([\d\.]+) ops/us", output)
        metrics['load_samples'] = [float(x) for x in load_samples]
        
        run_samples = re.findall(r"Run, throughput: ([\d\.]+) ,ops/us", output)
        metrics['run_samples'] = [float(x) for x in run_samples]
        
        return metrics
    
    def run_ycsb_once(self, version_id, run_number):
        """Run YCSB once for a specific version"""
        ycsb_binary = self.bskiplist_dir / "ycsb"
        output_file = f"{version_id}_run_{run_number:02d}.txt"
        
        cmd = [
            str(ycsb_binary),
            self.dataset_dir,
            self.workload,
            str(self.num_threads),
            output_file
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.bskiplist_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # Save output
            output_path = self.run_dir / version_id / f"run_{run_number:02d}.txt"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(f"{version_id} - Run {run_number}\n")
                f.write("=" * 80 + "\n\n")
                f.write(result.stdout)
            
            # Parse metrics
            metrics = self.parse_ycsb_output(result.stdout)
            
            # Save metrics
            metrics_file = self.run_dir / version_id / f"run_{run_number:02d}_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            return metrics
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            error_file = self.run_dir / version_id / f"run_{run_number:02d}_error.txt"
            error_file.parent.mkdir(parents=True, exist_ok=True)
            with open(error_file, 'w') as f:
                f.write(f"Run {run_number} failed: {e}\n")
            return None
    
    def benchmark_version(self, version):
        """Benchmark a single version"""
        version_id = version["id"]
        version_name = version["name"]
        version_file = version["file"]
        
        print(f"\n{'=' * 80}")
        print(f"Benchmarking: {version_name}")
        print(f"{'=' * 80}")
        print(f"Version ID: {version_id}")
        print(f"Description: {version['description']}")
        print(f"File: {version_file}")
        
        # Switch to this version
        print(f"\nSwitching to {version_id}...")
        self.switch_to_version(version_file)
        
        # Compile
        print(f"Compiling {version_id}...")
        if not self.compile_ycsb(version_id):
            print(f"✗ Failed to compile {version_id}")
            return None
        print(f"✓ Compilation successful")
        
        # Run benchmarks
        print(f"\nRunning {self.num_runs} benchmark iterations:")
        load_throughputs = []
        run_throughputs = []
        all_load_samples = []
        all_run_samples = []
        
        for i in range(1, self.num_runs + 1):
            print(f"  Run {i}/{self.num_runs}...", end=" ", flush=True)
            metrics = self.run_ycsb_once(version_id, i)
            
            if metrics and metrics['median_load'] and metrics['median_run']:
                load_throughputs.append(metrics['median_load'])
                run_throughputs.append(metrics['median_run'])
                all_load_samples.extend(metrics['load_samples'])
                all_run_samples.extend(metrics['run_samples'])
                print(f"✓ Load: {metrics['median_load']:.3f}, Run: {metrics['median_run']:.3f} ops/us")
            else:
                print(f"✗ Failed")
        
        if not load_throughputs:
            print(f"✗ All runs failed for {version_id}")
            return None
        
        # Calculate statistics
        stats = VersionStats(
            version_id=version_id,
            version_name=version_name,
            num_runs=len(load_throughputs),
            load_mean=statistics.mean(load_throughputs),
            load_median=statistics.median(load_throughputs),
            load_stdev=statistics.stdev(load_throughputs) if len(load_throughputs) > 1 else 0,
            run_mean=statistics.mean(run_throughputs),
            run_median=statistics.median(run_throughputs),
            run_stdev=statistics.stdev(run_throughputs) if len(run_throughputs) > 1 else 0,
            all_load_samples=all_load_samples,
            all_run_samples=all_run_samples
        )
        
        print(f"\n✓ {version_name} completed:")
        print(f"  Load:  {stats.load_mean:.3f} ± {stats.load_stdev:.3f} ops/us")
        print(f"  Run:   {stats.run_mean:.3f} ± {stats.run_stdev:.3f} ops/us")
        
        return stats
    
    def run_all_benchmarks(self):
        """Run benchmarks for all versions"""
        print("\n" + "=" * 80)
        print(f"Step 2: Running Ablation Study ({self.num_runs} runs per version)")
        print("=" * 80)
        
        # Backup original
        self.backup_original_bskip()
        
        try:
            for version in self.versions:
                stats = self.benchmark_version(version)
                if stats:
                    self.results[version["id"]] = stats
                else:
                    print(f"Warning: Skipping {version['id']} due to failures")
        
        finally:
            # Always restore original
            print(f"\n{'=' * 80}")
            print("Restoring original bskip.h...")
            self.restore_original_bskip()
            print("=" * 80)
        
        return len(self.results) > 0
    
    def calculate_improvement(self, baseline_value, test_value):
        """Calculate percentage improvement"""
        if baseline_value == 0:
            return 0
        return ((test_value - baseline_value) / baseline_value) * 100
    
    def generate_comparison_report(self):
        """Generate comparison report against baseline"""
        print("\n" + "=" * 80)
        print("Step 3: Generating Comparison Report")
        print("=" * 80)
        
        if "baseline" not in self.results:
            print("✗ Baseline results not found!")
            return
        
        baseline = self.results["baseline"]
        
        # Create comparison table
        comparison_data = []
        
        for version_id, stats in self.results.items():
            if version_id == "baseline":
                continue
            
            load_improvement = self.calculate_improvement(baseline.load_mean, stats.load_mean)
            run_improvement = self.calculate_improvement(baseline.run_mean, stats.run_mean)
            combined = (load_improvement + run_improvement) / 2
            
            comparison_data.append({
                "version_id": version_id,
                "version_name": stats.version_name,
                "load_mean": stats.load_mean,
                "load_stdev": stats.load_stdev,
                "run_mean": stats.run_mean,
                "run_stdev": stats.run_stdev,
                "load_improvement_pct": load_improvement,
                "run_improvement_pct": run_improvement,
                "combined_improvement_pct": combined
            })
        
        # Sort by combined improvement
        comparison_data.sort(key=lambda x: x["combined_improvement_pct"], reverse=True)
        
        # Print comparison table
        print("\nPerformance Comparison vs Baseline")
        print("=" * 120)
        print(f"{'Version':<30} {'Load (ops/us)':<20} {'Run (ops/us)':<20} {'Load Δ%':<12} {'Run Δ%':<12} {'Combined Δ%':<12}")
        print("=" * 120)
        
        # Baseline first
        print(f"{'Baseline (Original)':<30} {baseline.load_mean:>8.3f} ± {baseline.load_stdev:<6.3f} "
              f"{baseline.run_mean:>8.3f} ± {baseline.run_stdev:<6.3f} "
              f"{'0.00%':>10} {'0.00%':>10} {'0.00%':>10}")
        print("-" * 120)
        
        # Other versions
        for item in comparison_data:
            load_sign = "+" if item["load_improvement_pct"] >= 0 else ""
            run_sign = "+" if item["run_improvement_pct"] >= 0 else ""
            combined_sign = "+" if item["combined_improvement_pct"] >= 0 else ""
            
            print(f"{item['version_name']:<30} "
                  f"{item['load_mean']:>8.3f} ± {item['load_stdev']:<6.3f} "
                  f"{item['run_mean']:>8.3f} ± {item['run_stdev']:<6.3f} "
                  f"{load_sign}{item['load_improvement_pct']:>9.2f}% "
                  f"{run_sign}{item['run_improvement_pct']:>9.2f}% "
                  f"{combined_sign}{item['combined_improvement_pct']:>9.2f}%")
        
        print("=" * 120)
        
        # Save detailed report
        report_file = self.run_dir / "ABLATION_REPORT.txt"
        with open(report_file, 'w') as f:
            f.write("=" * 120 + "\n")
            f.write("ABLATION STUDY REPORT\n")
            f.write("=" * 120 + "\n\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Runs per version: {self.num_runs}\n")
            f.write(f"Workload: {self.workload}\n")
            f.write(f"Threads: {self.num_threads}\n")
            f.write(f"Dataset: {self.dataset_dir}\n\n")
            
            f.write("=" * 120 + "\n")
            f.write("BASELINE PERFORMANCE\n")
            f.write("=" * 120 + "\n")
            f.write(f"Load Throughput:  {baseline.load_mean:.6f} ± {baseline.load_stdev:.6f} ops/us\n")
            f.write(f"Run Throughput:   {baseline.run_mean:.6f} ± {baseline.run_stdev:.6f} ops/us\n\n")
            
            f.write("=" * 120 + "\n")
            f.write("OPTIMIZATION IMPACT (Ranked by Combined Improvement)\n")
            f.write("=" * 120 + "\n\n")
            
            for i, item in enumerate(comparison_data, 1):
                f.write(f"{i}. {item['version_name']}\n")
                f.write(f"   Version ID: {item['version_id']}\n")
                f.write(f"   Load:  {item['load_mean']:.6f} ± {item['load_stdev']:.6f} ops/us "
                       f"({item['load_improvement_pct']:+.2f}%)\n")
                f.write(f"   Run:   {item['run_mean']:.6f} ± {item['run_stdev']:.6f} ops/us "
                       f"({item['run_improvement_pct']:+.2f}%)\n")
                f.write(f"   Combined Improvement: {item['combined_improvement_pct']:+.2f}%\n\n")
        
        print(f"\n✓ Detailed report saved to: {report_file}")
        
        # Save JSON data
        json_data = {
            "timestamp": self.timestamp,
            "configuration": {
                "num_runs": self.num_runs,
                "workload": self.workload,
                "threads": self.num_threads,
                "dataset_dir": self.dataset_dir
            },
            "baseline": {
                "load_mean": baseline.load_mean,
                "load_median": baseline.load_median,
                "load_stdev": baseline.load_stdev,
                "run_mean": baseline.run_mean,
                "run_median": baseline.run_median,
                "run_stdev": baseline.run_stdev
            },
            "versions": comparison_data
        }
        
        json_file = self.run_dir / "ablation_results.json"
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"✓ JSON data saved to: {json_file}")
        
        return comparison_data
    
    def run(self):
        """Main execution flow"""
        print("\n" + "=" * 80)
        print("ABLATION STUDY RUNNER")
        print("=" * 80)
        print(f"Configuration:")
        print(f"  Runs per version: {self.num_runs}")
        print(f"  Total versions: {len(self.versions)}")
        print(f"  Dataset: {self.dataset_dir}")
        print(f"  Workload: {self.workload}")
        print(f"  Threads: {self.num_threads}")
        print(f"  Output directory: {self.run_dir}")
        print("=" * 80)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n✗ Prerequisites check failed. Exiting.")
            return False
        
        # Run benchmarks
        if not self.run_all_benchmarks():
            print("\n✗ Benchmark execution failed. Exiting.")
            return False
        
        # Generate report
        self.generate_comparison_report()
        
        print("\n" + "=" * 80)
        print("✓ ABLATION STUDY COMPLETE")
        print("=" * 80)
        print(f"\nAll results saved in: {self.run_dir}")
        print(f"  - Ablation report: {self.run_dir / 'ABLATION_REPORT.txt'}")
        print(f"  - JSON data: {self.run_dir / 'ablation_results.json'}")
        print(f"  - Individual runs: {self.run_dir}")
        print("=" * 80 + "\n")
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run ablation study for BSkip optimizations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (10 runs per version)
  python run_ablation_study.py
  
  # Run 20 times per version
  python run_ablation_study.py -n 20
  
  # Use different dataset directory
  python run_ablation_study.py -d /path/to/datasets/uniform/
  
  # Run with 64 threads
  python run_ablation_study.py -t 64

Before running:
  1. Ensure you have run 'python create_ablation_versions.py' first
  2. Make sure dataset files exist in the specified directory
        """
    )
    
    parser.add_argument(
        '-n', '--num-runs',
        type=int,
        default=10,
        help='Number of runs per version (default: 10)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='ablation_results',
        help='Output directory for results (default: ablation_results)'
    )
    
    parser.add_argument(
        '-d', '--dataset-dir',
        type=str,
        default='/mydata/skip_data/uniform/',
        help='Dataset directory path (default: /mydata/skip_data/uniform/)'
    )
    
    parser.add_argument(
        '-w', '--workload',
        type=str,
        default='a',
        choices=['a', 'b', 'c', 'd', 'e', 'x', 'y'],
        help='YCSB workload to run (default: a)'
    )
    
    parser.add_argument(
        '-t', '--threads',
        type=int,
        default=32,
        help='Number of threads to use (default: 32)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.num_runs < 1:
        print("Error: Number of runs must be at least 1")
        return 1
    
    if args.threads < 1:
        print("Error: Number of threads must be at least 1")
        return 1
    
    # Run ablation study
    study = AblationStudy(
        num_runs=args.num_runs,
        output_dir=args.output_dir,
        dataset_dir=args.dataset_dir,
        workload=args.workload,
        num_threads=args.threads
    )
    
    success = study.run()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())

