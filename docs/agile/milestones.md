---
status: rationale
updated: 2026-08-05
---

# AETHER v3.0.0 — Falsifiable Milestone Exit Gates

Per [ADR-0009](../decisions/0009-gates-are-the-schedule.md), a milestone is complete **only when all its exit gates pass cleanly in CI**. A prose description is not a gate; every gate listed below is backed by an automated test or mechanical verification check.

---

## Blocker Exit Gates

### Blocker B1 — Upstream Repository Cache
* **Specification**: [`measurement.md` §2 (B1)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1**: Standalone clone utility correctly resolves task base commits for all 12 upstream repositories without network errors.
* **Exit Gate 2**: Test script runs git commit resolution with zero `fatal: invalid reference:` errors across a sample of 20 SWE-bench tasks.

### Blocker B2 — Local OpenAI-Compatible Endpoint
* **Specification**: [`measurement.md` §2 (B2)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1**: `ModelProvider` adapter connects to local endpoint and completes structured JSON generation requests without timeouts.

### Blocker B3 — Isolated Evaluation Container & Canary Test
* **Specification**: [`measurement.md` §2 (B3)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1**: Worktree execution is isolated inside container; host `.pth` files do not leak `src/` into evaluation environment.
* **Exit Gate 2 (Canary Test)**: CI includes a canary test asserting that a deliberately broken candidate fails evaluation.

### Blocker B4 — Typed Instrument Error Handling
* **Specification**: [`measurement.md` §2 (B4)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1**: Evaluator returns typed `GateReport` with tri-state outcomes (`True` / `False` / `None`).
* **Exit Gate 2**: Exit code 127 (command not found) or uncollectable test runner errors yield `instrument_error` (i.e. `GateReport.status = None`), never a test failure.

---

## Architecture Milestone Exit Gates

### Milestone M0 — Pure Domain & Wire Protocols
* **Specification**: [`spec.md` §3–4](../spec.md#3-structure), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md)
* **Exit Gate 1 (`domain-is-pure`)**: `import-linter` contract asserts zero DB, HTTP, or filesystem imports inside `src/aether/domain/`.
* **Exit Gate 2 (`wire-serializable-ports`)**: Reflection contract asserts all methods in `src/aether/ports/` are `async` and use only serializable payloads (no live handles, callables, generators, or `Path` objects).
* **Exit Gate 3 (`tcb-isolation`)**: `import-linter` contract asserts `src/aether/kernel/` policy & dispatch cannot be imported or modified by `agency/` or `evolution/`.
* **Exit Gate 4**: `WorkflowStep[In, Out]` node and socket types land with strict Pyright typing (zero errors).

### Milestone M1a — Walking Skeleton (4-Node Linear DAG)
* **Specification**: [ADR-0013](../decisions/0013-workflow-dag-phased.md), [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md)
* **Exit Gate 1**: Walking skeleton executes the 4-node pipeline (`retrieve → generate → apply → evaluate`) end-to-end via headless `engine.py`.
* **Exit Gate 2 (`dispatch-choke-point`)**: Architecture test proves all side-effects pass through `src/aether/kernel/dispatch.py` with verified grant leases before execution.
* **Exit Gate 3**: Conformance tests pass for initial 8 core ports (`ModelProvider`, `Workspace`, `WorktreeManager`, `ToolRegistry`, `PolicyEngine`, `ResourceGovernor`, `TrajectoryStore`, `Evaluator`).
* **Exit Gate 4**: Benchmarks for initial performance timers (Worktree creation & AST parse-and-validate) recorded in `docs/rationale/benchmarks/`.

### Milestone M2 — Per-Node Memoization & Ablation Engine
* **Specification**: [ADR-0013](../decisions/0013-workflow-dag-phased.md), [ADR-0007](../decisions/0007-architect-editor-seam.md), [ADR-0010](../decisions/0010-context-prefix-layers.md)
* **Exit Gate 1**: Subtree re-execution skips unchanged nodes based on input digest hash.
* **Exit Gate 2 (Ablation 1)**: Generated context layer tested against equal-budget hand-authored brief; cleared or deleted per [ADR-0010](../decisions/0010-context-prefix-layers.md).
* **Exit Gate 3 (Ablation 2)**: Dual-model Architect/Editor seam ([ADR-0007](../decisions/0007-architect-editor-seam.md)) ablated against single-model baseline.

### Milestone M3 — Dynamic Branching & Best-of-N Fan-Out
* **Specification**: [ADR-0003](../decisions/0003-statistical-admission-protocol.md), [ADR-0013](../decisions/0013-workflow-dag-phased.md)
* **Exit Gate 1**: Workflow DAG supports conditional branches and multi-candidate fan-out.
* **Exit Gate 2**: Admission pipeline enforces exact McNemar test, Holm–Bonferroni family-wise error correction ($\alpha = 0.05$), $N \ge 50$.
