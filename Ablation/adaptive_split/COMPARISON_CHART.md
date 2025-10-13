# Adaptive Split Ablation: Three-Way Comparison

## Visual Comparison of Test Versions

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPTIMIZATION FEATURES                         │
├────────────────────┬──────────────┬─────────────┬───────────────┤
│ Feature            │ Baseline     │ Adaptive    │ Best Program  │
│                    │ (No Adapt)   │ Only        │ (All Opts)    │
├────────────────────┼──────────────┼─────────────┼───────────────┤
│ Adaptive Split     │      ❌      │     ✅      │      ✅       │
│ Thread-Local Hints │      ❌      │     ❌      │      ✅       │
│ Binary Search      │      ❌      │     ❌      │      ✅       │
│ Optimized Loops    │      ❌      │     ❌      │      ✅       │
├────────────────────┼──────────────┼─────────────┼───────────────┤
│ File               │ baseline_no  │ with_       │ best_         │
│                    │ _adaptive.h  │ adaptive.h  │ program.h     │
└────────────────────┴──────────────┴─────────────┴───────────────┘
```

## Split Logic Comparison

### Baseline: Simple Midpoint Split
```cpp
void split_node() {
    int split_index = num_elts / 2;  // Always middle
    // e.g., for 1024 elements → split at 512
}
```

**Characteristic**: Predictable, simple, but may cause cascading splits

---

### Adaptive Only: Biased Split  
```cpp
void split_node() {
    int split_index = num_elts / 2;
    
    if (rank < split_index) {
        // Left-heavy insertion pattern
        split_index -= (num_elts/16 + 1);  // Shift left
        // e.g., 1024 → split at ~448 instead of 512
    } else {
        // Right-heavy insertion pattern  
        split_index += (num_elts/16 + 1);  // Shift right
        // e.g., 1024 → split at ~576 instead of 512
    }
}
```

**Characteristic**: Adapts to insertion patterns, reduces future splits

---

### Best Program: Adaptive + More
```cpp
void split_node() {
    // SAME adaptive split logic as above
    // PLUS:
    // - Thread-local hints for faster traversal
    // - Binary search within nodes
    // - Optimized range query loops
    // - Better memory layout
}
```

**Characteristic**: All optimizations combined

## Expected Performance Progression

```
Performance (ops/μs)
     ↑
 19  │                                    ● Best Program
     │                                   
 18  │                    ● Adaptive    
     │                   
 17  │  ● Baseline      
     │ 
 16  │
     └────────────────────────────────────────────→
        No Opts      Adaptive      All Opts
                     Only
```

## The Key Question This Experiment Answers

**How much of the gap between Baseline and Best Program is due to Adaptive Split?**

```
Gap Analysis:
├─ Total Improvement: [Best - Baseline]
│  
├─ Adaptive Contribution: [Adaptive - Baseline]
│  
└─ Other Optimizations: [Best - Adaptive]
```

## Measurement Strategy

```
┌──────────────┐
│   Baseline   │ ← Run 3 times → Average Result A
└──────────────┘

┌──────────────┐
│  Adaptive    │ ← Run 3 times → Average Result B
└──────────────┘

┌──────────────┐
│ Best Program │ ← Run 3 times → Average Result C
└──────────────┘

Calculate:
• Adaptive Impact    = (B - A) / A × 100%
• Total Improvement  = (C - A) / A × 100%  
• Adaptive Share     = (B - A) / (C - A) × 100%
```

## What Each Comparison Tells Us

| Comparison | Question Answered |
|------------|-------------------|
| **Baseline vs Adaptive** | Does adaptive split help? By how much? |
| **Baseline vs Best** | What's the total improvement possible? |
| **Adaptive vs Best** | How much more is there beyond adaptive split? |

## Hypothesis

Based on code analysis:
- **Adaptive Split**: +0.5-2% improvement (modest)
- **Thread-Local Hints**: +2-4% improvement (significant)
- **Binary Search**: +1-2% improvement (moderate)
- **Combined Effect**: Possibly non-linear (synergy or interference)

## After Running: Analysis Template

```markdown
## Results

1. **Adaptive Split Impact**: X.X%
   - Load: +X.X%
   - Run: +X.X%
   
2. **Total OpenEvolve Gain**: X.X%

3. **Adaptive's Contribution**: XX% of total
   - If >50%: Adaptive split is the main driver
   - If 20-50%: Adaptive is significant but not dominant
   - If <20%: Other optimizations are more important

4. **Conclusion**: 
   - Worth the complexity? [Yes/No because...]
   - Recommended for production? [Yes/No because...]
```

---

## Quick Reference

| Need | See File |
|------|----------|
| Run experiment | `QUICK_START.md` |
| Understand setup | `EXPERIMENT_SETUP.md` |
| Technical details | `README.md` |
| All files overview | `SUMMARY.md` |
| Visual comparison | `COMPARISON_CHART.md` (this file) |

**Ready to run?** 
```bash
./run_adaptive_split_ablation.py
```



