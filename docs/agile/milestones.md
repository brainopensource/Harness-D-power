---
status: normative
updated: 2026-08-06
---

# AETHER v3.0.0 — Falsifiable Milestone Exit Gates

Per [ADR-0009](../decisions/0009-gates-are-the-schedule.md), a milestone is complete **only when all its exit gates pass cleanly in CI**. A prose description is not a gate; every gate listed below is backed by an automated test or mechanical verification check.

**This file is `normative`.** Its gate tables decide when a phase may end, which is binding content, so it counts against the word budget like anything else that binds. Tagging it `rationale` to stay exempt was a self-declared exemption the budget could not detect — see [`../README.md`](../benchmarks/results/README.md).

**Every gate here ships with a test proving it can fail.** A gate that cannot fail is not counted as a gate, and it is the most expensive bug this project can have.

---

## Blocker Exit Gates

### Blocker B1 — Manifest-Driven Upstream Repository Cache
* **Specification**: [`measurement.md` §2 (B1)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1**: The repo set is **derived from the pinned task manifest**, not hard-coded. Given a manifest, the utility clones exactly the distinct `repo` values it names, and adding a task from a new repository requires no code change.
* **Exit Gate 2**: Resolves **100% of base commits** for the pinned floor-manifest task set, with zero `fatal: invalid reference:` errors.
* **Exit Gate 3**: The cache is **content-addressed and offline-replayable** — a second run with the network disabled resolves every base commit from cache.

### Blocker B2 — Local OpenAI-Compatible Endpoint
* **Specification**: [`measurement.md` §2 (B2)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1 (B2a)**: Endpoint reachable; a structured JSON generation request completes without timeout. *(This gate is satisfied today — it is what "B2 resolved" referred to.)*
* **Exit Gate 2 (B2b)**: The `ModelProvider` adapter **passes the parametrized conformance suite** ([ADR-0005](../decisions/0005-eight-ports-adapter-first.md)). Until `src/aether/` holds an adapter this gate is `None` — unmeasured, never silently passed.

### Blocker B4 — Typed Instrument Error Handling
> **Precedes the A/A floor** ([`roadmap.md`](./roadmap.md)). It is a pure domain type; sequencing it after the floor lets instrument errors into the floor's denominator.
* **Specification**: [`measurement.md` §2 (B4)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1**: `Evaluator` returns a typed tri-state `GateReport` (`PASSED` / `FAILED` / `NONE`), with `instrument_error` populated **iff** status is `NONE`.
* **Exit Gate 2**: Exit code 127, uncollectable test-runner errors, and a test-command hash mismatch against the manifest each yield `NONE`, **never `FAILED`**. Negative test: a fixture producing each of the three must fail the suite if it maps to `FAILED`.
* **Exit Gate 3**: Outcomes with status `NONE` are **excluded from the resolve-rate denominator** and reported as a separate instrument-error rate.

### Blocker B3 — Isolated Evaluation Container & Canary Test
* **Specification**: [`measurement.md` §2 (B3)](../measurement.md#2-instrument-blockers)
* **Exit Gate 1**: Worktree execution is isolated inside the container; host `.pth` files do not leak `src/` into the evaluation environment.
* **Exit Gate 2 (Canary Test)**: CI includes a canary asserting that a **deliberately broken candidate fails** evaluation.
* **Exit Gate 3 (blocking on the floor)**: The Gate 2 canary is executed **in the A/A floor environment before the floor run**. If a broken candidate passes there, the floor is blocked on B3 regardless of roadmap order.

---

## Architecture Milestone Exit Gates

### Milestone M0 — Pure Domain & Wire Protocols
* **Specification**: [`spec.md` §3–4](../spec.md#3-structure), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md), [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Exit Gate 0 (TCB path migration — blocking, `TASK-000`)**: `.importlinter` `tcb-isolation` and CI `TCB_PATHS` name `src/aether/…` paths, landed **in the same change as the first `src/aether/` file**. Acceptance is negative: `tests/unit/test_path_constant_drift.py` **demonstrably fails** when the constants select only `src/sagiha/`. Until this gate passes, [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md) is enforced by nothing while CI stays green — the ADR names this trap itself.
* **Exit Gate 1 (`domain-is-pure`)**: `import-linter` contract asserts zero DB, HTTP, or filesystem imports inside `src/aether/domain/`.
* **Exit Gate 2 (`wire-serializable-ports`)**: Reflection contract asserts all methods in `src/aether/ports/` are `async` and use only serializable payloads (no live handles, callables, generators, `Path` objects, `dict[str, Any]`, or `Grant` in any public signature).
* **Exit Gate 3 (`tcb-isolation`)**: `import-linter` contract asserts `src/aether/kernel/` policy & dispatch cannot be imported by `agency/` or `evolution/`, and that the **full lattice** of [`spec.md` §3](../spec.md#3-structure) is encoded — every package has a declared position.
* **Exit Gate 4**: `WorkflowStep[In, Out]` node and socket types land with strict Pyright typing (zero errors).
* **Exit Gate 5 (`TASK-005`)**: The conformance meta-suite exists and **fails when a port's adapter parameter list is empty**. Mock adapters satisfy [ADR-0005](../decisions/0005-eight-ports-adapter-first.md)'s entry rule only because this suite tests them.

### Milestone M1a — Walking Skeleton (4-Node Linear DAG)
* **Specification**: [ADR-0013](../decisions/0013-workflow-dag-phased.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md), [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md)
* **Exit Gate 1**: Walking skeleton executes the 4-node pipeline (`retrieve → generate → apply → evaluate`) end-to-end via headless `engine.py`, **from a schema-validated declarative topology** ([ADR-0014](../decisions/0014-workflow-topology-is-data.md)); the executor refuses a topology failing any static check.
* **Exit Gate 2 (`dispatch-choke-point`)**: Architecture test proves all side-effects pass through `src/aether/kernel/dispatch.py` with grants verified **at the point of effect**, not at authorization.
* **Exit Gate 3 (re-scoped)**: Conformance suites pass for the **four boundaries the skeleton actually walks** — `ModelProvider`, `Workspace`/`WorktreeManager`, `ToolRegistry`, `Evaluator`. The remaining ports (`PolicyEngine`, `ResourceGovernor`, `TrajectoryStore`, `Indexer`) enter per [ADR-0005](../decisions/0005-eight-ports-adapter-first.md) as their adapters land and are gated then. *Rev. 2: the previous "8 ports" wording required eight adapters against a backlog funding one — a gate unreachable from its own plan, which is a tripwire guaranteed to fire.*
* **Exit Gate 4**: Worktree-creation and AST parse-and-validate timers recorded in [`docs/rationale/benchmarks/`](../benchmarks/results/README.md). These two numbers decide [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md)'s F1 fork.
* **Exit Gate 5**: `ResourceGovernor` reserve → commit → release is exercised end-to-end; the dispatcher **refuses any effect without a live lease**, so after-the-fact accounting is structurally unrepresentable.

### Milestone M1a+ — Bounded Repair Edge
> The repair edge is named in [`vision.md`](../vision.md) §2 as *"the single largest lever on score in the entire system."* Before rev. 2 it had no node, no gate and no task.
* **Specification**: [ADR-0013](../decisions/0013-workflow-dag-phased.md) (rev. 2)
* **Exit Gate 1**: A topology declaring `repair` executes `evaluate →(fail, k)→ repair → apply → evaluate`, statically unrolled to `max_iterations`.
* **Exit Gate 2**: The validator **rejects** a repair block with no `max_iterations` and one exceeding the bound. Negative test required.
* **Exit Gate 3**: A `GateReport` of `NONE` routes to the terminal flag node and **never into repair** — an instrument failure is not a repair candidate.
* **Exit Gate 4**: Each repair iteration reserves its own budget; exhausting it terminates the loop rather than the run.

### Milestone M1a++ — Inner Loop Context Lift
* **Specification**: [Sprint 3.5 Rationale](sprints/sprint-03.5.md), [ADR-0010](../decisions/0010-context-prefix-layers.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md)
* **Exit Gate 1**: `EditFormat` seam (`TASK-037`) passes generic conformance suite for diff & whole-file formats.
* **Exit Gate 2**: Node registry resolves step implementations dynamically from kind (`TASK-038`).
* **Exit Gate 3**: `RepairStep` re-reads worktree files dynamically and injects actual state into repair prompts (`TASK-039`).

### Milestone M1a++R — Instrument Restoration
* **Specification**: [`measurement.md` §2](../measurement.md#2-instrument-blockers), [`spec.md` §2 (I7)](../spec.md#2-invariants)
* **Exit Gate 1**: Invariant I7 (`tests_unmodified`) enforced in TCB evaluator with negative test (`TASK-049`).
* **Exit Gate 2**: Test-source injection demoted to named ablation arm with `False` default (`TASK-049b`).
* **Exit Gate 3**: Internal A/A floor executed with derived N and exact McNemar variance metrics.

### Milestone M1b — Capability & Composition Layer
* **Specification**: [ADR-0005](../decisions/0005-eight-ports-adapter-first.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md), [ADR-0018](../decisions/0018-agency-below-workflow.md)
* **Exit Gate 1**: `agency/` created under `workflow/` in import lattice (`TASK-053`).
* **Exit Gate 2**: `ContextSource` and `Inference` protocols extracted and swappable (`TASK-054`, `TASK-055`).
* **Exit Gate 3**: `ModelNode` + `RoleSpec` replace old monolithic node classes with golden-prompt test (`TASK-057`).
* **Exit Gate 4**: Deterministic record/replay cassette engine achieves 100 turns in <50ms with byte-for-byte determinism (`TASK-006`).

### Milestone M2 — Memoization & Ablation Engine
* **Specification**: [ADR-0013](../decisions/0013-workflow-dag-phased.md), [ADR-0003](../decisions/0003-statistical-admission-protocol.md), [ADR-0007](../decisions/0007-architect-editor-seam.md), [ADR-0010](../decisions/0010-context-prefix-layers.md)
* **Exit Gate 1 (M2-eng)**: Subtree re-execution skips unchanged nodes on input-digest match; a changed node invalidates exactly its descendants.
* **Exit Gate 2 (Ablation 1 — repair)**: **repair-on vs repair-off clears the noise floor** under [ADR-0003](../decisions/0003-statistical-admission-protocol.md) rev. 2, at derived N on the HOLDOUT split, with cost per resolved task within the declared margin. **This is the first capability ablation**, ahead of the two below: it is the largest expected effect, so it is the measurement worth the most.
* **Exit Gate 3 (Ablation 2 — generated context)**: Generated repository-context layer tested against a hand-authored brief of equal token budget; cleared or **deleted** per [ADR-0010](../decisions/0010-context-prefix-layers.md).
* **Exit Gate 4 (Ablation 3 — Architect/Editor)**: Dual-model seam ([ADR-0007](../decisions/0007-architect-editor-seam.md)) ablated against the single-model baseline; enabled only on a gain whose CI excludes the floor at acceptable cost per resolved task.
* **Exit Gate 5 (compaction)**: A task whose trajectory exceeds the context window **completes via compaction** on a pinned long-task fixture. Compaction touches only L5; a compaction that would rewrite L1–L4 fails by type.
* **Exit Gate 6 (prompt-cache floor)**: Harness-side **prefix stability** — byte-identical-prefix rate over a fixed recorded replay — meets its calibrated floor ([`spec.md` §2 I10](../spec.md#2-invariants)).

### Milestone M3 — Dynamic Branching & Best-of-N Fan-Out
* **Specification**: [ADR-0003](../decisions/0003-statistical-admission-protocol.md), [ADR-0013](../decisions/0013-workflow-dag-phased.md)
* **Exit Gate 1**: Workflow DAG supports conditional branches and declared multi-candidate fan-out; every fan-out node has a declared join.
* **Exit Gate 2**: Admission pipeline enforces exact McNemar, Holm–Bonferroni family-wise correction ($\alpha = 0.05$), and **derived N at ≥ 0.80 power** for the declared minimal effect. The statistics module **refuses to compute corrected p-values for an undeclared family**.
* **Exit Gate 3**: Best-of-N fan-out is **cache-sequenced** — candidate 1 warms the shared prefix before 2..N are released. Naive parallel fan-out over a cold prefix is not expressible in a valid topology.
* **Exit Gate 4**: Child leases carve from the parent reservation; cancelling N−1 losers refunds the parent, not the global pool.

### Milestone M4 — Benchmark Delivery (SWE-bench & SEALED Publication)
* **Specification**: [`measurement.md` §4 & §6](../measurement.md#6-pre-publication-verification-gate)
* **Exit Gate 1 (`TASK-071`)**: Pinned SWE-bench manifest with bidirectional validity canary passed on 100% of candidate tasks.
* **Exit Gate 2 (`TASK-072`)**: SWE-bench A/A floor executed, deriving benchmark-specific discordance rate ($p_{01}, p_{10}$) and required $N$.
* **Exit Gate 3 (`TASK-073` & `TASK-015b`)**: Paired lift runs executed for AETHER vs. bare-model and AETHER vs. OpenHands arm on same manifest.
* **Exit Gate 4 (`TASK-074`)**: Publication run on SEALED dataset satisfying all 7 conditions of [`measurement.md` §6](../measurement.md#6-pre-publication-verification-gate).

### Milestone M5 — Harness Evolution & Meta-Loop
* **Specification**: [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md), [ADR-0017](../decisions/0017-subagent-capability-attenuation.md)
* **Exit Gate 1**: `src/aether/evolution/` package established and covered under TCB isolation.
* **Exit Gate 2**: Declarative topology mutation engine operates under attenuated subagent capabilities.

