---
status: normative
updated: 2026-08-05
---
# ADR-0009: Exit Gates Are the Schedule; Durations Are Tripwires

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F9

## Context

One proposal offered five sprints of ~14 days with a Gantt chart. The other refused
durations entirely, on the grounds that the exit gates are the schedule.

Both are partly right and the failure modes are symmetric. A calendar with no gates ships
whatever exists on the date. Gates with no calendar give no signal that a phase is in
trouble until it has been in trouble for a long time — a position that is intellectually
correct and operationally unhelpful.

## Decision

**The gate decides when a phase ends. The calendar decides when to worry.**

- Every milestone has **quantitative, falsifiable exit gates**. A gate that is prose is not
  a gate.
- Indicative durations are published as **tripwires, not commitments**.
- **A phase running 50% over its indicative window is a signal to re-scope — never a reason
  to skip its gate.**

## Consequences

- No milestone can be declared complete by calendar.
- Slippage is visible early, and the response is scoped down rather than waved through.
- Duration estimates carry the same standing as any other unmeasured number in this project:
  useful for planning, never a gate.

## Reversal Conditions

If a tripwire fires repeatedly across milestones without a scope change following it, the
tripwires are being ignored and should either be re-estimated or dropped. A tripwire nobody
responds to is worse than none, because it manufactures a false sense of monitoring.
