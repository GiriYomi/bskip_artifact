#!/usr/bin/env python3
"""
Baseline vs Evolved Comparison Script
Runs YCSB workload E with baseline bskip.h and evolved best_program.h,
then compares the results.
"""

import os
import subprocess
import re
import json
import statistics
import shutil
from datetime import datetime
from pathlib import Path


class BaselineEvolvedComparison:
    def __init__(self, num_runs=5, output_dir="baseline_evolved_comparison", 
                 dataset_dir="/mydata/skip_data/uniform/", workload="e", num_threads=32):
        self.num_runs = num_runs
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.timestamp}"
        
        # YCSB configuration
        self.dataset_dir = dataset_dir
        self.workload = workload
        self.num_threads = num_threads
        
        # File paths
        self.bskiplist_dir = Path(__file__).parent / "bskiplist"
        self.baseline_file = self.bskiplist_dir / "bskip.h"
        self.evolved_file = Path(__file__).parent / "EvolveResult" / "result_trace_complex_prompt_iter100" / "best" / "best_program.h"
        self.backup_file = self.bskiplist_dir / "bskip_backup.h"
        
        # Create output directories
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_dir = self.run_dir / "baseline_runs"
        self.evolved_dir = self.run_dir / "evolved_runs"
        self.baseline_dir.mkdir(exist_ok=True)
        self.evolved_dir.mkdir(exist_ok=True)
        
        # Storage for metrics
        self.baseline_results = {
            'load_throughputs': [],
            'run_throughputs': [],
            'all_load_samples': [],
            'all_run_samples': []
        }
        
        self.evolved_results = {
            'load_throughputs': [],
            'run_throughputs': [],
            'all_load_samples': [],
            'all_run_samples': []
        }
    
    def backup_baseline(self):
        """Backup the original bskip.h"""
        print(f"Backing up baseline bskip.h to {self.backup_file}...")
        shutil.copy2(self.baseline_file, self.backup_file)
        print("✓ Backup created")
    
    def restore_baseline(self):
        """Restore the original bskip.h from backup"""
        if self.backup_file.exists():
            print(f"Restoring baseline bskip.h from backup...")
            shutil.copy2(self.backup_file, self.baseline_file)
            print("✓ Baseline restored")
            # Remove backup
            self.backup_file.unlink()
    
    def use_evolved_version(self):
        """Replace bskip.h with evolved best_program.h"""
        print(f"Replacing bskip.h with evolved version from {self.evolved_file}...")
        if not self.evolved_file.exists():
            print(f"✗ Evolved file not found: {self.evolved_file}")
            return False
        shutil.copy2(self.evolved_file, self.baseline_file)
        print("✓ Evolved version installed")
        return True
    
    def check_dataset_files(self):
        """Check if required dataset files exist"""
        print("=" * 80)
        print("Checking dataset files...")
        print("=" * 80)
        
        # Handle both absolute and relative paths
        if Path(self.dataset_dir).is_absolute():
            dataset_path = Path(self.dataset_dir)
        else:
            dataset_path = self.bskiplist_dir / self.dataset_dir
        
        # Expected files based on workload
        workload_files = {
            'a': ('loada_unif_int.dat', 'txnsa_unif_int.dat'),
            'b': ('loadb_unif_int.dat', 'txnsb_unif_int.dat'),
            'c': ('loadc_unif_int.dat', 'txnsc_unif_int.dat'),
            'd': ('loadd_unif_int.dat', 'txnsd_unif_int.dat'),
            'e': ('loade_unif_int.dat', 'txnse_unif_int.dat'),
            'x': ('loadx_unif_int.dat', 'txnsx_unif_int.dat'),
            'y': ('loady_unif_int.dat', 'txnsy_unif_int.dat'),
        }
        
        if self.workload not in workload_files:
            print(f"✗ Invalid workload '{self.workload}'")
            return False
        
        load_file, txn_file = workload_files[self.workload]
        load_path = dataset_path / load_file
        txn_path = dataset_path / txn_file
        
        print(f"Dataset directory: {dataset_path}")
        print(f"Workload: {self.workload}")
        
        missing_files = []
        if not load_path.exists():
            print(f"  ✗ {load_file} - NOT FOUND")
            missing_files.append(str(load_path))
        else:
            print(f"  ✓ {load_file} - Found")
        
        if not txn_path.exists():
            print(f"  ✗ {txn_file} - NOT FOUND")
            missing_files.append(str(txn_path))
        else:
            print(f"  ✓ {txn_file} - Found")
        
        if missing_files:
            print(f"\n✗ Missing required dataset files!")
            return False
        
        print("✓ All required dataset files found!")
        return True
    
    def compile_ycsb(self, version_name):
        """Compile YCSB using make"""
        print(f"\n{'=' * 80}")
        print(f"Compiling YCSB ({version_name})...")
        print("=" * 80)
        
        try:
            # Clean first
            print("Running 'make clean'...")
            subprocess.run(
                ["make", "clean"],
                cwd=self.bskiplist_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Compile
            print("Running 'make ycsb'...")
            result = subprocess.run(
                ["make", "ycsb"],
                cwd=self.bskiplist_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            print(f"✓ Compilation successful for {version_name}!")
            
            # Save compilation output
            compile_log = self.run_dir / f"compilation_{version_name}.log"
            with open(compile_log, 'w') as f:
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Compilation failed for {version_name}!")
            print(f"Error: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            
            # Save error log
            error_log = self.run_dir / f"compilation_error_{version_name}.log"
            with open(error_log, 'w') as f:
                f.write(f"Compilation failed at {datetime.now()}\n")
                f.write(f"Error: {e}\n")
                f.write(f"\nSTDOUT:\n{e.stdout}\n")
                f.write(f"\nSTDERR:\n{e.stderr}\n")
            
            return False
    
    def parse_ycsb_output(self, output):
        """Parse YCSB output to extract throughput metrics"""
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
        
        # Extract all load samples
        load_samples = re.findall(r"Load took \d+ us, throughput = ([\d\.]+) ops/us", output)
        metrics['load_samples'] = [float(x) for x in load_samples]
        
        # Extract all run samples
        run_samples = re.findall(r"Run, throughput: ([\d\.]+) ,ops/us", output)
        metrics['run_samples'] = [float(x) for x in run_samples]
        
        return metrics
    
    def run_ycsb_once(self, run_number, output_dir, version_name):
        """Run YCSB once and return metrics"""
        print(f"\n  Run {run_number}/{self.num_runs} ({version_name})...", end=" ", flush=True)
        
        ycsb_binary = self.bskiplist_dir / "ycsb"
        
        # Output file for this run
        output_file = f"run_{run_number:02d}_output.txt"
        
        # YCSB command: ./ycsb [dataset_dir] [workload] [threads] [output_file]
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
                timeout=600  # 10 minute timeout
            )
            
            # Save output immediately
            output_file_path = output_dir / f"run_{run_number:02d}.txt"
            with open(output_file_path, 'w') as f:
                f.write(f"Run {run_number} ({version_name}) - {datetime.now()}\n")
                f.write("=" * 80 + "\n\n")
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)
            
            # Parse metrics
            metrics = self.parse_ycsb_output(result.stdout)
            
            # Save metrics immediately as JSON
            metrics_file = output_dir / f"run_{run_number:02d}_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            # Print summary
            if metrics['median_load'] and metrics['median_run']:
                print(f"✓ Load: {metrics['median_load']:.3f} ops/us, Run: {metrics['median_run']:.3f} ops/us")
            else:
                print("✓ Completed (metrics parsing may have failed)")
            
            return metrics
            
        except subprocess.TimeoutExpired:
            print("✗ Timeout!")
            error_file = output_dir / f"run_{run_number:02d}_error.txt"
            with open(error_file, 'w') as f:
                f.write(f"Run {run_number} timed out after 600 seconds\n")
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed!")
            error_file = output_dir / f"run_{run_number:02d}_error.txt"
            with open(error_file, 'w') as f:
                f.write(f"Run {run_number} failed\n")
                f.write(f"Error: {e}\n")
                f.write(f"\nSTDOUT:\n{e.stdout}\n")
                f.write(f"\nSTDERR:\n{e.stderr}\n")
            return None
    
    def run_benchmarks_for_version(self, version_name, output_dir, results_dict):
        """Run YCSB num_runs times for a specific version"""
        print(f"\n{'=' * 80}")
        print(f"Running YCSB {self.num_runs} times with {version_name}")
        print("=" * 80)
        
        successful_runs = 0
        failed_runs = 0
        
        for i in range(1, self.num_runs + 1):
            metrics = self.run_ycsb_once(i, output_dir, version_name)
            
            if metrics and metrics['median_load'] and metrics['median_run']:
                results_dict['load_throughputs'].append(metrics['median_load'])
                results_dict['run_throughputs'].append(metrics['median_run'])
                results_dict['all_load_samples'].extend(metrics['load_samples'])
                results_dict['all_run_samples'].extend(metrics['run_samples'])
                successful_runs += 1
            else:
                failed_runs += 1
        
        print(f"\n{'=' * 80}")
        print(f"{version_name} completed: {successful_runs} successful, {failed_runs} failed")
        print("=" * 80)
        
        return successful_runs > 0
    
    def calculate_statistics(self, data, name):
        """Calculate and return statistics for a dataset"""
        if not data:
            return None
        
        stats = {
            'name': name,
            'count': len(data),
            'mean': statistics.mean(data),
            'median': statistics.median(data),
            'stdev': statistics.stdev(data) if len(data) > 1 else 0,
            'min': min(data),
            'max': max(data),
            'range': max(data) - min(data),
            'cv': (statistics.stdev(data) / statistics.mean(data) * 100) if len(data) > 1 and statistics.mean(data) > 0 else 0,
            'raw_data': data
        }
        
        # Calculate percentiles
        sorted_data = sorted(data)
        n = len(sorted_data)
        stats['p25'] = sorted_data[int(n * 0.25)]
        stats['p75'] = sorted_data[int(n * 0.75)]
        stats['p90'] = sorted_data[int(n * 0.90)]
        stats['p95'] = sorted_data[int(n * 0.95)]
        stats['p99'] = sorted_data[int(n * 0.99)] if n >= 100 else sorted_data[-1]
        
        return stats
    
    def calculate_improvement(self, baseline_value, evolved_value):
        """Calculate percentage improvement"""
        if baseline_value == 0:
            return 0
        return ((evolved_value - baseline_value) / baseline_value) * 100
    
    def generate_comparison_report(self):
        """Generate comprehensive comparison report"""
        print(f"\n{'=' * 80}")
        print("Generating Comparison Report")
        print("=" * 80)
        
        # Calculate statistics for both versions
        baseline_load_stats = self.calculate_statistics(
            self.baseline_results['load_throughputs'], 
            "Baseline Load Throughput"
        )
        baseline_run_stats = self.calculate_statistics(
            self.baseline_results['run_throughputs'], 
            "Baseline Run Throughput"
        )
        
        evolved_load_stats = self.calculate_statistics(
            self.evolved_results['load_throughputs'], 
            "Evolved Load Throughput"
        )
        evolved_run_stats = self.calculate_statistics(
            self.evolved_results['run_throughputs'], 
            "Evolved Run Throughput"
        )
        
        # Create comparison summary
        comparison = {
            'experiment_info': {
                'num_runs': self.num_runs,
                'timestamp': self.timestamp,
                'workload': self.workload,
                'threads': self.num_threads,
                'dataset_dir': self.dataset_dir
            },
            'baseline': {
                'load': baseline_load_stats,
                'run': baseline_run_stats
            },
            'evolved': {
                'load': evolved_load_stats,
                'run': evolved_run_stats
            },
            'improvements': {}
        }
        
        # Calculate improvements
        if baseline_load_stats and evolved_load_stats:
            comparison['improvements']['load_mean'] = self.calculate_improvement(
                baseline_load_stats['mean'], evolved_load_stats['mean']
            )
            comparison['improvements']['load_median'] = self.calculate_improvement(
                baseline_load_stats['median'], evolved_load_stats['median']
            )
        
        if baseline_run_stats and evolved_run_stats:
            comparison['improvements']['run_mean'] = self.calculate_improvement(
                baseline_run_stats['mean'], evolved_run_stats['mean']
            )
            comparison['improvements']['run_median'] = self.calculate_improvement(
                baseline_run_stats['median'], evolved_run_stats['median']
            )
        
        # Save JSON
        json_file = self.run_dir / "comparison_results.json"
        with open(json_file, 'w') as f:
            json.dump(comparison, f, indent=2)
        
        print(f"✓ JSON results saved to: {json_file}")
        
        # Generate human-readable report
        report_file = self.run_dir / "COMPARISON_REPORT.md"
        with open(report_file, 'w') as f:
            f.write("# Baseline vs Evolved B-Skip Comparison Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Workload:** YCSB Workload {self.workload.upper()}\n\n")
            f.write(f"**Configuration:**\n")
            f.write(f"- Number of runs: {self.num_runs}\n")
            f.write(f"- Threads: {self.num_threads}\n")
            f.write(f"- Dataset: {self.dataset_dir}\n\n")
            
            f.write("---\n\n")
            
            # Load throughput comparison
            f.write("## Load Throughput Comparison\n\n")
            if baseline_load_stats and evolved_load_stats:
                f.write("| Metric | Baseline | Evolved | Improvement |\n")
                f.write("|--------|----------|---------|-------------|\n")
                
                improvement_mean = comparison['improvements']['load_mean']
                improvement_median = comparison['improvements']['load_median']
                
                f.write(f"| Mean | {baseline_load_stats['mean']:.6f} ops/us | "
                       f"{evolved_load_stats['mean']:.6f} ops/us | "
                       f"{improvement_mean:+.2f}% |\n")
                
                f.write(f"| Median | {baseline_load_stats['median']:.6f} ops/us | "
                       f"{evolved_load_stats['median']:.6f} ops/us | "
                       f"{improvement_median:+.2f}% |\n")
                
                f.write(f"| Std Dev | {baseline_load_stats['stdev']:.6f} ops/us | "
                       f"{evolved_load_stats['stdev']:.6f} ops/us | - |\n")
                
                f.write(f"| Min | {baseline_load_stats['min']:.6f} ops/us | "
                       f"{evolved_load_stats['min']:.6f} ops/us | - |\n")
                
                f.write(f"| Max | {baseline_load_stats['max']:.6f} ops/us | "
                       f"{evolved_load_stats['max']:.6f} ops/us | - |\n")
                
                f.write(f"| CV | {baseline_load_stats['cv']:.2f}% | "
                       f"{evolved_load_stats['cv']:.2f}% | - |\n\n")
            
            # Run throughput comparison
            f.write("## Run Throughput Comparison\n\n")
            if baseline_run_stats and evolved_run_stats:
                f.write("| Metric | Baseline | Evolved | Improvement |\n")
                f.write("|--------|----------|---------|-------------|\n")
                
                improvement_mean = comparison['improvements']['run_mean']
                improvement_median = comparison['improvements']['run_median']
                
                f.write(f"| Mean | {baseline_run_stats['mean']:.6f} ops/us | "
                       f"{evolved_run_stats['mean']:.6f} ops/us | "
                       f"{improvement_mean:+.2f}% |\n")
                
                f.write(f"| Median | {baseline_run_stats['median']:.6f} ops/us | "
                       f"{evolved_run_stats['median']:.6f} ops/us | "
                       f"{improvement_median:+.2f}% |\n")
                
                f.write(f"| Std Dev | {baseline_run_stats['stdev']:.6f} ops/us | "
                       f"{evolved_run_stats['stdev']:.6f} ops/us | - |\n")
                
                f.write(f"| Min | {baseline_run_stats['min']:.6f} ops/us | "
                       f"{evolved_run_stats['min']:.6f} ops/us | - |\n")
                
                f.write(f"| Max | {baseline_run_stats['max']:.6f} ops/us | "
                       f"{evolved_run_stats['max']:.6f} ops/us | - |\n")
                
                f.write(f"| CV | {baseline_run_stats['cv']:.2f}% | "
                       f"{evolved_run_stats['cv']:.2f}% | - |\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            if baseline_run_stats and evolved_run_stats:
                load_improvement = comparison['improvements'].get('load_mean', 0)
                run_improvement = comparison['improvements'].get('run_mean', 0)
                
                if load_improvement > 0:
                    f.write(f"✓ **Load throughput improved by {load_improvement:.2f}%**\n\n")
                elif load_improvement < 0:
                    f.write(f"✗ Load throughput decreased by {abs(load_improvement):.2f}%\n\n")
                else:
                    f.write(f"→ Load throughput unchanged\n\n")
                
                if run_improvement > 0:
                    f.write(f"✓ **Run throughput improved by {run_improvement:.2f}%**\n\n")
                elif run_improvement < 0:
                    f.write(f"✗ Run throughput decreased by {abs(run_improvement):.2f}%\n\n")
                else:
                    f.write(f"→ Run throughput unchanged\n\n")
            
            f.write("---\n\n")
            f.write("## Files\n\n")
            f.write(f"- Baseline runs: `{self.baseline_dir.relative_to(self.run_dir)}/`\n")
            f.write(f"- Evolved runs: `{self.evolved_dir.relative_to(self.run_dir)}/`\n")
            f.write(f"- JSON data: `comparison_results.json`\n")
        
        print(f"✓ Comparison report saved to: {report_file}")
        
        # Print to console
        print(f"\n{'=' * 80}")
        print("COMPARISON SUMMARY")
        print("=" * 80)
        
        if baseline_load_stats and evolved_load_stats:
            print(f"\nLoad Throughput (Mean):")
            print(f"  Baseline: {baseline_load_stats['mean']:.6f} ops/us")
            print(f"  Evolved:  {evolved_load_stats['mean']:.6f} ops/us")
            print(f"  Change:   {comparison['improvements']['load_mean']:+.2f}%")
        
        if baseline_run_stats and evolved_run_stats:
            print(f"\nRun Throughput (Mean):")
            print(f"  Baseline: {baseline_run_stats['mean']:.6f} ops/us")
            print(f"  Evolved:  {evolved_run_stats['mean']:.6f} ops/us")
            print(f"  Change:   {comparison['improvements']['run_mean']:+.2f}%")
        
        print(f"\n{'=' * 80}\n")
        
        return comparison
    
    def run(self):
        """Main execution flow"""
        print(f"\n{'=' * 80}")
        print("BASELINE vs EVOLVED COMPARISON")
        print("=" * 80)
        print(f"Configuration:")
        print(f"  Number of runs per version: {self.num_runs}")
        print(f"  Dataset directory: {self.dataset_dir}")
        print(f"  Workload: {self.workload}")
        print(f"  Threads: {self.num_threads}")
        print(f"  Output directory: {self.run_dir}")
        print("=" * 80 + "\n")
        
        try:
            # Check dataset files
            if not self.check_dataset_files():
                print("\n✗ Dataset check failed. Exiting.")
                return False
            
            # Backup original bskip.h
            self.backup_baseline()
            
            # Phase 1: Run baseline version
            print(f"\n{'=' * 80}")
            print("PHASE 1: BASELINE VERSION")
            print("=" * 80)
            
            if not self.compile_ycsb("baseline"):
                print("\n✗ Baseline compilation failed. Exiting.")
                self.restore_baseline()
                return False
            
            if not self.run_benchmarks_for_version("BASELINE", self.baseline_dir, self.baseline_results):
                print("\n✗ Baseline benchmark runs failed. Exiting.")
                self.restore_baseline()
                return False
            
            # Phase 2: Run evolved version
            print(f"\n{'=' * 80}")
            print("PHASE 2: EVOLVED VERSION")
            print("=" * 80)
            
            if not self.use_evolved_version():
                print("\n✗ Failed to install evolved version. Exiting.")
                self.restore_baseline()
                return False
            
            if not self.compile_ycsb("evolved"):
                print("\n✗ Evolved compilation failed. Exiting.")
                self.restore_baseline()
                return False
            
            if not self.run_benchmarks_for_version("EVOLVED", self.evolved_dir, self.evolved_results):
                print("\n✗ Evolved benchmark runs failed. Exiting.")
                self.restore_baseline()
                return False
            
            # Restore baseline
            self.restore_baseline()
            
            # Generate comparison report
            self.generate_comparison_report()
            
            print(f"\n{'=' * 80}")
            print("✓ COMPARISON COMPLETE")
            print("=" * 80)
            print(f"\nAll results saved in: {self.run_dir}")
            print(f"  - Baseline runs: {self.baseline_dir}")
            print(f"  - Evolved runs: {self.evolved_dir}")
            print(f"  - Comparison report: {self.run_dir / 'COMPARISON_REPORT.md'}")
            print(f"  - JSON data: {self.run_dir / 'comparison_results.json'}")
            print("=" * 80 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            self.restore_baseline()
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Compare baseline bskip.h with evolved best_program.h on YCSB workload E',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (5 runs each, workload E, 32 threads)
  python compare_baseline_evolved.py
  
  # Run 10 times each
  python compare_baseline_evolved.py -n 10
  
  # Use different dataset directory
  python compare_baseline_evolved.py -d /path/to/datasets/uniform/
  
  # Use different workload
  python compare_baseline_evolved.py -w a
  
  # Run with 64 threads
  python compare_baseline_evolved.py -t 64
        """
    )
    
    parser.add_argument(
        '-n', '--num-runs',
        type=int,
        default=5,
        help='Number of times to run YCSB for each version (default: 5)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='baseline_evolved_comparison',
        help='Output directory for results (default: baseline_evolved_comparison)'
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
        default='e',
        choices=['a', 'b', 'c', 'd', 'e', 'x', 'y'],
        help='YCSB workload to run (default: e)'
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
    
    # Run comparison
    comparison = BaselineEvolvedComparison(
        num_runs=args.num_runs,
        output_dir=args.output_dir,
        dataset_dir=args.dataset_dir,
        workload=args.workload,
        num_threads=args.threads
    )
    
    success = comparison.run()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())

