# OpenEvolve Analysis Tools

This directory contains tools to analyze and extract ranked programs from OpenEvolve checkpoints.

## Overview

OpenEvolve stores all generated programs in its database, but only saves the best program as a readable `.h` file. These tools allow you to:

1. **Analyze any checkpoint** to see all programs ranked by performance
2. **Extract the top N programs** as readable `.h` files with metadata
3. **View comprehensive statistics** about program performance and success rates

## Tools

### 1. `analyze_checkpoint.py` - Comprehensive Analysis

The main analysis tool that provides detailed statistics about any checkpoint.

**Usage:**
```bash
python analyze_checkpoint.py <checkpoint_number> [--top N] [--save] [--output-dir DIR]
```

**Examples:**
```bash
# Analyze checkpoint 6, show top 10 programs
python analyze_checkpoint.py 6

# Analyze checkpoint 6, show top 5 programs and save them
python analyze_checkpoint.py 6 --top 5 --save

# Analyze checkpoint 6 and save to custom directory
python analyze_checkpoint.py 6 --save --output-dir /path/to/output
```

**Output:**
- Comprehensive statistics (total programs, success rate, performance distribution)
- Ranked list of programs with scores and metadata
- Optional: Saves top programs as `.h` files with metadata

### 2. `get_top_programs.py` - Simple Interface

A simplified interface for quick analysis and extraction.

**Usage:**
```bash
python get_top_programs.py <checkpoint> [top_n] [--save]
```

**Examples:**
```bash
# Show top 5 programs from checkpoint 6
python get_top_programs.py 6 5

# Show top 5 programs and save them
python get_top_programs.py 6 5 --save

# Show top 10 programs (default)
python get_top_programs.py 6
```

### 3. `extract_ranked_programs.py` - Basic Extraction

A basic tool for extracting ranked programs (legacy, use `analyze_checkpoint.py` instead).

## Output Format

When you save programs, each program gets two files:

### `.h` File
- **Format:** `rank_NN_programid.h`
- **Content:** The actual C++ code of the program
- **Example:** `rank_01_a237744d-f7f1-440d-8a81-bd8964648acd.h`

### Metadata File
- **Format:** `rank_NN_programid_info.json`
- **Content:** JSON with program metadata including:
  - `rank`: Ranking position (1-based)
  - `program_id`: Unique program identifier
  - `metrics`: Performance metrics (speedup, scores, etc.)
  - `generation`: Generation when program was created
  - `iteration_found`: Iteration when program was first found
  - `parent_id`: Parent program ID
  - `complexity`: Program complexity score
  - `diversity`: Program diversity score
  - `timestamp`: Creation timestamp
  - `h_file`: Associated .h filename

## Example Analysis Output

```
================================================================================
OpenEvolve Checkpoint 6 Analysis
================================================================================
Total Programs: 8
Successful Programs: 3
Failed Programs: 5
Success Rate: 37.5%
Last Iteration: 6

Islands: 4
  Island 0: 6 programs
  Island 1: 2 programs
  Island 2: 0 programs
  Island 3: 0 programs

Top 5 Programs by Performance:
----------------------------------------------------------------------------------------------------
Rank Program ID                           Score    Load %   Run %    Gen  Iter Status    
----------------------------------------------------------------------------------------------------
1    a237744d-f7f1-440d-8a81-bd8964648acd 16.07    21.9     10.3     1    2    SUCCESS   
2    20736556-fb4a-4d21-886b-ff19aa6005b7 16.07    21.9     10.3     1    2    SUCCESS   
3    54e29bb0-c897-4d3b-8cdf-6a8128d4ea40 13.17    17.8     8.5      2    6    SUCCESS   
4    50f1dec4-a158-4689-b8b1-b6b24700fa27 0.00     0.0      0.0      1    4    FAILED    
5    8f6f6131-019d-4ecf-9a2c-d2afde988e6d 0.00     0.0      0.0      1    1    FAILED    

Performance Distribution:
  Best Score: 16.07
  Worst Score: 13.17
  Average Score: 15.11
  Score 10-15: 1 programs
  Score 15-20: 2 programs
```

## Understanding the Results

### Program Status
- **SUCCESS**: Program compiled and ran successfully, has performance metrics
- **FAILED**: Program failed to compile, run, or timed out (score = 0.0)

### Performance Metrics
- **Score**: Combined performance score (higher is better)
- **Load %**: Load operation speedup percentage
- **Run %**: Run operation speedup percentage
- **Gen**: Generation when program was created
- **Iter**: Iteration when program was first found

### Islands
OpenEvolve uses multiple "islands" (parallel populations) for evolution. Each island can have different programs and the best from each island is tracked.

## Common Use Cases

1. **Find the best performing programs:**
   ```bash
   python get_top_programs.py 6 5 --save
   ```

2. **Analyze why programs are failing:**
   ```bash
   python analyze_checkpoint.py 6 --top 20
   ```

3. **Compare performance across checkpoints:**
   ```bash
   python analyze_checkpoint.py 5
   python analyze_checkpoint.py 6
   python analyze_checkpoint.py 7
   ```

4. **Extract all successful programs:**
   ```bash
   python analyze_checkpoint.py 6 --top 50 --save
   ```

## File Locations

- **Checkpoint data:** `/home/yomi/0Projects/bskip_artifact/bskiplist/openevolve_output/checkpoints/checkpoint_N/`
- **Programs database:** `checkpoint_N/programs/` (JSON files)
- **Metadata:** `checkpoint_N/metadata.json`
- **Ranked programs:** `checkpoint_N/ranked_programs/` (after running with --save)

## Troubleshooting

- **"Checkpoint directory not found"**: Make sure the checkpoint number exists
- **"Error loading program"**: Some programs may be corrupted, the tool will skip them
- **Empty results**: Check if the checkpoint has any programs with valid metrics

## Notes

- Programs are ranked by `combined_score` (descending)
- Failed programs (score = 0.0) are still included in the ranking
- The tools automatically handle JSON extraction from OpenEvolve's database format
- All timestamps are in Unix format
