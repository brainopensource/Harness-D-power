---
status: rationale
updated: 2026-08-05
---

# Sprint 01 Plan — Foundations & Instrument Unblocking

* **Goal**: Establish core pure domain models, wire-serializable ports, standalone upstream repository cache (B1), and initial performance timers.
* **Target Milestone**: [Milestone M0 & Blocker B1](../milestones.md#milestone-m0--pure-domain--wire-protocols)
* **Tripwire Window**: 5 Business Days (2026-08-06 to 2026-08-12)

---

## Sprint Backlog Items

### Task 1: Implement Pure Domain Data Models (`TASK-001`)
* **Target Seam**: `src/aether/domain/`
* **Specification Pointer**: [`spec.md` §3 (I1)](../../spec.md#2-invariants), [AGENTS.md Guideline 2](../../../AGENTS.md)
* **Acceptance Criteria**: 
  1. Immutable Pydantic models for run trajectories, tasks, grants, and events.
  2. `import-linter` contract `domain-is-pure` passes green in CI.

### Task 2: Define 8 Wire-Serializable Port Protocols (`TASK-002`)
* **Target Seam**: `src/aether/ports/`
* **Specification Pointer**: [`spec.md` §4](../../spec.md#4-ports), [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I2, I3)](../../spec.md#2-invariants)
* **Acceptance Criteria**:
  1. `ModelProvider`, `Workspace`, `WorktreeManager`, `ToolRegistry`, `PolicyEngine`, `ResourceGovernor`, `TrajectoryStore`, `Evaluator`, `Indexer` protocols defined.
  2. Every method is `async`. All payloads are Pydantic-serializable. Zero live objects or `Path` objects in signatures. Reflection test passes.

### Task 3: Build Standalone Upstream Repository Cache Utility (`TASK-010`)
* **Target Seam**: `src/aether/measurement/repo_cache.py`, `scripts/resolve_swebench_bases.py`
* **Specification Pointer**: [`measurement.md` §2 (B1)](../../measurement.md#2-instrument-blockers), [ADR-0002](../../decisions/0002-no-number-before-the-floor.md)
* **Acceptance Criteria**:
  1. Utility handles shallow git clones of 12 upstream SWE-bench repositories.
  2. Resolves base commits for 20 sample tasks with zero `fatal: invalid reference:` errors.

### Task 4: Implement WorkflowStep Node & Socket Types (`TASK-004`)
* **Target Seam**: `src/aether/workflow/step.py`
* **Specification Pointer**: [ADR-0013 (M0)](../../decisions/0013-workflow-dag-phased.md)
* **Acceptance Criteria**:
  1. `WorkflowStep[In, Out]` type definitions land with socket type safety.
  2. Pyright strict check passes with zero errors.

### Task 5: Initial Performance Timers (`TASK-021`)
* **Target Seam**: `src/aether/measurement/timers.py`
* **Specification Pointer**: [ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md)
* **Acceptance Criteria**:
  1. Instrument worktree creation timer and AST parse-and-validate timer.
  2. Record baseline numbers in `docs/rationale/benchmarks/`.

---

## Daily Sprint Definition of Done

1. `ruff check --fix` and `ruff format` pass without errors.
2. `pyright` strict type checking passes with 0 errors.
3. `import-linter` contract enforcement passes.
4. `python scripts/docs_budget.py --max 54000` passes in CI.
