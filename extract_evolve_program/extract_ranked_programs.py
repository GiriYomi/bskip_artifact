#!/usr/bin/env python3
"""
Extract and rank OpenEvolve programs by performance.
This script reads the OpenEvolve database and extracts the top N programs,
compiling them to readable .h files with metadata.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

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

def rank_programs_by_performance(programs_dir: str, metadata_path: str) -> List[Tuple[str, Dict[str, Any], float]]:
    """Rank all programs by their combined_score performance."""
    programs = []
    
    # Load metadata to get program IDs
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Get all program IDs from all islands
    all_program_ids = set()
    for island in metadata.get('islands', []):
        all_program_ids.update(island)
    
    # Load each program and extract metrics
    for program_id in all_program_ids:
        program_path = os.path.join(programs_dir, f"{program_id}.json")
        if os.path.exists(program_path):
            try:
                program_data = load_program_data(program_path)
                metrics = get_program_metrics(program_data)
                combined_score = metrics.get('combined_score', 0.0)
                
                programs.append((program_id, program_data, combined_score))
            except Exception as e:
                print(f"Error loading program {program_id}: {e}")
                continue
    
    # Sort by combined_score (descending)
    programs.sort(key=lambda x: x[2], reverse=True)
    return programs

def save_ranked_program(program_id: str, program_data: Dict[str, Any], 
                       rank: int, output_dir: str) -> str:
    """Save a ranked program to a .h file with metadata."""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract code
    code = extract_program_code(program_data)
    
    # Save .h file
    h_filename = f"rank_{rank:02d}_{program_id}.h"
    h_path = os.path.join(output_dir, h_filename)
    with open(h_path, 'w') as f:
        f.write(code)
    
    # Save metadata
    metadata_filename = f"rank_{rank:02d}_{program_id}_info.json"
    metadata_path = os.path.join(output_dir, metadata_filename)
    
    metadata = {
        "rank": rank,
        "program_id": program_id,
        "metrics": get_program_metrics(program_data),
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
    
    return h_path

def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_ranked_programs.py <checkpoint_number>")
        print("Example: python extract_ranked_programs.py 6")
        sys.exit(1)
    
    checkpoint_num = sys.argv[1]
    # Auto-detect base directory
    if os.path.exists('/home/yomi/0Projects/bskip_artifact'):
        base_dir = "/home/yomi/0Projects/bskip_artifact/bskiplist/openevolve_output"
    else:
        base_dir = "/opt/bskip_artifact/bskiplist/openevolve_output"
    checkpoint_dir = os.path.join(base_dir, f"checkpoints/checkpoint_{checkpoint_num}")
    
    if not os.path.exists(checkpoint_dir):
        print(f"Checkpoint directory not found: {checkpoint_dir}")
        sys.exit(1)
    
    programs_dir = os.path.join(checkpoint_dir, "programs")
    metadata_path = os.path.join(checkpoint_dir, "metadata.json")
    output_dir = os.path.join(checkpoint_dir, "ranked_programs")
    
    print(f"Extracting ranked programs from checkpoint {checkpoint_num}...")
    print(f"Programs directory: {programs_dir}")
    print(f"Output directory: {output_dir}")
    
    # Rank all programs
    ranked_programs = rank_programs_by_performance(programs_dir, metadata_path)
    
    print(f"\nFound {len(ranked_programs)} programs")
    print("\nTop 10 programs by performance:")
    print("-" * 80)
    print(f"{'Rank':<4} {'Program ID':<36} {'Combined Score':<15} {'Load Speedup':<12} {'Run Speedup':<12}")
    print("-" * 80)
    
    # Show top 10 and save all
    for i, (program_id, program_data, combined_score) in enumerate(ranked_programs):
        metrics = get_program_metrics(program_data)
        load_speedup = metrics.get('load_speedup', 0.0)
        run_speedup = metrics.get('run_speedup', 0.0)
        
        if i < 10:
            print(f"{i+1:<4} {program_id:<36} {combined_score:<15.4f} {load_speedup:<12.2f}% {run_speedup:<12.2f}%")
        
        # Save program
        h_path = save_ranked_program(program_id, program_data, i+1, output_dir)
        
        if i == 0:
            print(f"\nBest program saved to: {h_path}")
    
    print(f"\nAll {len(ranked_programs)} programs saved to: {output_dir}")
    print(f"Each program has a .h file and a _info.json metadata file")

if __name__ == "__main__":
    main()
