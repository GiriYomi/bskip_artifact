#!/usr/bin/env python3
"""
Comprehensive OpenEvolve checkpoint analyzer.
Extracts and analyzes all programs from a checkpoint, ranking them by performance.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse

def load_program_data(program_path: str) -> Dict[str, Any]:
    """Load program data from JSON file."""
    with open(program_path, 'r') as f:
        return json.load(f)

def extract_program_code(program_data: Dict[str, Any]) -> str:
    """Extract code from program data."""
    return program_data.get('code', '')

def get_program_metrics(program_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metrics from program data."""
    return program_data.get('metrics', {})

def analyze_checkpoint(checkpoint_num: int, top_n: int = 10) -> Dict[str, Any]:
    """Analyze a checkpoint and return comprehensive statistics."""
    base_dir = "/home/yomi/0Projects/bskip_artifact/bskiplist/openevolve_output"
    checkpoint_dir = os.path.join(base_dir, f"checkpoints/checkpoint_{checkpoint_num}")
    
    if not os.path.exists(checkpoint_dir):
        raise FileNotFoundError(f"Checkpoint directory not found: {checkpoint_dir}")
    
    programs_dir = os.path.join(checkpoint_dir, "programs")
    metadata_path = os.path.join(checkpoint_dir, "metadata.json")
    
    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Get all program IDs
    all_program_ids = set()
    for island in metadata.get('islands', []):
        all_program_ids.update(island)
    
    # Load and rank programs
    programs = []
    for program_id in all_program_ids:
        program_path = os.path.join(programs_dir, f"{program_id}.json")
        if os.path.exists(program_path):
            try:
                program_data = load_program_data(program_path)
                metrics = get_program_metrics(program_data)
                combined_score = metrics.get('combined_score', 0.0)
                
                programs.append({
                    'id': program_id,
                    'data': program_data,
                    'metrics': metrics,
                    'combined_score': combined_score
                })
            except Exception as e:
                print(f"Error loading program {program_id}: {e}")
                continue
    
    # Sort by combined_score (descending)
    programs.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Calculate statistics
    successful_programs = [p for p in programs if p['combined_score'] > 0]
    failed_programs = [p for p in programs if p['combined_score'] == 0]
    
    stats = {
        'checkpoint': checkpoint_num,
        'total_programs': len(programs),
        'successful_programs': successful_programs,  # Keep as list
        'failed_programs': failed_programs,  # Keep as list
        'success_count': len(successful_programs),
        'failed_count': len(failed_programs),
        'success_rate': len(successful_programs) / len(programs) * 100 if programs else 0,
        'top_programs': programs[:top_n],
        'islands': metadata.get('islands', []),
        'island_best_programs': metadata.get('island_best_programs', []),
        'best_program_id': metadata.get('best_program_id'),
        'last_iteration': metadata.get('last_iteration', 0)
    }
    
    return stats

def print_analysis(stats: Dict[str, Any]):
    """Print a comprehensive analysis of the checkpoint."""
    print("=" * 80)
    print(f"OpenEvolve Checkpoint {stats['checkpoint']} Analysis")
    print("=" * 80)
    
    print(f"Total Programs: {stats['total_programs']}")
    print(f"Successful Programs: {stats['success_count']}")
    print(f"Failed Programs: {stats['failed_count']}")
    print(f"Success Rate: {stats['success_rate']:.1f}%")
    print(f"Last Iteration: {stats['last_iteration']}")
    
    print(f"\nIslands: {len(stats['islands'])}")
    for i, island in enumerate(stats['islands']):
        if isinstance(island, list):
            print(f"  Island {i}: {len(island)} programs")
        else:
            print(f"  Island {i}: 0 programs")
    
    print(f"\nTop {len(stats['top_programs'])} Programs by Performance:")
    print("-" * 100)
    print(f"{'Rank':<4} {'Program ID':<36} {'Score':<8} {'Load %':<8} {'Run %':<8} {'Gen':<4} {'Iter':<4} {'Status':<10}")
    print("-" * 100)
    
    for i, program in enumerate(stats['top_programs']):
        metrics = program['metrics']
        load_speedup = metrics.get('load_speedup', 0.0)
        run_speedup = metrics.get('run_speedup', 0.0)
        generation = program['data'].get('generation', '?')
        iteration = program['data'].get('iteration_found', '?')
        status = "SUCCESS" if program['combined_score'] > 0 else "FAILED"
        
        print(f"{i+1:<4} {program['id']:<36} {program['combined_score']:<8.2f} "
              f"{load_speedup:<8.1f} {run_speedup:<8.1f} {generation:<4} {iteration:<4} {status:<10}")
    
    # Show performance distribution
    if stats['success_count'] > 0:
        try:
            scores = [p['combined_score'] for p in stats['successful_programs']]
            print(f"\nPerformance Distribution:")
            print(f"  Best Score: {max(scores):.2f}")
            print(f"  Worst Score: {min(scores):.2f}")
            print(f"  Average Score: {sum(scores)/len(scores):.2f}")
            
            # Show score ranges
            ranges = [(0, 5), (5, 10), (10, 15), (15, 20), (20, float('inf'))]
            for low, high in ranges:
                count = sum(1 for s in scores if low <= s < high)
                if count > 0:
                    high_str = '∞' if high == float('inf') else str(high)
                    print(f"  Score {low}-{high_str}: {count} programs")
        except Exception as e:
            print(f"Error in performance distribution: {e}")
            print(f"Successful programs: {stats['success_count']}")
            if stats['successful_programs']:
                print(f"First program: {stats['successful_programs'][0]}")

def save_ranked_programs(stats: Dict[str, Any], output_dir: str):
    """Save ranked programs to files."""
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nSaving ranked programs to: {output_dir}")
    
    # Clear existing files to avoid duplicates
    for file in os.listdir(output_dir):
        if file.startswith('rank_'):
            os.remove(os.path.join(output_dir, file))
    
    for i, program in enumerate(stats['top_programs']):
        program_id = program['id']
        program_data = program['data']
        code = extract_program_code(program_data)
        
        # Save .h file
        h_filename = f"rank_{i+1:02d}_{program_id}.h"
        h_path = os.path.join(output_dir, h_filename)
        with open(h_path, 'w') as f:
            f.write(code)
        
        # Save metadata
        metadata_filename = f"rank_{i+1:02d}_{program_id}_info.json"
        metadata_path = os.path.join(output_dir, metadata_filename)
        
        metadata = {
            "rank": i + 1,
            "program_id": program_id,
            "metrics": program['metrics'],
            "generation": program_data.get('generation', 'unknown'),
            "iteration_found": program_data.get('iteration_found', 'unknown'),
            "parent_id": program_data.get('parent_id', 'unknown'),
            "complexity": program_data.get('complexity', 'unknown'),
            "diversity": program_data.get('diversity', 'unknown'),
            "timestamp": program_data.get('timestamp', 'unknown'),
            "h_file": h_filename
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    print(f"Saved {len(stats['top_programs'])} programs with metadata")

def main():
    parser = argparse.ArgumentParser(description='Analyze OpenEvolve checkpoint')
    parser.add_argument('checkpoint', type=int, help='Checkpoint number to analyze')
    parser.add_argument('--top', type=int, default=10, help='Number of top programs to show (default: 10)')
    parser.add_argument('--save', action='store_true', help='Save ranked programs to files')
    parser.add_argument('--output-dir', type=str, help='Output directory for saved programs')
    
    args = parser.parse_args()
    
    try:
        # Analyze checkpoint
        stats = analyze_checkpoint(args.checkpoint, args.top)
        
        # Print analysis
        print_analysis(stats)
        
        # Save programs if requested
        if args.save:
            if args.output_dir:
                output_dir = args.output_dir
            else:
                base_dir = "/home/yomi/0Projects/bskip_artifact/bskiplist/openevolve_output"
                output_dir = os.path.join(base_dir, f"checkpoints/checkpoint_{args.checkpoint}/ranked_programs")
            
            save_ranked_programs(stats, output_dir)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
