---
status: rationale
updated: 2026-08-07
---

# Sprint 02 Plan — Real Adapters & the Walking Skeleton

* **Goal**: Replace the mocks with the four real adapters M1a needs, run the four-node skeleton end to end from a validated topology, and take the two numbers that decide the F1 fork.
* **Target Milestone**: [M1a](../milestones.md#milestone-m1a--walking-skeleton-4-node-linear-dag) · [B2b](../milestones.md#blocker-b2--local-openai-compatible-endpoint)
* **Tripwire Window**: 5 Business Days
* **Entry condition**: Sprint-01 complete. **M0 Exit Gate 0 must be green** — every task below writes into `src/aether/`, and until the TCB constants have moved, none of that code is covered by a contract that selects it.
* **Position in the plan**: [`sprints/README.md`](README.md)

---

## Sprint Backlog Items

### Task 1: Local Model Provider Adapter (`TASK-011`) — closes B2b
* **Target Seam**: `src/aether/adapters/model_provider/openai_compatible.py`
* **Specification Pointer**: [`measurement.md` §2 (B2)](../../measurement.md#2-instrument-blockers), [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md), [`tech_stack_and_infra.md` §4.2](../../architecture/tech_stack_and_infra.md)
* **Acceptance Criteria**:
  1. Passes the `ModelProvider` conformance suite — the same parametrized suite the mock passes, with the adapter added to its params list.
  2. Streams typed `ModelStreamEvent`s over `httpx`; **the stream always terminates with a `StopEvent`**.
  3. **Enforces the request's token ceilings.** Conservation is kernel policy, not adapter courtesy.
  4. A provider error is a typed error. It is never an empty list.

### Task 2: Git Workspace & Worktree Adapter (`TASK-017`)
* **Target Seam**: `src/aether/adapters/workspace/git_cli.py`
* **Specification Pointer**: [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I3)](../../spec.md#2-invariants), [`tech_stack_and_infra.md` §3.2](../../architecture/tech_stack_and_infra.md)
* **Acceptance Criteria**:
  1. Passes both the `Workspace` and `WorktreeManager` conformance suites.
  2. **No `Path` crosses the port** — all paths are repo-relative strings, `WorktreeRef.abs_hint` is a log string only (I3).
  3. `git` CLI via `asyncio.subprocess`, thin typed wrapper. One worktree per candidate under a run-scoped root.
  4. **The worktree-creation timer is instrumented here** (feeds Task 6).

### Task 3: Tool Registry & Tool-Execution Container (`TASK-018`)
* **Target Seam**: `src/aether/adapters/tools/builtin.py`, `containers/tools/`
* **Specification Pointer**: [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md), [ADR-0015](../../decisions/0015-taintgate-provenance-model.md), [ADR-0008](../../decisions/0008-shell-ast-classifies.md)
* **Acceptance Criteria**:
  1. Catalog **frozen at composition** (I6); runtime registration raises.
  2. **Tool outputs are labelled `untrusted-external` at construction**, not at point of use — nothing downstream has to remember to mark them.
  3. Separate image and separate lease class from the evaluator, so a runaway tool loop cannot starve the judge.

### Task 4: Evaluator (`TASK-019`) — TCB
* **Target Seam**: `src/aether/measurement/evaluator.py`
* **Specification Pointer**: [`spec.md` §4](../../spec.md#4-ports) (TCB port residency), [`spec.md` §2 (I7)](../../spec.md#2-invariants), [`milestones.md` B4](../milestones.md#blocker-b4--typed-instrument-error-handling)
* **Acceptance Criteria**:
  1. **Lives in `measurement/`, never `adapters/`.** The residency rule is what makes `tcb-isolation` select it; put it in `adapters/` and the contract silently stops covering the judge.
  2. `import-linter` proves it cannot import `agency/` or `workflow/`.
  3. Verifies the test command against the manifest's `test_command_hash` before running. **A drifted command is `GateStatus.NONE`, not a result.**
  4. Consumes Sprint-01's tri-state `GateReport` (`TASK-013`): exit-127 and uncollectable tests yield `NONE`.

### Task 5: Declarative Topology Executor (`TASK-020`) + Engine & Bus (`TASK-022`) + Governor (`TASK-034`)
* **Target Seam**: `src/aether/workflow/{executor,validator}.py`, `src/aether/engine.py`, `src/aether/kernel/{bus,governor}.py`, `workflows/linear_v1.yaml`
* **Specification Pointer**: [ADR-0013](../../decisions/0013-workflow-dag-phased.md), [ADR-0014](../../decisions/0014-workflow-topology-is-data.md), [`schemas_and_contracts.md` §1](../../architecture/schemas_and_contracts.md), [`spec.md` §5](../../spec.md#5-execution)
* **Acceptance Criteria**:
  1. The four-node skeleton (`retrieve → generate → apply → evaluate`) runs end to end through headless `engine.py`, **from a schema-validated YAML topology** — not Python composition.
  2. **The validator refuses any topology failing a static check**, with a typed error naming the check. Each of the five checks has a malformed fixture proving it can fail. **No `--force` flag exists.**
  3. `reserve → commit → release` is exercised; **the dispatcher refuses any effect without a live lease**, so after-the-fact accounting is structurally unrepresentable.
  4. Event-catalog drift check passes. **Events never schedule nodes.**

### Task 6: The Two F1 Timers (`TASK-021`) — *moved from Sprint-01*
* **Target Seam**: `src/aether/measurement/timers.py`, `src/aether/adapters/indexer/tree_sitter.py`
* **Specification Pointer**: [ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md), [ADR-0011](../../decisions/0011-no-lsp-adapter.md)
* **Acceptance Criteria**:
  1. Worktree creation (over Task 2) and AST parse-and-validate (over tree-sitter) timed, **with hardware and method recorded alongside the numbers**.
  2. Published to [`docs/benchmarks/results/performance_timers.md`](../../benchmarks/results/performance_timers.md).
  3. Compared against RT-1 / RT-2 / RT-3. **A trigger nobody has instrumented cannot fire** — this task is what makes those three thresholds real.
* **Why it is here and not in Sprint-01**: it wraps Task 2's adapter and a tree-sitter indexer, neither of which exists at M0. [ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md)'s *"first working slice"* is M1a.
* **Note**: these two numbers can reverse [ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md) directly. **A result of "no bottleneck" is a real result** and is recorded as such — it settles F1 just as firmly as a threshold crossing would.

### Task 7: SQLite Trajectory Store (`TASK-026`)
* **Target Seam**: `src/aether/adapters/trajectory_store/sqlite.py`
* **Specification Pointer**: [`spec.md` §8](../../spec.md#8-clients), [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md)
* **Acceptance Criteria**:
  1. Passes conformance. WAL mode, stdlib `sqlite3`, no ORM.
  2. **Never dropped under backpressure** — display consumers are drop-oldest; the durable log and the measurement harvester are not.
  3. Replay from it is byte-for-byte deterministic (feeds Sprint-01's cassettes).

---

## Milestone Gates Closed

**All six gates below are closed.** `engine.run()` executes `workflows/linear_v1.yaml`'s
four-node topology end to end (`tests/integration/test_engine_smoke.py`); see
[`STATUS.md`](../../STATUS.md) for the pasted gate results (135 passed, 1 skipped; `pyright
--strict` 0 errors; `lint-imports` 9/9 kept).

| Gate | Closed by | Evidence |
| :--- | :--- | :--- |
| B2 · 2 (B2b) | Task 1 (`TASK-011`) | `tests/conformance/test_model_provider.py`, respx-mocked SSE, all cases green |
| M1a · 1 skeleton from validated topology | Task 5 (`TASK-020`) | `workflows/linear_v1.yaml` loaded and validated by `workflow/validator.py`'s 5 checks before every run |
| M1a · 2 dispatch choke point | Task 5 (architecture test over Sprint-01's `TASK-003`) | `DispatchFacade` routes every node effect through `Dispatcher.dispatch()`; no adapter is reachable from a `WorkflowStep` any other way |
| M1a · 3 conformance, four boundaries | Tasks 1–4 | `tests/conformance/{test_model_provider,test_workspace,test_tool_registry,test_evaluator}.py` — mock + real adapter parametrized for all four |
| M1a · 4 F1 timers | Task 6 (`TASK-021`) | [`performance_timers.md`](../../benchmarks/results/performance_timers.md) — RT-3 not crossed (measured, not claimed unmeasured) |
| M1a · 5 reserve/commit/release | Task 5 (`TASK-034`) | `kernel/governor.py`'s real `ResourceGovernor`, exercised both per-effect (inside `Dispatcher.dispatch()`) and per-node (`workflow/executor.py`) |

---

## Explicitly not in this sprint

- **No repair edge.** M1a is the linear skeleton; `TASK-023` is Sprint-03.
- **No evaluation container.** Task 4 builds the judge; `TASK-016` containerises it in Sprint-03 alongside the B3 canary. **Until then no number produced here is a capability number** ([ADR-0002](../../decisions/0002-no-number-before-the-floor.md)) — the skeleton ships and reports an honest zero, which is a correct milestone result and not a failure.
- **No `PolicyEngine`, `ResourceGovernor`, `TrajectoryStore` or `Indexer` conformance gate.** M1a Gate 3 covers the four boundaries the skeleton walks; the rest enter per [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md) as their adapters land.

## Daily Sprint Definition of Done

Unchanged from [Sprint-01](./sprint-01.md), plus:

8. **No conformance suite has an empty adapter parameter list.** A suite that selects no adapter tests nothing.
9. **Every port in `ports/` has a real adapter or a named one.** A mock whose named real adapter did not land this sprint means the port is deleted, not carried ([ADR-0005](../../decisions/0005-eight-ports-adapter-first.md) rev. 2).
