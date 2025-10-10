#!/usr/bin/env python3
"""
YCSB Benchmark Runner
Compiles and runs YCSB 20 times, extracts ops/us metrics, and calculates statistics.
"""

import os
import subprocess
import re
import json
import statistics
from datetime import datetime
from pathlib import Path


class YCSBBenchmark:
    def __init__(self, num_runs=20, output_dir="ycsb_benchmark_results"):
        self.num_runs = num_runs
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.timestamp}"
        
        # Create output directories
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.individual_runs_dir = self.run_dir / "individual_runs"
        self.individual_runs_dir.mkdir(exist_ok=True)
        
        # Storage for all metrics
        self.load_throughputs = []
        self.run_throughputs = []
        self.all_load_samples = []  # All individual load samples from all runs
        self.all_run_samples = []   # All individual run samples from all runs
        
    def compile_ycsb(self):
        """Compile YCSB using make"""
        print("=" * 80)
        print("Step 1: Compiling YCSB...")
        print("=" * 80)
        
        # Change to bskiplist directory
        bskiplist_dir = Path(__file__).parent / "bskiplist"
        
        try:
            # Clean first
            print("Running 'make clean'...")
            subprocess.run(
                ["make", "clean"],
                cwd=bskiplist_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Compile
            print("Running 'make ycsb'...")
            result = subprocess.run(
                ["make", "ycsb"],
                cwd=bskiplist_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            print("✓ Compilation successful!")
            
            # Save compilation output
            compile_log = self.run_dir / "compilation.log"
            with open(compile_log, 'w') as f:
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Compilation failed!")
            print(f"Error: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            
            # Save error log
            error_log = self.run_dir / "compilation_error.log"
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
    
    def run_ycsb_once(self, run_number):
        """Run YCSB once and return metrics"""
        print(f"\nRun {run_number}/{self.num_runs}...", end=" ", flush=True)
        
        bskiplist_dir = Path(__file__).parent / "bskiplist"
        ycsb_binary = bskiplist_dir / "ycsb"
        
        try:
            result = subprocess.run(
                [str(ycsb_binary)],
                cwd=bskiplist_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            # Save output immediately
            output_file = self.individual_runs_dir / f"run_{run_number:02d}.txt"
            with open(output_file, 'w') as f:
                f.write(f"Run {run_number} - {datetime.now()}\n")
                f.write("=" * 80 + "\n\n")
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\n\nSTDERR:\n")
                f.write(result.stderr)
            
            # Parse metrics
            metrics = self.parse_ycsb_output(result.stdout)
            
            # Save metrics immediately as JSON
            metrics_file = self.individual_runs_dir / f"run_{run_number:02d}_metrics.json"
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
            error_file = self.individual_runs_dir / f"run_{run_number:02d}_error.txt"
            with open(error_file, 'w') as f:
                f.write(f"Run {run_number} timed out after 600 seconds\n")
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed!")
            error_file = self.individual_runs_dir / f"run_{run_number:02d}_error.txt"
            with open(error_file, 'w') as f:
                f.write(f"Run {run_number} failed\n")
                f.write(f"Error: {e}\n")
                f.write(f"\nSTDOUT:\n{e.stdout}\n")
                f.write(f"\nSTDERR:\n{e.stderr}\n")
            return None
    
    def run_all_benchmarks(self):
        """Run YCSB num_runs times"""
        print("\n" + "=" * 80)
        print(f"Step 2: Running YCSB {self.num_runs} times")
        print("=" * 80)
        
        successful_runs = 0
        failed_runs = 0
        
        for i in range(1, self.num_runs + 1):
            metrics = self.run_ycsb_once(i)
            
            if metrics and metrics['median_load'] and metrics['median_run']:
                self.load_throughputs.append(metrics['median_load'])
                self.run_throughputs.append(metrics['median_run'])
                self.all_load_samples.extend(metrics['load_samples'])
                self.all_run_samples.extend(metrics['run_samples'])
                successful_runs += 1
            else:
                failed_runs += 1
        
        print(f"\n{'=' * 80}")
        print(f"Completed: {successful_runs} successful, {failed_runs} failed")
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
    
    def print_statistics(self, stats):
        """Pretty print statistics"""
        if not stats:
            print("No data available")
            return
        
        print(f"\n{stats['name']}")
        print("-" * 60)
        print(f"  Count:              {stats['count']}")
        print(f"  Mean:               {stats['mean']:.6f} ops/us")
        print(f"  Median:             {stats['median']:.6f} ops/us")
        print(f"  Std Dev:            {stats['stdev']:.6f} ops/us")
        print(f"  Coefficient of Var: {stats['cv']:.2f}%")
        print(f"  Min:                {stats['min']:.6f} ops/us")
        print(f"  Max:                {stats['max']:.6f} ops/us")
        print(f"  Range:              {stats['range']:.6f} ops/us")
        print(f"\n  Percentiles:")
        print(f"    25th (P25):       {stats['p25']:.6f} ops/us")
        print(f"    75th (P75):       {stats['p75']:.6f} ops/us")
        print(f"    90th (P90):       {stats['p90']:.6f} ops/us")
        print(f"    95th (P95):       {stats['p95']:.6f} ops/us")
        print(f"    99th (P99):       {stats['p99']:.6f} ops/us")
    
    def generate_summary(self):
        """Generate and save summary statistics"""
        print("\n" + "=" * 80)
        print("Step 3: Calculating Performance Statistics")
        print("=" * 80)
        
        # Calculate statistics for median values from each run
        load_stats = self.calculate_statistics(self.load_throughputs, "Load Throughput (Median per Run)")
        run_stats = self.calculate_statistics(self.run_throughputs, "Run Throughput (Median per Run)")
        
        # Calculate statistics for all individual samples across all runs
        all_load_stats = self.calculate_statistics(self.all_load_samples, "Load Throughput (All Samples)")
        all_run_stats = self.calculate_statistics(self.all_run_samples, "Run Throughput (All Samples)")
        
        # Print to console
        if load_stats:
            self.print_statistics(load_stats)
        
        if run_stats:
            self.print_statistics(run_stats)
        
        if all_load_stats:
            self.print_statistics(all_load_stats)
        
        if all_run_stats:
            self.print_statistics(all_run_stats)
        
        # Save detailed statistics to JSON
        summary = {
            'benchmark_info': {
                'num_runs': self.num_runs,
                'timestamp': self.timestamp,
                'successful_runs': len(self.load_throughputs)
            },
            'median_per_run': {
                'load': load_stats,
                'run': run_stats
            },
            'all_samples': {
                'load': all_load_stats,
                'run': all_run_stats
            }
        }
        
        summary_file = self.run_dir / "summary_statistics.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'=' * 80}")
        print(f"✓ Summary statistics saved to: {summary_file}")
        
        # Create a human-readable summary report
        report_file = self.run_dir / "SUMMARY_REPORT.txt"
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("YCSB BENCHMARK SUMMARY REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp:        {self.timestamp}\n")
            f.write(f"Total Runs:       {self.num_runs}\n")
            f.write(f"Successful Runs:  {len(self.load_throughputs)}\n")
            f.write(f"Output Directory: {self.run_dir}\n\n")
            
            if load_stats:
                f.write("=" * 80 + "\n")
                f.write("LOAD THROUGHPUT (Median per Run)\n")
                f.write("=" * 80 + "\n")
                f.write(f"Mean:      {load_stats['mean']:.6f} ops/us\n")
                f.write(f"Median:    {load_stats['median']:.6f} ops/us\n")
                f.write(f"Std Dev:   {load_stats['stdev']:.6f} ops/us\n")
                f.write(f"Min:       {load_stats['min']:.6f} ops/us\n")
                f.write(f"Max:       {load_stats['max']:.6f} ops/us\n")
                f.write(f"CV:        {load_stats['cv']:.2f}%\n\n")
            
            if run_stats:
                f.write("=" * 80 + "\n")
                f.write("RUN THROUGHPUT (Median per Run)\n")
                f.write("=" * 80 + "\n")
                f.write(f"Mean:      {run_stats['mean']:.6f} ops/us\n")
                f.write(f"Median:    {run_stats['median']:.6f} ops/us\n")
                f.write(f"Std Dev:   {run_stats['stdev']:.6f} ops/us\n")
                f.write(f"Min:       {run_stats['min']:.6f} ops/us\n")
                f.write(f"Max:       {run_stats['max']:.6f} ops/us\n")
                f.write(f"CV:        {run_stats['cv']:.2f}%\n\n")
            
            if all_load_stats:
                f.write("=" * 80 + "\n")
                f.write("LOAD THROUGHPUT (All Individual Samples)\n")
                f.write("=" * 80 + "\n")
                f.write(f"Count:     {all_load_stats['count']}\n")
                f.write(f"Mean:      {all_load_stats['mean']:.6f} ops/us\n")
                f.write(f"Median:    {all_load_stats['median']:.6f} ops/us\n")
                f.write(f"Std Dev:   {all_load_stats['stdev']:.6f} ops/us\n")
                f.write(f"P90:       {all_load_stats['p90']:.6f} ops/us\n")
                f.write(f"P95:       {all_load_stats['p95']:.6f} ops/us\n")
                f.write(f"P99:       {all_load_stats['p99']:.6f} ops/us\n\n")
            
            if all_run_stats:
                f.write("=" * 80 + "\n")
                f.write("RUN THROUGHPUT (All Individual Samples)\n")
                f.write("=" * 80 + "\n")
                f.write(f"Count:     {all_run_stats['count']}\n")
                f.write(f"Mean:      {all_run_stats['mean']:.6f} ops/us\n")
                f.write(f"Median:    {all_run_stats['median']:.6f} ops/us\n")
                f.write(f"Std Dev:   {all_run_stats['stdev']:.6f} ops/us\n")
                f.write(f"P90:       {all_run_stats['p90']:.6f} ops/us\n")
                f.write(f"P95:       {all_run_stats['p95']:.6f} ops/us\n")
                f.write(f"P99:       {all_run_stats['p99']:.6f} ops/us\n\n")
        
        print(f"✓ Human-readable report saved to: {report_file}")
        print("=" * 80 + "\n")
        
        return summary
    
    def run(self):
        """Main execution flow"""
        print("\n" + "=" * 80)
        print("YCSB BENCHMARK RUNNER")
        print("=" * 80)
        print(f"Configuration:")
        print(f"  Number of runs: {self.num_runs}")
        print(f"  Output directory: {self.run_dir}")
        print("=" * 80 + "\n")
        
        # Step 1: Compile
        if not self.compile_ycsb():
            print("\n✗ Compilation failed. Exiting.")
            return False
        
        # Step 2: Run benchmarks
        if not self.run_all_benchmarks():
            print("\n✗ All benchmark runs failed. Exiting.")
            return False
        
        # Step 3: Generate summary
        self.generate_summary()
        
        print("\n" + "=" * 80)
        print("✓ BENCHMARK COMPLETE")
        print("=" * 80)
        print(f"\nAll results saved in: {self.run_dir}")
        print(f"  - Individual runs: {self.individual_runs_dir}")
        print(f"  - Summary report: {self.run_dir / 'SUMMARY_REPORT.txt'}")
        print(f"  - JSON data: {self.run_dir / 'summary_statistics.json'}")
        print("=" * 80 + "\n")
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Compile and run YCSB benchmark multiple times',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 20 times (default)
  python run_ycsb_benchmark.py
  
  # Run 10 times
  python run_ycsb_benchmark.py -n 10
  
  # Custom output directory
  python run_ycsb_benchmark.py -o my_results
        """
    )
    
    parser.add_argument(
        '-n', '--num-runs',
        type=int,
        default=20,
        help='Number of times to run YCSB (default: 20)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='ycsb_benchmark_results',
        help='Output directory for results (default: ycsb_benchmark_results)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.num_runs < 1:
        print("Error: Number of runs must be at least 1")
        return 1
    
    # Run benchmark
    benchmark = YCSBBenchmark(
        num_runs=args.num_runs,
        output_dir=args.output_dir
    )
    
    success = benchmark.run()
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())

