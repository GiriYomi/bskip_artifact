#!/bin/bash

# Automated experiment script for testing different prompts with OpenEvolve
# This script runs the evolution process with prompts 1, 2, and 3 sequentially
# and renames the output folders accordingly

set -e  # Exit on any error

echo "Starting automated OpenEvolve experiment with different prompts..."

# Function to run evolution with a specific prompt
run_evolution() {
    local prompt_num=$1
    echo "=========================================="
    echo "Running evolution with prompt $prompt_num"
    echo "=========================================="
    
    # Run the evolution
    python run_skip.py $prompt_num
    
    # Wait a moment for any file operations to complete
    sleep 2
    
    # Check if openevolve_output folder exists and rename it
    if [ -d "bskiplist/openevolve_output" ]; then
        echo "Renaming openevolve_output to openevolve_output_prompt_$prompt_num"
        mv "bskiplist/openevolve_output" "bskiplist/openevolve_output_prompt_$prompt_num"
        echo "Prompt $prompt_num completed successfully!"
    else
        echo "Warning: openevolve_output folder not found after prompt $prompt_num"
    fi
    
    echo ""
}

# Run evolution with prompt 1
run_evolution 1

# Run evolution with prompt 2
run_evolution 2

# Run evolution with prompt 3
run_evolution 3

echo "=========================================="
echo "All experiments completed!"
echo "Results stored in:"
echo "  - bskiplist/openevolve_output_prompt_1"
echo "  - bskiplist/openevolve_output_prompt_2"
echo "  - bskiplist/openevolve_output_prompt_3"
echo "=========================================="