---
status: normative
updated: 2026-07-31
---

# ADR-0022: RHI Is Re-Founded on Economics — Tiers A/B Scheduled, Tier C Trigger-Gated

**Status**: Accepted
**Date**: 2026-07-31

## Context

The [RHI outer loop](../04-workflows-and-loops/rhi-outer-loop.md) is specified as a four-step cycle
whose centre of gravity is **Mutation Proposal**: the Meta-Improver proposes harness changes, AOI
ranks them, four verification tiers evaluate them. The cost note at the end acknowledges an
iteration runs into the thousands of dollars.

Two facts make funding that as the loop's core indefensible right now:

1. **The evidence for its return does not exist.** The gates that would show a mutation helped were
   hardcoded `True` until `v2-S1` (H1), and cost accounting was zeroed (H2). Every prior signal
   about mutation-search value was taken over fabricated instruments and cannot be cited.
2. **The cheap half of the loop was never separated from the expensive half.** Trajectory
   ingestion, the A/A noise floor, paired statistics, and cost accounting are instrumentation on
   runs that were paid for anyway. Bundling them into the same "outer loop" as mutation search
   means the near-free, compounding activity inherits the scheduling constraints of the expensive,
   speculative one — so in practice neither runs.

## Decision

The outer loop is re-founded as **three tiers with different economics and different schedules.**

| Tier | Activity | Cost | Schedule |
| :--- | :--- | :--- | :--- |
| **A** | Trajectory ingestion and measurement: A/A noise floor, paired statistics, cost/latency/cache-hit accounting, failure-pattern reporting | Near-zero — instrumentation on runs already paid for | **Always on** |
| **B** | Distillation and dataset export; human-authored prompt and policy refinements, evaluated against Tier A's floor | Bounded, predictable | **Scheduled** at phase close |
| **C** | Mutation search: Meta-Improver proposals, AOI ranking, Tiers 0–3 evaluation | Thousands of dollars per iteration | **Dormant** behind an explicit funding trigger |

**Tier C does not run on a schedule.** It activates when a human funds a specific iteration against
a **named hypothesis**, with the A/A floor already measured on honest gates. "The outer loop ran
this week" is not a reason; "we believe change X improves Y and here is the floor it must beat" is.

`ports/meta_improver.py` stays in the tree — 22 LOC, governed by
[ADR-0023](./0023-port-rent-rule.md) — but has no scheduled consumer, and its absence from the
schedule is not a defect to be fixed.

The four verification tiers (0–3) are unchanged. They are **how** Tier C evaluates when it runs;
this ADR governs **whether and when** it runs.

## Consequences

**Easy.** Tier A ships immediately and compounds: every run makes the floor tighter and the failure
patterns clearer, at no marginal cost. The A/A floor — the single most important gate in the loop —
stops being gated behind the willingness to fund mutation search.

**Hard.** "Self-improving harness" becomes a much narrower claim than the architecture originally
implied. That is the honest description of what is funded, and stating it here prevents the
capability from being assumed by a downstream doc.

**Foreclosed.** Continuous autonomous self-modification. Given that an optimizer's cheapest path to
a higher score is editing the grader ([ADR-0007](./0007-trusted-computing-base.md)), and that the
graders were literals until `v2-S1`, this forecloses nothing that could have been trusted.

**Risk accepted.** Tier C may stay dormant indefinitely and effectively become unmaintained.
ADR-0023's rent rule is the mechanism that forces that to be a decision rather than a drift.

## Reversal Conditions

* **Tier C demonstrates return.** If a funded iteration produces a mutation that beats the A/A
  floor under Tier 3 statistics on honest gates, and the improvement replicates, promote Tier C to
  scheduled and record the measured cost-per-accepted-mutation here.
* **Evaluation cost collapses.** If per-task evaluation cost falls by an order of magnitude —
  cheaper models, cached evaluation, a smaller sufficient suite — the trigger threshold should be
  recomputed rather than inherited.
* **Tier A saturates.** If measurement stops yielding new failure patterns, the marginal value has
  moved to mutation search and the balance should be re-argued.
* **The Conductor arrives.** The `C0` phase depends on honest cost telemetry and would schedule
  across these tiers. When it becomes startable (post-Phase 7), this allocation is its input, not
  its constraint, and should be re-derived.

## Related

[RHI Outer Loop](../04-workflows-and-loops/rhi-outer-loop.md) ·
[Trace Distillation](../04-workflows-and-loops/trace-distillation.md) (Tier B) ·
[ADR-0007](./0007-trusted-computing-base.md) (TCB — why the evaluator is never mutable) ·
[ADR-0023](./0023-port-rent-rule.md) (port rent) ·
[STATUS.md](../STATUS.md) (H1/H2 — why prior signals cannot be cited)
