---
status: normative
updated: 2026-08-05
---
# ADR-0003: Exact McNemar, Holm–Bonferroni, N ≥ 50

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F3

## Context

One proposal specified an A/A floor, exact McNemar and Holm–Bonferroni. The other specified
`p < 0.05`, `N ≥ 50` and Student's t / two-tailed permutation. Each held half of the right
answer.

Two of the objections are correctness issues, not preferences:

- **Resolve/not-resolve is a paired binary outcome.** Student's t assumes continuous,
  roughly normal data. On paired binary outcomes its p-value does not mean what it appears
  to mean.
- **α = 0.05 applied per-test across five arms is a ~23% family-wise error rate**
  (`1 − 0.95⁵`). A raw `p < 0.05` on the fifth of five arms is close to meaningless.

And structurally: **without an A/A floor, "significant" has no denominator.**

Against that, `N ≥ 50` is the better half of the opposing protocol, and is adopted.

## Decision

| Element | Choice |
| :--- | :--- |
| Design | Paired — same tasks, same order, same seeds where seeds exist |
| Sample | **N ≥ 50** instances; ≥ 2 passes per arm |
| Statistic | **Exact McNemar** |
| Multiple comparisons | **Holm–Bonferroni** across the gate family |
| Threshold | **α = 0.05 family-wise**, not per-test |
| Intervals | Seeded bootstrap CI, 2000 iterations |
| Effect size | Paired difference in resolve rate with CI, plus cost per resolved task |

- Implementation is ported **verbatim** from the predecessor's `e0/statistics.py` — 259 LOC,
  pure stdlib, pinned JSON fixtures. It is the one component whose claimed properties verify
  line by line, and it is the single cleanest asset Phase 0 produced.
- **Null results are recorded as "no signal at this tier"** — a property of the measurement,
  not a verdict on the mechanism. They re-enter at a higher tier.

## Consequences

- Admission requires cost held flat or reduced, in addition to the statistical result.
- The gate family must be declared before the sweep, not chosen after seeing results.

## Reversal Conditions

If a benchmark's outcome type stops being binary — partial credit, graded rubrics — McNemar
no longer applies and the statistic is reselected for the new outcome type. Holm–Bonferroni
and the family-wise α survive that change.
