---
status: normative
updated: 2026-08-06
---

# STATUS

**Sprint 1 in progress (6 of 7 tasks complete).** `src/aether/` contains core M0 foundational domain models, wire port protocols, kernel dispatch & policy engine, workflow step types, mock adapters, and conformance suites.

| Area | State |
| :--- | :--- |
| `src/aether/domain/` | **Implemented.** Pure Pydantic models (ids, task, taint, budget, gate, model_io, workspace, tools) |
| `src/aether/ports/` | **Implemented.** 9 wire-serializable protocols for core boundaries |
| `src/aether/kernel/` | **Implemented.** Dispatch choke point (`dispatch.py`) and PolicyEngine (`policy.py`) |
| `src/aether/workflow/` | **Implemented.** `WorkflowStep[In, Out]` node & socket types (`step.py`) |
| `src/aether/measurement/` | **In Progress / Pending.** `TASK-010` (`repo_cache.py`) & `scripts/resolve_swebench_bases.py` pending to close Sprint 1 |
| `src/aether/adapters/` | **Pending.** Mocks exist in `tests/aether/mocks.py`. Real adapters land in Sprint 2 |
| Benchmark results | **None.** No valid number has ever been produced — see [`measurement.md`](./measurement.md) §1 |
| A/A variance floor | Not established. Blocked on B1 (`TASK-010`), B2b (`TASK-011`) and B4 (`TASK-013` domain complete) |
| Benchmark suite (`benchmarks/definitions/`) | Does not exist yet |
| Phase 0 decisions | **Ratified and locked.** |
| Documentation | **Phase 0 locked** (2026-08-06). Both docs gates green |
| Predecessor (`src/sagiha/`) | Reference material being retired |

## What CI currently proves

| Gate | State |
| :--- | :--- |
| `ruff`, `pyright` strict, `import-linter` (contracts) | Green — `aether` contracts active and passing alongside `sagiha` |
| `tests/aether/` suite | **Green.** 71/71 tests passing |
| Docs word budget (`--max 15000`) | **Green.** |
| Relative links | **Green.** |
| Docs gates can fail | **Green** — `tests/unit/test_docs_gates.py` |
| Path-constant drift | **Green** — `test_path_constant_drift.py` asserts `aether` module targets |
| `tcb-check` | Green |

## Rules this file is held to

- No claim here is unsupported by a line-level code read **or by running the gate and pasting what it said**.
- A gate that cannot fail is not counted as a gate.
- "Not implemented" is a legitimate and expected entry. A plausible-sounding estimate is not.
- A gate reported green here names the command that produced the green.
