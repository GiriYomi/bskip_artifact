#!/usr/bin/env python3
"""
Simple script to get top N programs from any OpenEvolve checkpoint.
Usage: python get_top_programs.py <checkpoint> [top_n]
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analyze_checkpoint import analyze_checkpoint, print_analysis, save_ranked_programs

def main():
    if len(sys.argv) < 2:
        print("Usage: python get_top_programs.py <checkpoint> [top_n] [--save]")
        print("Example: python get_top_programs.py 6 5 --save")
        sys.exit(1)
    
    checkpoint = int(sys.argv[1])
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != '--save' else 10
    save = '--save' in sys.argv
    
    try:
        # Analyze checkpoint
        stats = analyze_checkpoint(checkpoint, top_n)
        
        # Print analysis
        print_analysis(stats)
        
        # Save if requested
        if save:
            # Auto-detect base directory
            if os.path.exists('/home/yomi/0Projects/bskip_artifact'):
                base_dir = "/home/yomi/0Projects/bskip_artifact/bskiplist/openevolve_output"
            else:
                base_dir = "/opt/bskip_artifact/bskiplist/openevolve_output"
            output_dir = os.path.join(base_dir, f"checkpoints/checkpoint_{checkpoint}/ranked_programs")
            save_ranked_programs(stats, output_dir)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
