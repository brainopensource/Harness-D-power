---
status: rationale
---
# 📊 SAGIHA Post-Honesty Baseline Benchmark Report (v2-S1)

**Date:** 2026-07-31  
**Sprint:** `v2-S1` (Instrument Honesty)  
**Suite ID:** `s0-baseline` (21 harvested tasks)  
**Pass Rate:** 0.0%  

## 📐 Noise Floor Calibration (A/A)
- **Mean Delta:** `0.0000`
- **Beats Noise Floor:** `False`

## ⚖️ Gate Honesty Summary
- **Before v2-S1:** Coding gates (`tests_unmodified`, `diff_within_bounds`, `no_new_suppressions`) returned hardcoded `True` literals, resulting in fabricated admission even when no code was written or verified.
- **After v2-S1:** Coding gates execute real `git diff` checks against `RunContext.base_commit`. Runs without git bases or without matching replay cassettes report honest `None` verdicts and fail closed (`admitted = False`).
- **Pass Rate Drop Note:** The drop to 0.0% pass rate on replay runs without recorded cassettes is the fix. The instrument now accurately reflects un-evaluated executions rather than fabricating 100% success.
