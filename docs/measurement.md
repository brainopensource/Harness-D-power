---
status: normative
updated: 2026-08-05
---

# Measurement Protocol

**The governing rule, and the reason this document exists before any capability document:**

> Instruments are built and verified before the capability they measure.
> Every gate ships with a test proving it can fail.

The prototype phase sequenced measurement last. Capability shipped without proof of value,
and **every number taken had to be discarded**. This document is the mechanism that prevents
a repeat; [`concepts/`](./concepts/README.md) is the evidence that it happened.

---

## 1. The current state, stated plainly

**AETHER has never produced a valid benchmark number.** Not a low one — none.

On day one that is the correct content for a results section, and it stays until the A/A
floor exists. A project that reports zero honestly is in a better position than one
reporting a comfortable estimate over a broken instrument, because the second has to discard
the estimate *and* every decision made on it.

---

## 2. Instrument blockers

Four, all reproduced. They are numbered as they were found; the numbering is preserved so
the historical record stays greppable.

| # | Defect | Effect | When fixed |
| :--- | :--- | :--- | :--- |
| **B1** | The runner resolves task base commits against the **local** repository; SWE-bench base commits live in **12 upstream repositories that were never cloned** | Every task fails `fatal: invalid reference:`. This is why the 2026-08-01 A/A run produced nothing | **Now.** Standalone utility, no AETHER dependency. It unblocks every number |
| **B2** | No model endpoint | Nothing to run | **Resolved.** A local OpenAI-compatible endpoint is sufficient for the floor, the baseline and every ablation |
| **B3** | An editable install's `.pth` leaks live `src/` into every supposedly-isolated worktree | **Candidate diffs invisible to the gates scoring them.** This one produced numbers | With the evaluation container. Ships with a **canary test asserting a deliberately broken candidate fails** |
| **B4** | Exit-127 (command not found) scored as a test failure | Instrument failures enter the denominator | With the gate. Requires a **typed distinction between *test failed* and *instrument failed*** |

**B3 and B4 are the same class of bug as a hard-coded gate:** the instrument produced numbers
while not measuring what it claimed. An instrument failure is never a data point.

**This is not "fix everything before writing code."** B1 starts now; B3 and B4 arrive with
the components they isolate. Two independent reviewers made the stronger reading, and it is
not implementable.

---

## 3. The A/A variance floor

Two identical configurations run against each other. Any observed difference is variance —
sampling, test order, timing, flaky tests in the task repositories.

| Element | Choice |
| :--- | :--- |
| Design | Paired: same tasks, same order, same seeds where seeds exist |
| Sample | **N ≥ 50** instances; ≥ 2 passes per arm |
| Statistic | **Exact McNemar** — the outcome is paired and binary |
| Multiple comparisons | **Holm–Bonferroni** across the gate family |
| Threshold | **α = 0.05 family-wise**, not per-test |
| Intervals | Seeded bootstrap CI, 2000 iterations |
| Effect size | Paired difference in resolve rate with CI, plus cost per resolved task |
| Implementation | `measurement/statistics.py` — pure stdlib, pinned JSON fixtures |

**Why not a t-test.** Resolve/not-resolve is paired binary. Student's t assumes continuous,
roughly normal data; on paired binary outcomes its p-value does not mean what it appears to
mean. And α applied per-test across five arms is a **~23% family-wise error rate** — five
arms, `1 − 0.95⁵`.

**Why the floor comes first.** Without it, "significant" has no denominator.

**Null results are recorded as "no signal at this tier"** — a property of the measurement,
not a verdict on the mechanism. They re-enter at a higher tier.

---

## 4. Targets

**Lift is the committed target.** Lift ≥ **+10 points**: the resolve-rate delta between a
bare model call and the same model inside AETHER, on identical tasks, same model both sides.
It is what the harness work actually moves, and it survives a model swap, a leaderboard
reshuffle and a diligence review.

**Absolute targets are provisional** (ADR-0004) — the leaderboard re-baselining behind them
has not been independently verified.

| Suite | Committed | Stretch |
| :--- | :--- | :--- |
| SWE-bench Verified | ≥ 90% | ≥ 96% |
| SWE-bench Pro | ≥ 60% | ≥ 80% |
| Terminal-Bench | ≥ 75% | — |

**An absolute number is never published without its lift.**

---

## 5. Gate design

- Tri-state `GateReport`: `True` / `False` / **`None`**. `None` means *unmeasured* and never
  silently passes.
- Every gate ships with a test proving it **can fail**. A gate that cannot fail is the most
  expensive bug this project can have.
- **Hard gates admit; learned proxies rank** (I9). A learned scorer may order candidates and
  may never admit one.
- A gate keyed to a path must select something. A contract that matches no file forbids
  nothing and passes green — `tests/unit/test_path_constant_drift.py` enforces this.

---

## 6. What a claim needs before it is published

1. The instrument's blockers are closed for the thing being claimed.
2. The A/A floor exists and is published.
3. The effect clears the floor with its CI, under Holm–Bonferroni across the family.
4. Cost per resolved task is reported alongside.
5. Lift is reported alongside any absolute.

**A number we did not measure on our own instruments never appears in a result, a claim, or
a regression gate.** It may set a default, motivate an ablation, or bound a design — nothing
more. Third-party figures enter as hypotheses with a named experiment, never as evidence.
