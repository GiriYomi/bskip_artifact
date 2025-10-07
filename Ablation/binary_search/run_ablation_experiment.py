#!/usr/bin/env python3
"""
Ablation experiment to test the performance impact of only the binary search optimization.
This script compares:
1. Original bskip_binary.h (with all original features)
2. bskip_binary_ablation.h (with only the optimized binary search)
3. Best program (with all optimizations removed except binary search)
"""

import subprocess
import os
import time
import json
from pathlib import Path

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
        build_result = subprocess.run(["make", "-j"], capture_output=True, text=True)
        
        if build_result.returncode != 0:
            print(f"Build failed: {build_result.stderr}")
            return None
        
        print("Build successful!")
        
        # Run benchmark multiple times
        results = []
        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}...")
            
            # Run YCSB benchmark
            cmd = ["./ycsb", "/home/yomi/0Projects/skip_data/uniform/", "a", "32", f"results/ablation_run_{i}.txt"]
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
        return None
    
    finally:
        # Restore backup
        if os.path.exists("bskip.h.backup"):
            subprocess.run(["cp", "bskip.h.backup", "bskip.h"], check=True)
            subprocess.run(["rm", "bskip.h.backup"], check=True)

def main():
    print("B-Skiplist Ablation Experiment")
    print("Testing the performance impact of binary search optimization")
    
    # Change to bskiplist directory
    os.chdir("/home/yomi/0Projects/bskip_artifact/bskiplist")
    
    # Define test cases
    test_cases = [
        {
            'file': 'bskip_binary.h',
            'description': 'Original (with all features)'
        },
        {
            'file': 'bskip_binary_ablation.h', 
            'description': 'Ablation (only optimized binary search)'
        },
        {
            'file': 'openevolve_output/checkpoints/checkpoint_9/best_program.h',
            'description': 'Best Program (simplified + optimized binary search)'
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
    
    # Print comparison
    if len(results) >= 2:
        print(f"\n{'='*80}")
        print("ABLATION EXPERIMENT RESULTS")
        print(f"{'='*80}")
        
        baseline = results[0]  # Original
        ablation = results[1] if len(results) > 1 else None
        best = results[2] if len(results) > 2 else None
        
        print(f"\nBaseline (Original):")
        print(f"  Load: {baseline['load_throughput']:.2f} ops/us")
        print(f"  Run: {baseline['run_throughput']:.2f} ops/us")
        print(f"  Combined: {baseline['combined']:.2f} ops/us")
        
        if ablation:
            load_speedup = (ablation['load_throughput'] / baseline['load_throughput'] - 1) * 100
            run_speedup = (ablation['run_throughput'] / baseline['run_throughput'] - 1) * 100
            combined_speedup = (ablation['combined'] / baseline['combined'] - 1) * 100
            
            print(f"\nAblation (Binary Search Only):")
            print(f"  Load: {ablation['load_throughput']:.2f} ops/us ({load_speedup:+.1f}%)")
            print(f"  Run: {ablation['run_throughput']:.2f} ops/us ({run_speedup:+.1f}%)")
            print(f"  Combined: {ablation['combined']:.2f} ops/us ({combined_speedup:+.1f}%)")
        
        if best:
            load_speedup = (best['load_throughput'] / baseline['load_throughput'] - 1) * 100
            run_speedup = (best['run_throughput'] / baseline['run_throughput'] - 1) * 100
            combined_speedup = (best['combined'] / baseline['combined'] - 1) * 100
            
            print(f"\nBest Program (All Optimizations):")
            print(f"  Load: {best['load_throughput']:.2f} ops/us ({load_speedup:+.1f}%)")
            print(f"  Run: {best['run_throughput']:.2f} ops/us ({run_speedup:+.1f}%)")
            print(f"  Combined: {best['combined']:.2f} ops/us ({combined_speedup:+.1f}%)")
        
        # Save results
        with open("ablation_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: ablation_results.json")
    
    else:
        print("Not enough successful results for comparison")

if __name__ == "__main__":
    main()
