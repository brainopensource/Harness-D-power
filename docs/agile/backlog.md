---
status: rationale
updated: 2026-08-05
---

# AETHER v3.0.0 — Product & Technical Backlog

This backlog catalogs all Epics and User Stories for building AETHER v3.0.0. All tasks map directly to normative rules in [`docs/spec.md`](../spec.md), [`docs/measurement.md`](../measurement.md), or [`docs/decisions/`](../decisions/README.md).

---

## Epic 1: TCB Kernel & Core Domain (Milestone M0)

### TASK-001: Pure Domain Data Models
* **Description**: Implement immutable Pydantic domain models in `src/aether/domain/`. Zero I/O dependencies.
* **Target Files**: `src/aether/domain/*.py`
* **Normative Specs**: [`spec.md` §3 (I1)](../spec.md#2-invariants), [AGENTS.md Guideline 2](../../AGENTS.md)
* **Exit Criteria**: `import-linter` contract `domain-is-pure` passes green in CI.

### TASK-002: Wire-Serializable Port Protocols
* **Description**: Define typed `Protocol` boundaries for the 8 core port areas in `src/aether/ports/`.
* **Target Files**: `src/aether/ports/*.py`
* **Normative Specs**: [`spec.md` §4](../spec.md#4-ports), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I2, I3)](../spec.md#2-invariants)
* **Exit Criteria**: All method signatures are `async`, payloads are Pydantic-serializable, zero `dict[str, Any]` or live file/path handles in public signatures. Reflection test passes.

### TASK-003: Kernel Dispatch & Policy Engine Choke Point
* **Description**: Build TCB kernel authorization and dispatch choke point in `src/aether/kernel/dispatch.py`.
* **Target Files**: `src/aether/kernel/dispatch.py`, `src/aether/kernel/policy.py`
* **Normative Specs**: [`spec.md` §5](../spec.md#5-execution), [`spec.md` §2 (I5, I8)](../spec.md#2-invariants), [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Exit Criteria**: Grant leases verified immediately prior to effect execution. Architecture test proves no bypass path exists outside `dispatch.py`.

### TASK-004: WorkflowStep Node & Socket Types
* **Description**: Implement typed `WorkflowStep[In, Out]` node definition and socket types for the graph framework.
* **Target Files**: `src/aether/workflow/step.py`
* **Normative Specs**: [ADR-0013 (M0)](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Pyright strict type check passes with zero errors.

---

## Epic 2: Measurement Rig & Instrument Blockers

### TASK-010: Standalone Upstream Repository Cache Utility (Blocker B1)
* **Description**: Build standalone utility to clone and resolve task base commits across 12 upstream SWE-bench repos.
* **Target Files**: `src/aether/measurement/repo_cache.py`, `scripts/resolve_swebench_bases.py`
* **Normative Specs**: [`measurement.md` §2 (B1)](../measurement.md#2-instrument-blockers), [ADR-0002](../decisions/0002-no-number-before-the-floor.md)
* **Exit Criteria**: Resolves base commits without network errors for sample tasks.

### TASK-011: Local Model Provider Adapter (Blocker B2)
* **Description**: Implement `ModelProvider` adapter connecting to local OpenAI-compatible endpoint.
* **Target Files**: `src/aether/adapters/model_provider/openai_local.py`
* **Normative Specs**: [`measurement.md` §2 (B2)](../measurement.md#2-instrument-blockers), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md)
* **Exit Criteria**: Adapter passes `ModelProvider` conformance test suite.

### TASK-012: Statistical Engine & A/A Variance Floor
* **Description**: Implement stdlib statistical module for exact McNemar test, Holm–Bonferroni correction, and bootstrap CIs.
* **Target Files**: `src/aether/measurement/statistics.py`
* **Normative Specs**: [`measurement.md` §3](../measurement.md#3-the-aa-variance-floor), [ADR-0003](../decisions/0003-statistical-admission-protocol.md)
* **Exit Criteria**: Passes unit tests with pinned JSON fixtures against known statistical benchmarks.

---

## Epic 3: Walking Skeleton & Engine (Milestone M1a)

### TASK-020: 4-Node Linear DAG Executor
* **Description**: Build sequential executor running the linear graph: `retrieve → generate → apply → evaluate`.
* **Target Files**: `src/aether/workflow/executor.py`, `src/aether/workflow/nodes/*.py`
* **Normative Specs**: [ADR-0013 (M1a)](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Linear graph runs unconditionally end-to-end on sample task.

### TASK-021: Performance Timers (Worktree & AST Parse)
* **Description**: Instrument timers for worktree creation and AST parse-and-validate in developer slice.
* **Target Files**: `src/aether/measurement/timers.py`
* **Normative Specs**: [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md)
* **Exit Criteria**: Latency values measured and published to `docs/rationale/benchmarks/performance_timers.md`.

### TASK-022: Headless Engine API & Event Bus
* **Description**: Implement `engine.py` headless API emitting append-only typed event stream generated from `domain/events.py`.
* **Target Files**: `src/aether/engine.py`, `src/aether/domain/events.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients)
* **Exit Criteria**: Event catalog drift check passes in CI.

---

## Epic 4: Security, Context & Optimizations (Milestone M2 & M3)

### TASK-030: Shell AST Classifier & TaintGate
* **Description**: Implement shell command AST classifier for escalation taxonomy (`Reject | AskRuleMatch | AskFailClosed`).
* **Target Files**: `src/aether/agency/context/taint_gate.py`, `src/aether/kernel/shell_ast.py`
* **Normative Specs**: [ADR-0008](../decisions/0008-shell-ast-classifies.md), [`spec.md` §5](../spec.md#5-execution)
* **Exit Criteria**: Classifies dangerous commands; auto-denial loop halts at 3 consecutive / 20 total.

### TASK-031: 5-Layer Prompt Cache Architecture
* **Description**: Implement prompt assembler with 5 prefix layers and 4 explicit `cache_control` breakpoints.
* **Target Files**: `src/aether/agency/context/assembler.py`
* **Normative Specs**: [ADR-0010](../decisions/0010-context-prefix-layers.md), [`spec.md` §2 (I10)](../spec.md#2-invariants)
* **Exit Criteria**: CI cache hit-rate test meets target floor over fixed replay.

### TASK-032: Per-Node Digest Memoization
* **Description**: Implement node execution caching keyed by input digest for subtree re-execution during ablations.
* **Target Files**: `src/aether/workflow/memoization.py`
* **Normative Specs**: [ADR-0013 (M2)](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Unchanged subtrees skip execution on pipeline rerun.
