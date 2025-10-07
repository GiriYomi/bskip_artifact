#!/usr/bin/env python3
"""
Ablation Study: flip_coins Optimization Impact
================================================

This script measures the isolated performance impact of the flip_coins 
optimization found by OpenEvolve. 

**What Changed:**
The evolved best_program.h replaced the adaptive density-based flip_coins 
function with a power-of-two optimized version using __builtin_ctzll.

**Test Versions:**
1. Original Baseline (bskip.h) - Adaptive density-based flip_coins
2. Best Program (best_program.h) - Power-of-two optimized flip_coins

**Key Insight:**
Since flip_coins is the ONLY difference between the two versions, this 
directly measures the performance impact of this single optimization.
"""

import subprocess
import json
import time
import os
import shutil
from pathlib import Path

# Paths - automatically detect the project root
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Go up from Ablation/flip_coins_optimization to project root
BSKIP_DIR = PROJECT_ROOT / "bskiplist"
ORIGINAL_BSKIP = BSKIP_DIR / "bskip.h"
DATA_DIR = "/mydata/skip_data/uniform/"
BEST_PROGRAM = PROJECT_ROOT / "bskiplist" / "openevolve_output" / "best" / "best_program.h"
ABLATION_DIR = PROJECT_ROOT / "Ablation" / "flip_coins_optimization"
RESULTS_FILE = ABLATION_DIR / "flip_coins_ablation_results.json"

# Test configuration
NUM_RUNS = 3
WORKLOAD = "a"  # Read-heavy workload
NUM_THREADS = 32

def backup_original():
    """Backup the original bskip.h"""
    backup_path = BSKIP_DIR / "bskip.h.backup"
    shutil.copy2(ORIGINAL_BSKIP, backup_path)
    print(f"✅ Backed up original to {backup_path}")
    return backup_path

def restore_original(backup_path):
    """Restore the original bskip.h"""
    shutil.copy2(backup_path, ORIGINAL_BSKIP)
    print(f"✅ Restored original from {backup_path}")
    backup_path.unlink()

def install_version(source_file, version_name):
    """Install a specific version of bskip.h"""
    # Don't copy if it's already the same file
    if source_file.resolve() != ORIGINAL_BSKIP.resolve():
        shutil.copy2(source_file, ORIGINAL_BSKIP)
        print(f"📝 Installed {version_name}")
    else:
        print(f"📝 Using {version_name} (already in place)")

def clean_build():
    """Clean build artifacts"""
    subprocess.run(["make", "clean"], cwd=BSKIP_DIR, capture_output=True)

def compile_program():
    """Compile the program"""
    print("🔨 Compiling...")
    # Compile without LATENCY flag for pure throughput measurement
    result = subprocess.run(["make", "LATENCY=0"], cwd=BSKIP_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Compilation failed:")
        print(result.stderr)
        return False
    print("✅ Compilation successful")
    return True

def run_benchmark():
    """Run a single benchmark and parse output"""
    # Run the benchmark
    cmd = [
        "./ycsb",
        f"{DATA_DIR},
        f"{WORKLOAD}",
        str(NUM_THREADS),
        "ablation_flip_coins_run.txt"
    ]
    
    print(f"   Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BSKIP_DIR, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Benchmark failed:")
        print(result.stderr)
        return None
    
    # Parse output
    output = result.stdout
    load_tpt = None
    run_tpt = None
    
    for line in output.split('\n'):
        if "Median Load throughput:" in line:
            load_tpt = float(line.split(':')[1].strip().split()[0])
        elif "Median Run throughput:" in line:
            run_tpt = float(line.split(':')[1].strip().split()[0])
    
    return {
        "load_throughput": load_tpt,
        "run_throughput": run_tpt
    }

def run_experiment(version_name, source_file):
    """Run the full experiment for one version"""
    print(f"\n{'='*60}")
    print(f"Testing: {version_name}")
    print(f"{'='*60}")
    
    # Install this version
    install_version(source_file, version_name)
    
    # Clean and compile
    clean_build()
    if not compile_program():
        return None
    
    # Run multiple times
    results = []
    for run_num in range(1, NUM_RUNS + 1):
        print(f"\n🏃 Run {run_num}/{NUM_RUNS}...")
        result = run_benchmark()
        if result:
            results.append(result)
            print(f"   Load: {result['load_throughput']:.6f} ops/μs")
            print(f"   Run:  {result['run_throughput']:.6f} ops/μs")
        
        # Sleep between runs to let system stabilize
        if run_num < NUM_RUNS:
            print("   Sleeping 5 seconds...")
            time.sleep(5)
    
    # Calculate statistics
    if not results:
        return None
    
    load_tpts = [r['load_throughput'] for r in results if r['load_throughput']]
    run_tpts = [r['run_throughput'] for r in results if r['run_throughput']]
    
    stats = {
        "version": version_name,
        "runs": results,
        "avg_load_throughput": sum(load_tpts) / len(load_tpts) if load_tpts else None,
        "avg_run_throughput": sum(run_tpts) / len(run_tpts) if run_tpts else None,
        "avg_combined": None
    }
    
    if stats["avg_load_throughput"] and stats["avg_run_throughput"]:
        stats["avg_combined"] = (stats["avg_load_throughput"] + stats["avg_run_throughput"]) / 2
    
    return stats

def analyze_results(results):
    """Analyze and compare results"""
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}\n")
    
    baseline = results["original_baseline"]
    best = results["best_program"]
    
    # Calculate improvements
    load_improvement = ((best["avg_load_throughput"] - baseline["avg_load_throughput"]) 
                        / baseline["avg_load_throughput"] * 100)
    run_improvement = ((best["avg_run_throughput"] - baseline["avg_run_throughput"]) 
                       / baseline["avg_run_throughput"] * 100)
    combined_improvement = ((best["avg_combined"] - baseline["avg_combined"]) 
                            / baseline["avg_combined"] * 100)
    
    print(f"📊 Performance Comparison:")
    print(f"{'='*60}")
    print(f"Metric                  | Baseline      | Best Program  | Change")
    print(f"{'-'*60}")
    print(f"Load Throughput         | {baseline['avg_load_throughput']:7.4f} ops/μs | {best['avg_load_throughput']:7.4f} ops/μs | {load_improvement:+6.2f}%")
    print(f"Run Throughput          | {baseline['avg_run_throughput']:7.4f} ops/μs | {best['avg_run_throughput']:7.4f} ops/μs | {run_improvement:+6.2f}%")
    print(f"Combined Score          | {baseline['avg_combined']:7.4f} ops/μs | {best['avg_combined']:7.4f} ops/μs | {combined_improvement:+6.2f}%")
    print(f"{'='*60}\n")
    
    print(f"\n💡 Key Findings:")
    print(f"{'='*60}")
    print(f"The flip_coins optimization (power-of-two fast path) provides:")
    print(f"  • Load phase: {load_improvement:+.2f}% {'improvement' if load_improvement > 0 else 'regression'}")
    print(f"  • Run phase:  {run_improvement:+.2f}% {'improvement' if run_improvement > 0 else 'regression'}")
    print(f"  • Overall:    {combined_improvement:+.2f}% {'improvement' if combined_improvement > 0 else 'regression'}")
    print(f"\nThis is the ONLY change between baseline and best program.")
    print(f"{'='*60}\n")
    
    return {
        "load_improvement_pct": load_improvement,
        "run_improvement_pct": run_improvement,
        "combined_improvement_pct": combined_improvement
    }

def main():
    """Main experiment runner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Ablation Study: flip_coins Optimization Impact             ║
╚══════════════════════════════════════════════════════════════╝

This experiment measures the isolated performance impact of the 
flip_coins optimization found by OpenEvolve.

Versions being tested:
  1. Original Baseline - Adaptive density-based flip_coins
  2. Best Program - Power-of-two optimized flip_coins (with __builtin_ctzll)

Configuration:
  • Workload: YCSB-A (100% reads)
  • Threads: {NUM_THREADS}
  • Runs per version: {NUM_RUNS}
  
""".format(NUM_THREADS=NUM_THREADS, NUM_RUNS=NUM_RUNS))
    
    # Create output directory
    ABLATION_DIR.mkdir(parents=True, exist_ok=True)
    
    # Backup original
    backup_path = backup_original()
    
    try:
        # Test both versions
        results = {}
        
        # 1. Original baseline
        results["original_baseline"] = run_experiment(
            "Original Baseline (Adaptive flip_coins)", 
            ORIGINAL_BSKIP
        )
        
        # 2. Best program
        results["best_program"] = run_experiment(
            "Best Program (Power-of-two optimized flip_coins)", 
            BEST_PROGRAM
        )
        
        # Analyze results
        if results["original_baseline"] and results["best_program"]:
            analysis = analyze_results(results)
            results["analysis"] = analysis
            
            # Save results
            with open(RESULTS_FILE, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"💾 Results saved to: {RESULTS_FILE}")
        else:
            print("❌ Experiment failed - incomplete results")
            
    finally:
        # Always restore original
        restore_original(backup_path)
        print("\n✅ Original bskip.h restored")

if __name__ == "__main__":
    main()

