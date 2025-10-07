#!/usr/bin/env python3
"""
Compare the best program with the original bskip.h and provide detailed analysis.
"""

import subprocess
import sys
import os

def run_diff(file1, file2):
    """Run diff and return the output."""
    try:
        result = subprocess.run(['diff', '-u', file1, file2], 
                              capture_output=True, text=True)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

def analyze_differences(diff_output):
    """Analyze the diff output and categorize changes."""
    lines = diff_output.split('\n')
    
    changes = {
        'removed_lines': [],
        'added_lines': [],
        'modified_functions': [],
        'removed_features': [],
        'added_features': [],
        'comments_changed': [],
        'algorithm_changes': []
    }
    
    current_function = None
    in_function = False
    
    for line in lines:
        if line.startswith('@@'):
            # Parse function context
            parts = line.split()
            if len(parts) > 3:
                context = parts[3]
                if 'flip_coins' in context:
                    current_function = 'flip_coins'
                elif 'insert' in context:
                    current_function = 'insert'
                elif 'find' in context:
                    current_function = 'find'
                else:
                    current_function = 'other'
        
        elif line.startswith('-'):
            changes['removed_lines'].append(line[1:])
            if current_function:
                changes['modified_functions'].append(current_function)
            
            # Categorize removals
            if 'thread_local' in line or 'tl_' in line:
                changes['removed_features'].append('Thread-local optimizations')
            elif 'bias' in line or 'density' in line:
                changes['removed_features'].append('Adaptive density-based promotion')
            elif 'hint' in line:
                changes['removed_features'].append('Thread-local hints')
            elif 'split' in line and 'adaptive' in line:
                changes['removed_features'].append('Adaptive split point selection')
            elif '//' in line:
                changes['comments_changed'].append('Comment removed')
                
        elif line.startswith('+'):
            changes['added_lines'].append(line[1:])
            if current_function:
                changes['modified_functions'].append(current_function)
            
            # Categorize additions
            if 'binary search' in line or 'find_rank_in_node' in line:
                changes['added_features'].append('Optimized binary search')
            elif '//' in line:
                changes['comments_changed'].append('Comment added')
    
    # Remove duplicates
    for key in changes:
        if isinstance(changes[key], list):
            changes[key] = list(set(changes[key]))
    
    return changes

def print_analysis(changes):
    """Print a comprehensive analysis of the changes."""
    print("=" * 80)
    print("DETAILED COMPARISON: Best Program vs Original bskip.h")
    print("=" * 80)
    
    print(f"\n📊 SUMMARY:")
    print(f"  • Modified functions: {len(changes['modified_functions'])}")
    print(f"  • Removed features: {len(changes['removed_features'])}")
    print(f"  • Added features: {len(changes['added_features'])}")
    print(f"  • Comment changes: {len(changes['comments_changed'])}")
    
    print(f"\n🔧 MODIFIED FUNCTIONS:")
    for func in changes['modified_functions']:
        print(f"  • {func}")
    
    print(f"\n❌ REMOVED FEATURES:")
    for feature in changes['removed_features']:
        print(f"  • {feature}")
    
    print(f"\n✅ ADDED FEATURES:")
    for feature in changes['added_features']:
        print(f"  • {feature}")
    
    print(f"\n📝 COMMENT CHANGES:")
    for comment in changes['comments_changed']:
        print(f"  • {comment}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_programs.py <original_file> <best_program_file>")
        sys.exit(1)
    
    original_file = sys.argv[1]
    best_program_file = sys.argv[2]
    
    if not os.path.exists(original_file):
        print(f"Error: {original_file} not found")
        sys.exit(1)
    
    if not os.path.exists(best_program_file):
        print(f"Error: {best_program_file} not found")
        sys.exit(1)
    
    print("Running diff analysis...")
    diff_output, diff_error = run_diff(original_file, best_program_file)
    
    if diff_error:
        print(f"Error running diff: {diff_error}")
        sys.exit(1)
    
    if not diff_output:
        print("Files are identical!")
        return
    
    print("Analyzing differences...")
    changes = analyze_differences(diff_output)
    print_analysis(changes)
    
    print(f"\n📄 FULL DIFF OUTPUT:")
    print("-" * 80)
    print(diff_output)

if __name__ == "__main__":
    main()
