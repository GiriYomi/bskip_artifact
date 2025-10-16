# Ablation Study Versions

This directory contains 5 ablation versions of bskip.h to isolate individual optimizations:

## Versions

1. **v1_binary_search** - Binary Search Only
   - Original bskip.h with BINARY_SEARCH=1
   - Tests the impact of enabling binary search in leaf nodes

2. **v2_exponential_search** - Exponential + Binary Search
   - Adds exponential search strategy to find_rank_in_node
   - Better performance for large nodes (MAX_KEYS=1024)

3. **v3_thread_hints** - Thread-Local Hints
   - Adds thread-local per-level hints for faster traversal
   - Optimistic caching of recently accessed nodes

4. **v4_bitops_flipcoins** - Bit Operations in flip_coins
   - Optimizes promotion algorithm with bit operations
   - Avoids expensive division/modulus when p is power-of-two

5. **v5_adaptive_split** - Adaptive Split + Micro-optimizations
   - Adaptive split point selection based on insertion location
   - Tight loops in map_range
   - Other micro-optimizations

## Usage

These versions are used by `run_ablation_study.py` to measure the performance
impact of each optimization individually.

## Note

Some versions (v2, v3, v5) currently use the full evolved version as cleanly
isolating specific optimizations requires significant code refactoring. Future
improvements could create more precise isolation.
