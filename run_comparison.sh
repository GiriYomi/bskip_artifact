#!/bin/bash
#
# Quick wrapper script to run baseline vs evolved comparison
# 

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================================"
echo "Baseline vs Evolved B-Skip Comparison"
echo "========================================================================"
echo ""

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/compare_baseline_evolved.py" ]; then
    echo "Error: compare_baseline_evolved.py not found!"
    exit 1
fi

# Default values
NUM_RUNS=5
WORKLOAD="e"
THREADS=32
DATASET_DIR="/mydata/skip_data/uniform/"

# Parse command line arguments
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--num-runs)
            NUM_RUNS="$2"
            shift 2
            ;;
        -w|--workload)
            WORKLOAD="$2"
            shift 2
            ;;
        -t|--threads)
            THREADS="$2"
            shift 2
            ;;
        -d|--dataset-dir)
            DATASET_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -n, --num-runs NUM     Number of runs per version (default: 5)"
            echo "  -w, --workload WORK    YCSB workload (a/b/c/d/e/x/y) (default: e)"
            echo "  -t, --threads NUM      Number of threads (default: 32)"
            echo "  -d, --dataset-dir DIR  Dataset directory (default: /mydata/skip_data/uniform/)"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                      # Run with defaults"
            echo "  $0 -n 10 -w e           # Run 10 times with workload E"
            echo "  $0 -t 64                # Run with 64 threads"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo "Configuration:"
echo "  Number of runs: $NUM_RUNS per version"
echo "  Workload: YCSB Workload $WORKLOAD"
echo "  Threads: $THREADS"
echo "  Dataset: $DATASET_DIR"
echo ""
echo "========================================================================"
echo ""

# Run the Python script
python3 "$SCRIPT_DIR/compare_baseline_evolved.py" \
    -n "$NUM_RUNS" \
    -w "$WORKLOAD" \
    -t "$THREADS" \
    -d "$DATASET_DIR"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✓ Comparison completed successfully!"
    echo "========================================================================"
    echo ""
    echo "Check the results in the baseline_evolved_comparison/ directory"
    echo "Look for COMPARISON_REPORT.md for a detailed analysis"
else
    echo ""
    echo "========================================================================"
    echo "✗ Comparison failed with exit code: $exit_code"
    echo "========================================================================"
fi

exit $exit_code

