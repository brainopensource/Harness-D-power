---
status: rationale
updated: 2026-08-05
---

# AETHER v3.0.0 — Agile Engineering & Tracking

This directory contains the operational management documentation for **AETHER v3.0.0**, including roadmaps, milestones, backlogs, and sprint plans.

> [!IMPORTANT]
> **Normative Standing & Drift Prevention**:
> Management documents in `docs/agile/` do **not** define system architecture, data models, or code contracts. 
> - **Code & Specifications Win**: Architecture and invariants are defined in [`docs/spec.md`](../spec.md), [`docs/measurement.md`](../measurement.md), [`docs/decisions/`](../decisions/README.md), and `src/aether/ports/`.
> - **High-Level Pointers**: Tasks in sprint backlogs refer directly to normative specification sections and code targets via markdown links. Tasks must not re-explain implementation details in prose to prevent specification drift.
> - **Gate-Driven Schedule**: Per [ADR-0009](../decisions/0009-gates-are-the-schedule.md), exit gates decide when a phase ends; calendar durations are tripwires, not commitments.

---

## Directory Index

| Document | Purpose |
| :--- | :--- |
| [`roadmap.md`](./roadmap.md) | Phased execution DAG (M0–M3) and instrument unblocking timeline |
| [`milestones.md`](./milestones.md) | Quantitative, falsifiable exit gates and tripwires for all phases |
| [`backlog.md`](./backlog.md) | Complete prioritized epic & task inventory with normative pointers |
| [`sprints/sprint-01.md`](./sprints/sprint-01.md) | **Current Sprint**: M0 Domain/Ports, Blocker B1 utility, and core timers |

---

## Operational Guidelines

1. **Frontmatter**: Every file in this directory carries `status: rationale` to stay exempt from the normative word budget enforced by `scripts/docs_budget.py`.
2. **Acceptance Criteria**: Every task item must state a mechanical, testable gate (e.g., CI check, import-linter contract, conformance suite pass).
3. **No Plausible Estimates**: Unmeasured performance claims are forbidden; tasks report measured benchmarks or stay unmeasured until instrumented (per [ADR-0002](../decisions/0002-no-number-before-the-floor.md)).
