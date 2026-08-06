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

1. **Frontmatter follows what the file does, not what it costs.** [`milestones.md`](./milestones.md) and [`roadmap.md`](./roadmap.md) carry **`status: normative`**: their exit gates and dependency edges decide when a phase may end, which binds. [`backlog.md`](./backlog.md) and the sprint plans carry `status: rationale` — they point at normative specs rather than defining anything.

   > **This guideline previously read "every file here carries `status: rationale` to stay exempt from the budget."** That is the one evasion `scripts/docs_budget.py` cannot detect: the ceiling constrains only what self-declares normative, so tagging binding content `rationale` buys unlimited normative words. It was closed by retagging, not by adding a third tag — the two files cost 910 words against roughly 8,000 of headroom, so a new taxonomy would have bought nothing. See [`../README.md`](../README.md).

2. **Acceptance Criteria**: Every task item must state a mechanical, testable gate (CI check, import-linter contract, conformance suite pass). **If a gate is prose, it is not a gate.**

3. **Every gate ships with a test proving it can fail.** A gate that cannot fail is the most expensive bug this project can have, and this tree has already shipped three: a `bench-aa` job guarded on a file that does not exist, TCB contracts that go vacuous at the tree migration, and two docs gates reported green while red.

4. **No Plausible Estimates**: Unmeasured performance claims are forbidden; tasks report measured benchmarks or stay unmeasured until instrumented (per [ADR-0002](../decisions/0002-no-number-before-the-floor.md)). **A duration is an unmeasured number** and therefore a tripwire, never a commitment ([ADR-0009](../decisions/0009-gates-are-the-schedule.md)).

5. **Every gate is funded.** A gate in [`milestones.md`](./milestones.md) with no task in [`backlog.md`](./backlog.md) is a tripwire guaranteed to fire, and tripwires that always fire get ignored — [ADR-0009](../decisions/0009-gates-are-the-schedule.md)'s own reversal condition. Check the direction gate → task, not task → gate.
