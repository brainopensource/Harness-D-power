---
status: normative
updated: 2026-07-31
---
# ADR-0022: RHI Is Re-Founded on Economics — Tiers A/B Scheduled, Tier C Trigger-Gated

**Status**: Accepted  
**Date**: 2026-07-31  

## Context

The [RHI outer loop](../04-workflows-and-loops/rhi-outer-loop.md) combines zero-marginal-cost telemetry with expensive mutation search ($1000s per run). Combining them causes low-cost measurement tasks to inherit the schedule constraints of speculative mutation search.

## Decision

The outer loop is split into **three distinct economic tiers**:

| Tier | Activity | Cost | Schedule |
| :--- | :--- | :--- | :--- |
| **A** | Trajectory ingestion & measurement: A/A noise floor, paired stats, cost/latency/cache accounting, failure reporting | Near-zero | **Always on** |
| **B** | Distillation & dataset export; human-authored prompt/policy refinements vs Tier A floor | Bounded, predictable | **Scheduled** at phase close |
| **C** | Mutation search: Meta-Improver proposals, AOI ranking, Tiers 0–3 evaluation | Thousands of dollars/run | **Dormant** behind explicit funding trigger |

**Tier C requires explicit human funding against a named hypothesis.** `ports/meta_improver.py` (22 LOC, governed by [ADR-0023](./0023-port-rent-rule.md)) remains dormant until triggered. Verification Tiers 0–3 apply when Tier C runs.

## Consequences

- **Easy**: Tier A runs continuously, compounding evaluation floor accuracy without marginal cost.
- **Hard**: Self-improving capabilities are explicitly bounded by funded iterations rather than continuous autonomous execution.
- **Foreclosed**: Unbudgeted continuous self-modification loops.
- **Risk Accepted**: Tier C remains dormant if unbudgeted.

## Reversal Conditions

- Funded Tier C iteration proves measurable gain beating A/A floor.
- Per-task evaluation cost drops by an order of magnitude.
- Tier A measurements saturate.
- Conductor (`C0`) phase arrives post-Phase 7 to re-derive tier scheduling.

## Related

[RHI Outer Loop](../04-workflows-and-loops/rhi-outer-loop.md) · [Trace Distillation](../04-workflows-and-loops/trace-distillation.md) · [ADR-0007](./0007-trusted-computing-base.md) · [ADR-0023](./0023-port-rent-rule.md) · [STATUS.md](../STATUS.md)
