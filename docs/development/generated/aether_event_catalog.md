---
status: normative
updated: 2026-08-07
---

# AETHER Event Catalog

> [!IMPORTANT]
> **This file is generated** from `src/aether/domain/events.py` by
> `scripts/gen_aether_event_catalog.py`, drift-checked in CI with `--check`.
> Edit the Python, not this file.

Events never schedule nodes (spec.md §8) — this catalog is an observational
record the trajectory store, TUI, and future clients consume; it is not a
control-flow mechanism.

| Event | Payload |
| :--- | :--- |
| `run_started` | `task_id` |
| `node_started` | `node_id` |
| `node_completed` | `node_id`, `status` |
| `effect_dispatched` | `effect_class`, `status` |
| `budget_overrun_emitted` | `overrun` |
| `gate_report_emitted` | `node_id`, `report` |
| `run_completed` | `final_status` |

