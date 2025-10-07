#!/usr/bin/env python3
"""
Ablation experiment to test the performance impact of Adaptive Node Splitting optimization.
This script compares:
1. Baseline (bskip without adaptive split)
2. Adaptive Split Only (bskip with only adaptive split optimization)
3. Best Program (bskip with all optimizations including adaptive split, hints, binary search, etc.)
"""

import subprocess
import os
import time
import json
from pathlib import Path

# Configuration
DATA_DIR = "/mydata/skip_data/uniform/"
WORKLOAD = "a"
NUM_THREADS = 32

def run_benchmark(bskip_file, description, num_runs=3):
    """Run benchmark with a specific bskip.h file and return average metrics."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"File: {bskip_file}")
    print(f"{'='*60}")
    
    # Backup current bskip.h
    if os.path.exists("bskip.h"):
        subprocess.run(["cp", "bskip.h", "bskip.h.backup"], check=True)
    
    try:
        # Copy test file to bskip.h
        subprocess.run(["cp", bskip_file, "bskip.h"], check=True)
        
        # Clean and build
        print("Building...")
        subprocess.run(["make", "clean"], check=True, capture_output=True)
        build_result = subprocess.run(["make", "LATENCY=0", "-j"], capture_output=True, text=True)
        
        if build_result.returncode != 0:
            print(f"Build failed: {build_result.stderr}")
            return None
        
        print("Build successful!")
        
        # Run benchmark multiple times
        results = []
        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}...")
            
            # Run YCSB benchmark
            cmd = ["./ycsb", DATA_DIR, WORKLOAD, str(NUM_THREADS), f"ablation_adaptive_run_{i}.txt"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"Benchmark failed: {result.stderr}")
                continue
            
            # Parse output for metrics
            lines = result.stdout.split('\n')
            load_throughput = None
            run_throughput = None
            
            for line in lines:
                if "Median Load throughput:" in line:
                    try:
                        load_throughput = float(line.split()[-2])
                    except:
                        pass
                elif "Median Run throughput:" in line:
                    try:
                        run_throughput = float(line.split()[-2])
                    except:
                        pass
            
            if load_throughput and run_throughput:
                results.append({
                    'load_throughput': load_throughput,
                    'run_throughput': run_throughput,
                    'combined': (load_throughput + run_throughput) / 2
                })
                print(f"  Load: {load_throughput:.2f} ops/us, Run: {run_throughput:.2f} ops/us")
            else:
                print(f"  Failed to parse metrics from run {i+1}")
        
        if not results:
            print("No successful runs!")
            return None
        
        # Calculate averages
        avg_load = sum(r['load_throughput'] for r in results) / len(results)
        avg_run = sum(r['run_throughput'] for r in results) / len(results)
        avg_combined = sum(r['combined'] for r in results) / len(results)
        
        print(f"\nAverage Results:")
        print(f"  Load Throughput: {avg_load:.2f} ops/us")
        print(f"  Run Throughput: {avg_run:.2f} ops/us")
        print(f"  Combined: {avg_combined:.2f} ops/us")
        
        return {
            'description': description,
            'file': bskip_file,
            'load_throughput': avg_load,
            'run_throughput': avg_run,
            'combined': avg_combined,
            'runs': len(results)
        }
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Restore backup
        if os.path.exists("bskip.h.backup"):
            subprocess.run(["cp", "bskip.h.backup", "bskip.h"], check=True)
            subprocess.run(["rm", "bskip.h.backup"], check=True)

def main():
    print("B-Skiplist Adaptive Split Ablation Experiment")
    print("Testing the performance impact of adaptive node splitting optimization")
    
    # Change to bskiplist directory - auto-detect from script location
    script_dir = Path(__file__).parent.resolve()
    bskiplist_dir = script_dir.parent.parent / "bskiplist"
    os.chdir(str(bskiplist_dir))
    
    # Define test cases
    test_cases = [
        {
            'file': '../Ablation/adaptive_split/bskip_baseline_no_adaptive.h',
            'description': 'Baseline (Original without adaptive split)'
        },
        {
            'file': '../Ablation/adaptive_split/bskip_with_adaptive.h', 
            'description': 'Adaptive Split Only (Original with adaptive split)'
        },
        {
            'file': '../bskiplist/openevolve_output_prompt3/best/best_program.h',
            'description': 'Best Program (All optimizations)'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        if not os.path.exists(test_case['file']):
            print(f"Warning: {test_case['file']} not found, skipping...")
            continue
        
        result = run_benchmark(test_case['file'], test_case['description'])
        if result:
            results.append(result)
        
        # Sleep between runs to let system cool down
        time.sleep(5)
    
    # Print comparison
    if len(results) >= 2:
        print(f"\n{'='*80}")
        print("ADAPTIVE SPLIT ABLATION EXPERIMENT RESULTS")
        print(f"{'='*80}")
        
        baseline = results[0]  # Baseline without adaptive split
        adaptive = results[1] if len(results) > 1 else None
        best = results[2] if len(results) > 2 else None
        
        print(f"\nBaseline (No Adaptive Split):")
        print(f"  Load: {baseline['load_throughput']:.2f} ops/us")
        print(f"  Run: {baseline['run_throughput']:.2f} ops/us")
        print(f"  Combined: {baseline['combined']:.2f} ops/us")
        
        if adaptive:
            load_speedup = (adaptive['load_throughput'] / baseline['load_throughput'] - 1) * 100
            run_speedup = (adaptive['run_throughput'] / baseline['run_throughput'] - 1) * 100
            combined_speedup = (adaptive['combined'] / baseline['combined'] - 1) * 100
            
            print(f"\nAdaptive Split Only:")
            print(f"  Load: {adaptive['load_throughput']:.2f} ops/us ({load_speedup:+.1f}%)")
            print(f"  Run: {adaptive['run_throughput']:.2f} ops/us ({run_speedup:+.1f}%)")
            print(f"  Combined: {adaptive['combined']:.2f} ops/us ({combined_speedup:+.1f}%)")
        
        if best:
            load_speedup = (best['load_throughput'] / baseline['load_throughput'] - 1) * 100
            run_speedup = (best['run_throughput'] / baseline['run_throughput'] - 1) * 100
            combined_speedup = (best['combined'] / baseline['combined'] - 1) * 100
            
            print(f"\nBest Program (All Optimizations):")
            print(f"  Load: {best['load_throughput']:.2f} ops/us ({load_speedup:+.1f}%)")
            print(f"  Run: {best['run_throughput']:.2f} ops/us ({run_speedup:+.1f}%)")
            print(f"  Combined: {best['combined']:.2f} ops/us ({combined_speedup:+.1f}%)")
        
        if adaptive and best:
            # Calculate how much of the total improvement comes from adaptive split
            adaptive_improvement = adaptive['combined'] - baseline['combined']
            total_improvement = best['combined'] - baseline['combined']
            if total_improvement > 0:
                adaptive_contribution = (adaptive_improvement / total_improvement) * 100
                print(f"\nAdaptive Split Contribution Analysis:")
                print(f"  Adaptive Split Improvement: {adaptive_improvement:.2f} ops/us")
                print(f"  Total Improvement (Best vs Baseline): {total_improvement:.2f} ops/us")
                print(f"  Adaptive Split accounts for: {adaptive_contribution:.1f}% of total improvement")
        
        # Save results
        output_file = "../Ablation/adaptive_split/adaptive_split_ablation_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
    
    else:
        print("Not enough successful results for comparison")

if __name__ == "__main__":
    main()

