---
status: rationale
updated: 2026-08-06
---

# AETHER v3.0.0 — Product & Technical Backlog

This backlog catalogs all Epics and User Stories for building AETHER v3.0.0. All tasks map directly to normative rules in [`docs/spec.md`](../spec.md), [`docs/measurement.md`](../measurement.md), or [`docs/decisions/`](../decisions/README.md).

**Every exit gate in [`milestones.md`](./milestones.md) has a task here that funds it.** The reverse check is the one that matters: a gate with no funded task is a tripwire guaranteed to fire, and a tripwire that always fires gets ignored — which is [ADR-0009](../decisions/0009-gates-are-the-schedule.md)'s own reversal condition.

---

## Epic 0: Enforcement Migration (Milestone M0 — **blocking**)

### TASK-000: Migrate TCB Path Constants to `src/aether/`
* **Description**: Move `.importlinter` `tcb-isolation` targets and CI `TCB_PATHS` from `src/sagiha/…` to `src/aether/…`, **in the same change as the first `src/aether/` file**.
* **Target Files**: `.importlinter`, `.github/workflows/ci.yml`, `tests/unit/test_path_constant_drift.py`
* **Normative Specs**: [ADR-0006 "The trap this ADR must not fall into"](../decisions/0006-tcb-boundary-and-meta-loop-authority.md), [`milestones.md` M0 Gate 0](./milestones.md#milestone-m0--pure-domain--wire-protocols)
* **Exit Criteria**: The drift test **demonstrably fails** when the constants select only `src/sagiha/`. No contract selects zero modules.
* **Priority**: **First PR of Sprint-01.** Until it lands, ADR-0006 is enforced by nothing while CI reports green.

---

## Epic 1: TCB Kernel & Core Domain (Milestone M0)

### TASK-001: Pure Domain Data Models
* **Description**: Implement immutable Pydantic domain models in `src/aether/domain/`. Zero I/O dependencies.
* **Target Files**: `src/aether/domain/*.py`
* **Normative Specs**: [`spec.md` §2 (I1)](../spec.md#2-invariants), [AGENTS.md Guideline 2](../../AGENTS.md)
* **Exit Criteria**: `import-linter` contract `domain-is-pure` passes green. All datetimes tz-aware; budget arithmetic is integer-only by type.

### TASK-002: Wire-Serializable Port Protocols
* **Description**: Define typed `Protocol` boundaries for the 8 core port areas (9 protocols) in `src/aether/ports/`.
* **Target Files**: `src/aether/ports/*.py`
* **Normative Specs**: [`spec.md` §4](../spec.md#4-ports), [ADR-0005 rev. 2](../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I2, I3)](../spec.md#2-invariants)
* **Exit Criteria**: Each protocol lands with a mock adapter, a conformance test, **and its first real adapter named**. Reflection meta-test passes: all `async`, no `Path`/handle/callable/generator/live object, no `dict[str, Any]`, **no `Grant` in any public signature**.

### TASK-003: Kernel Dispatch & Policy Engine Choke Point
* **Description**: Build the TCB authorization and dispatch choke point.
* **Target Files**: `src/aether/kernel/dispatch.py`, `src/aether/kernel/policy.py`
* **Normative Specs**: [`spec.md` §5](../spec.md#5-execution), [`spec.md` §2 (I5, I8)](../spec.md#2-invariants), [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Exit Criteria**: Grants verified immediately prior to effect execution. Architecture test proves no bypass path. **The concrete `PolicyEngine` lives in `kernel/`, never `adapters/`** ([`spec.md` §4](../spec.md#4-ports) residency rule).

### TASK-004: WorkflowStep Node & Socket Types
* **Description**: Implement typed `WorkflowStep[In, Out]` and socket types.
* **Target Files**: `src/aether/workflow/step.py`
* **Normative Specs**: [ADR-0013 (M0)](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Pyright strict passes with zero errors. Steps receive **no adapter handles** — effects reach a dispatch facade injected by the executor.

### TASK-005: Conformance Meta-Suite Harness
* **Description**: One parametrized suite, N adapters — the enforcement mechanism for I4, previously unfunded.
* **Target Files**: `tests/conformance/`
* **Normative Specs**: [`spec.md` §2 (I4)](../spec.md#2-invariants), [ADR-0005 rev. 2](../decisions/0005-eight-ports-adapter-first.md)
* **Exit Criteria**: **The meta-test fails when a port's adapter parameter list is empty.** A suite that selects no adapter tests nothing — same defect class as a contract that selects no file.

### TASK-006: Mock Adapter Set & Record/Replay Cassettes
* **Description**: Mock adapters for every port, plus record/replay cassettes for deterministic CI.
* **Target Files**: `src/aether/adapters/mock/*.py`, `tests/fixtures/cassettes/`
* **Normative Specs**: [ADR-0005 rev. 2](../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §7](../spec.md#7-measurement)
* **Exit Criteria**: 100 turns in under 50 ms with no API call and no container. Replay is **byte-for-byte deterministic**. Mocks raise on unimplemented paths — they never return a plausible value.

---

## Epic 2: Measurement Rig & Instrument Blockers

### TASK-010: Manifest-Driven Upstream Repository Cache (Blocker B1)
* **Description**: Standalone utility cloning and resolving base commits for the repositories **named by the pinned manifest**.
* **Target Files**: `src/aether/measurement/repo_cache.py`, `scripts/resolve_swebench_bases.py`
* **Normative Specs**: [`measurement.md` §2 (B1)](../measurement.md#2-instrument-blockers), [ADR-0002](../decisions/0002-no-number-before-the-floor.md)
* **Exit Criteria**: Repo set derived from the manifest, never hard-coded. 100% of base commits resolve for the floor manifest. Cache is content-addressed and **offline-replayable**.

### TASK-011: Local Model Provider Adapter (Blocker B2b)
* **Description**: `ModelProvider` adapter for the local OpenAI-compatible endpoint. Named as the first **real** adapter satisfying TASK-002's mock clause for this port.
* **Target Files**: `src/aether/adapters/model_provider/openai_compatible.py`
* **Normative Specs**: [`measurement.md` §2 (B2)](../measurement.md#2-instrument-blockers), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md)
* **Exit Criteria**: Passes the `ModelProvider` conformance suite. Enforces the request's token ceilings — conservation is kernel policy, not adapter courtesy.

### TASK-012: Statistical Engine & A/A Variance Floor
* **Description**: Port `e0/statistics.py` verbatim (exact McNemar, Holm–Bonferroni, seeded bootstrap), then add the rev. 2 layer: derived-N power simulation and the family gatekeeper.
* **Target Files**: `src/aether/measurement/statistics.py`, `src/aether/measurement/families/`
* **Normative Specs**: [`measurement.md` §3](../measurement.md#3-the-aa-variance-floor), [ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md), [`spec.md` §9](../spec.md#9-standing-rules) (predecessor-code clause — provenance in the module docstring)
* **Exit Criteria**: Pinned JSON fixtures pass. **The module refuses to compute corrected p-values for an undeclared family.** The power simulation is seeded and re-runnable from a family file alone.

### TASK-013: Typed Tri-State `GateReport` (Blocker B4)
* **Description**: The typed distinction between *test failed* and *instrument failed*. Pulled forward from M2 — it is a pure domain type and a **precondition of the A/A floor**.
* **Target Files**: `src/aether/domain/gate.py`, `src/aether/measurement/evaluator.py`
* **Normative Specs**: [`measurement.md` §2 (B4)](../measurement.md#2-instrument-blockers), [`milestones.md` B4](./milestones.md#blocker-b4--typed-instrument-error-handling)
* **Exit Criteria**: Exit-127, uncollectable tests and test-command-hash mismatch all yield `NONE`, never `FAILED`. `NONE` outcomes are **excluded from the resolve-rate denominator** and reported separately. Negative test required.

### TASK-014: Task-Manifest Tooling & Bidirectional Validity Canary
* **Description**: Build, pin and validate task manifests; run the per-task canary; publish exclusions.
* **Target Files**: `src/aether/measurement/manifest.py`, `src/aether/measurement/schemas/manifest_schema.yaml`
* **Normative Specs**: [`measurement.md` §4.2–4.3](../measurement.md#42-splits-and-why-they-are-pinned), [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published), [`schemas_and_contracts.md` §2](../development/schemas_and_contracts.md)
* **Exit Criteria**: A task enters a manifest only if the **gold patch passes and the empty patch fails** on our instrument. **Exclusions are published with a reason** — silent exclusion is the overfitting vector. Manifest and split assignment are TCB; a change is a new hash.

### TASK-016: Evaluation Container & B3 Canary (Blocker B3)
* **Description**: Rootless Podman evaluation container — the isolation that makes a candidate diff visible to the gate scoring it.
* **Target Files**: `src/aether/adapters/sandbox/podman.py`, `containers/eval/`
* **Normative Specs**: [`measurement.md` §2 (B3)](../measurement.md#2-instrument-blockers), [`tech_stack_and_infra.md` §3](../development/tech_stack_and_infra.md), [ADR-0008](../decisions/0008-shell-ast-classifies.md)
* **Exit Criteria**: `--network none`, `--cap-drop all`, `--security-opt no-new-privileges`, read-only root, image **created from digest, never tag**. Two mounts only: the task worktree (RW) and pinned image layers (RO) — **no `.pth` leakage by construction**. **Canary: a deliberately broken candidate must fail evaluation**, and the canary runs in the A/A floor environment before the floor run.
* **Why it matters**: the `.pth` leak is the one instrument defect that *produced numbers*.

### TASK-019: Evaluator Implementation (TCB)
* **Description**: The judge. Runs the task's pinned test command in the evaluation container and returns a tri-state `GateReport`.
* **Target Files**: `src/aether/measurement/evaluator.py`
* **Normative Specs**: [`spec.md` §4](../spec.md#4-ports) (TCB port residency), [`spec.md` §2 (I7)](../spec.md#2-invariants), [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Exit Criteria**: **Lives in `measurement/`, never `adapters/`** — the residency rule is what makes `tcb-isolation` select it. Verifies the test command against the manifest's `test_command_hash` before running; a mismatch is `NONE`, not a result. `import-linter` proves it cannot import `agency/` or `workflow/`.
* **Named as**: the first real adapter for the `Evaluator` port under [ADR-0005](../decisions/0005-eight-ports-adapter-first.md) rev. 2.

### TASK-015: Comparative-Lift Rig (`HarnessUnderTest`)
* **Description**: A runner seam producing paired outcomes for (harness, model, manifest) through **our** evaluator. Arms: bare-model baseline, AETHER, OpenHands.
* **Target Files**: `src/aether/measurement/runner.py`
* **Normative Specs**: [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md) (measurement is a tool, not a port)
* **Exit Criteria**: Same model, same manifest, same evaluator across arms. **Without this the mission statement is unsubstantiable** — [`spec.md` §9](../spec.md#9-standing-rules) forbids citing competitors' published numbers as evidence. Scheduled after the floor, before any public claim.

---

## Epic 3: Walking Skeleton & Engine (Milestone M1a)

### TASK-020: Declarative Topology Executor
* **Description**: Executor running a schema-validated linear graph `retrieve → generate → apply → evaluate`, plus the TCB topology validator.
* **Target Files**: `src/aether/workflow/executor.py`, `src/aether/workflow/validator.py`, `src/aether/workflow/nodes/*.py`, `workflows/linear_v1.yaml`
* **Normative Specs**: [ADR-0013 (M1a)](../decisions/0013-workflow-dag-phased.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md), [`schemas_and_contracts.md` §1](../development/schemas_and_contracts.md)
* **Exit Criteria**: The executor **refuses** any topology failing a static check, with a typed error naming the failed check. Each of the five checks has a malformed fixture proving it can fail. **No `--force` flag exists.**

### TASK-021: Performance Timers (Worktree & AST Parse)
* **Description**: Instrument worktree creation and AST parse-and-validate.
* **Target Files**: `src/aether/measurement/timers.py`
* **Normative Specs**: [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md)
* **Exit Criteria**: Latencies published to [`docs/rationale/benchmarks/performance_timers.md`](../rationale/benchmarks/README.md) **with hardware and method recorded**. These two numbers decide the F1 fork. A run showing nothing is recorded as showing nothing.

### TASK-022: Headless Engine API & Event Bus
* **Description**: `engine.py` headless API emitting an append-only typed event stream generated from `domain/events.py`.
* **Target Files**: `src/aether/engine.py`, `src/aether/kernel/bus.py`, `src/aether/domain/events.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients), [ADR-0013](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Event-catalog drift check passes. **Events never drive node scheduling** — a sensor that must cause work enqueues a task through the engine API. Display consumers are drop-oldest; the trajectory store and harvester are never dropped.

### TASK-017: Git Workspace & Worktree Adapter
* **Description**: `Workspace` + `WorktreeManager` over the `git` CLI via `asyncio.subprocess`.
* **Target Files**: `src/aether/adapters/workspace/git_cli.py`
* **Normative Specs**: [ADR-0005](../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I3)](../spec.md#2-invariants), [`tech_stack_and_infra.md` §3.2](../development/tech_stack_and_infra.md)
* **Exit Criteria**: Passes both conformance suites. **All paths are repo-relative strings — no `Path` crosses the port** (I3). One worktree per candidate under a run-scoped root. This is where the worktree-creation timer (`TASK-021`) lives.
* **Named as**: the first real adapter for the `Workspace`/`WorktreeManager` boundary.

### TASK-018: Built-in Tool Registry & Tool-Execution Container
* **Description**: `ToolRegistry` adapter with the built-in tool set, executing in a **separate** container from the evaluator.
* **Target Files**: `src/aether/adapters/tools/builtin.py`, `containers/tools/`
* **Normative Specs**: [ADR-0005](../decisions/0005-eight-ports-adapter-first.md), [ADR-0015](../decisions/0015-taintgate-provenance-model.md), [ADR-0016](../decisions/0016-mcp-integration-trust-model.md)
* **Exit Criteria**: Catalog **frozen at composition** (I6). **Tool outputs are labelled `untrusted-external` at construction**, not at point of use. Separate image and separate lease class from the evaluator, so a runaway tool loop cannot starve the judge.
* **Named as**: the first real adapter for `ToolRegistry`. MCP ([ADR-0016](../decisions/0016-mcp-integration-trust-model.md)) is a second adapter of the same port, later.

### TASK-026: SQLite Trajectory Store Adapter
* **Description**: Durable append-only event log; a bus consumer like any other.
* **Target Files**: `src/aether/adapters/trajectory_store/sqlite.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md)
* **Exit Criteria**: Passes conformance. WAL mode, no ORM. **Never dropped under backpressure** — display consumers are drop-oldest, the durable log and the measurement harvester are not. Replay from it is byte-for-byte deterministic.
* **Named as**: the first real adapter for `TrajectoryStore`.

### TASK-023: Repair Node & Bounded-Iteration Construct
* **Description**: The repair edge — `evaluate →(fail, k)→ repair → apply → evaluate`, statically unrolled.
* **Target Files**: `src/aether/workflow/nodes/repair.py`, `src/aether/agency/repair.py`, `workflows/linear_repair_v1.yaml`
* **Normative Specs**: [ADR-0013 rev. 2](../decisions/0013-workflow-dag-phased.md), [`milestones.md` M1a+](./milestones.md#milestone-m1a--bounded-repair-edge)
* **Exit Criteria**: `max_iterations` mandatory and bounded; validator rejects an unbounded repair block. Each iteration reserves its own budget. **A `NONE` gate result never routes into repair.** Test output is tail-biased-truncated to keep the failure block, not the pass list.
* **Why it matters**: [`vision.md`](../vision.md) §2 calls this *"the single largest lever on score in the entire system."* It had zero tasks before the Phase 0 lock.

### TASK-024: Compaction v1
* **Description**: Deterministic structural compaction of L5 — drop superseded file snapshots, collapse resolved tool exchanges.
* **Target Files**: `src/aether/agency/context/compactor.py`
* **Normative Specs**: [ADR-0010](../decisions/0010-context-prefix-layers.md), [`milestones.md` M2 Gate 5](./milestones.md#milestone-m2--memoization--ablation-engine)
* **Exit Criteria**: A task exceeding the context window **completes via compaction** on a pinned long-task fixture. **Compaction never touches L1–L4** — the assembler exposes no API for it. Model-summarized compaction is a *mechanism* and does not promote without its own ablation.

---

## Epic 4: Security, Context & Optimizations (Milestones M2 & M3)

### TASK-030a: Shell AST Classifier
* **Description**: Parse shell commands to an AST before execution; drive the `Reject | AskRuleMatch | AskFailClosed` taxonomy and emit the `widens_capability` flag.
* **Target Files**: `src/aether/kernel/shell_ast.py`
* **Normative Specs**: [ADR-0008](../decisions/0008-shell-ast-classifies.md), [`spec.md` §5](../spec.md#5-execution)
* **Exit Criteria**: Classifies dangerous commands; auto-denial bounded at **3 consecutive / 20 total**, after which the run halts. **No security claim is made for the parser** in any document, ADR or commit message — the sandbox is the perimeter.

### TASK-030b: TaintGate Provenance & Red-Team Gate
* **Description**: Provenance labels on every context span, deterministic propagation, and the enforcing predicate in the policy engine.
* **Target Files**: `src/aether/agency/context/taint_gate.py`, `src/aether/kernel/policy.py`, `tests/security/injection_corpus/`
* **Normative Specs**: [ADR-0015](../decisions/0015-taintgate-provenance-model.md), [`spec.md` §2 (I11)](../spec.md#2-invariants)
* **Exit Criteria**: Pinned injection corpus produces **zero capability grants**; a deliberately permissive predicate makes the corpus produce one (the gate can fail). The gate labels, the **policy decides** — the predicate lives in the TCB.
* **Note**: split from a single task that conflated this with TASK-030a. Different mechanisms, different layers; merged, neither gets designed.

### TASK-031: Five-Layer Prompt Prefix & Cache Architecture
* **Description**: Context assembler with the five fixed layers and at most four cache breakpoints.
* **Target Files**: `src/aether/agency/context/assembler.py`
* **Normative Specs**: [ADR-0010](../decisions/0010-context-prefix-layers.md), [`spec.md` §2 (I10)](../spec.md#2-invariants)
* **Exit Criteria**: Layer order L1 system/policy · L2 tool schemas · L3 repo brief · L4 task · L5 dialogue. CI floor on **harness-side prefix stability** (byte-identical-prefix rate over a fixed replay), not on a provider-reported hit rate.

### TASK-032: Per-Node Digest Memoization
* **Description**: Node execution caching keyed by input digest for subtree re-execution during ablations.
* **Target Files**: `src/aether/workflow/memoization.py`
* **Normative Specs**: [ADR-0013 (M2)](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Unchanged subtrees skip execution; a changed node invalidates exactly its descendants. Digest = `sha256(node_kind, impl_version, canonical payload)`.

### TASK-033: Best-of-N Cache Sequencing
* **Description**: Warm the shared prefix on candidate 1 before releasing candidates 2..N.
* **Target Files**: `src/aether/workflow/executor.py`, `src/aether/agency/context/assembler.py`
* **Normative Specs**: [ADR-0010](../decisions/0010-context-prefix-layers.md) (consequence), [ADR-0014](../decisions/0014-workflow-topology-is-data.md) (schema-visible)
* **Exit Criteria**: Naive parallel fan-out over a cold prefix is **not expressible in a valid topology** — the schema requires a `cache_sequencing` value on every declared fan-out site.

### TASK-025: Architect/Editor Seam (ships disabled)
* **Description**: Decoupled `architect.py` (plan, no write tools) and `editor.py` (surgical edits), with enablement bound to config and defaulting to single-model.
* **Target Files**: `src/aether/agency/architect.py`, `src/aether/agency/editor.py`
* **Normative Specs**: [ADR-0007](../decisions/0007-architect-editor-seam.md)
* **Exit Criteria**: **Ships off.** Flipping one config value is one ablation arm. Enabled only on an M2 ablation whose CI excludes the noise floor at cost per resolved task within the declared margin ([ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md)).
* **Note**: if the ablation does not clear, **the seam is deleted, not left dormant** — a disabled code path nobody measures is debt, not optionality.

### TASK-035: Conditional Branching & Best-of-N Fan-Out
* **Description**: Executor support for conditional edges and declared multi-candidate fan-out — parallel candidates as graph structure.
* **Target Files**: `src/aether/workflow/executor.py`, `src/aether/workflow/validator.py`
* **Normative Specs**: [ADR-0013 (M3)](../decisions/0013-workflow-dag-phased.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md)
* **Exit Criteria**: `when: on_pass | on_fail | on_instrument_error` routing honoured; **`on_instrument_error` may only reach a terminal flag node**. Every fan-out site has a declared join — unjoined fan-out leaks worktrees and leases. N parallel candidates ⇒ N child leases from one parent reservation (`TASK-034`).

### TASK-034: `ResourceGovernor` Reserve / Commit / Release
* **Description**: The budget triple as an atomic ledger.
* **Target Files**: `src/aether/kernel/governor.py`
* **Normative Specs**: [`spec.md` §5](../spec.md#5-execution), [`tech_stack_and_infra.md` §4.5](../development/tech_stack_and_infra.md)
* **Exit Criteria**: The dispatcher **refuses any effect without a live lease**, making after-the-fact accounting structurally unrepresentable. Integer arithmetic only. Overrun records a typed `BudgetOverrun` event and debits reality. **A child lease's release refunds the parent, not the global pool.**
* **Why it matters**: budget-recorded-after-the-fact was H2 in the predecessor's refactor plan, and it worsens under Best-of-N fan-out.

---

## Gate coverage map

**Read this direction: gate → task.** A gate with no task is a tripwire guaranteed to fire, and a tripwire that always fires gets ignored ([ADR-0009](../decisions/0009-gates-are-the-schedule.md)'s own reversal condition). The reverse direction — task with no gate — is a smaller problem, and this table does not check it.

Every exit gate in [`milestones.md`](./milestones.md) and the task that funds it:

| Gate | Funded by |
| :--- | :--- |
| B1 · 1–3 | `TASK-010` |
| B2 · 1 (B2a) | *resolved — endpoint exists* |
| B2 · 2 (B2b) | `TASK-011` |
| B4 · 1–3 | `TASK-013`, `TASK-019` |
| B3 · 1–3 | `TASK-016` |
| M0 · 0 TCB migration | `TASK-000` |
| M0 · 1 `domain-is-pure` | `TASK-001` |
| M0 · 2 wire-serializable | `TASK-002` |
| M0 · 3 `tcb-isolation` + full lattice | `TASK-000`, `TASK-003` |
| M0 · 4 `WorkflowStep` types | `TASK-004` |
| M0 · 5 conformance meta-suite | `TASK-005` |
| M1a · 1 skeleton from a validated topology | `TASK-020` |
| M1a · 2 dispatch choke point | `TASK-003` |
| M1a · 3 conformance, four boundaries | `TASK-011`, `TASK-017`, `TASK-018`, `TASK-019`, `TASK-005` |
| M1a · 4 F1 timers | `TASK-021` |
| M1a · 5 reserve/commit/release | `TASK-034` |
| M1a+ · 1–4 repair edge | `TASK-023` |
| M2 · 1 memoization | `TASK-032` |
| M2 · 2 **repair ablation** (first) | `TASK-023`, `TASK-012` |
| M2 · 3 generated-context ablation | `TASK-031` |
| M2 · 4 Architect/Editor ablation | `TASK-025` |
| M2 · 5 compaction | `TASK-024` |
| M2 · 6 prefix-stability floor | `TASK-031` |
| M3 · 1 branching & fan-out | `TASK-035` |
| M3 · 2 statistical admission | `TASK-012` |
| M3 · 3 cache sequencing | `TASK-033` |
| M3 · 4 child leases | `TASK-034` |

**Not gate-funding, and deliberately so** — these support the gates above rather than closing one: `TASK-006` (mocks and cassettes), `TASK-014` (manifests and validity canary), `TASK-015` (comparative-lift rig), `TASK-022` (engine and bus), `TASK-026` (trajectory store), `TASK-030a`/`TASK-030b` (shell classifier and TaintGate — gated by the I11 red-team corpus in CI rather than by a milestone).

**Four gates had no task before the Phase 0 lock**: all three of B3's, and M2's Architect/Editor ablation. M1a Gate 3 had one adapter funded against eight required. That is the D15 defect class, and this table is the mechanism that keeps it closed.

---

## Backend Roadmap Complexity & Developer Assignment

| Task ID | Feature / Component | Milestone | Complexity | Assigned Developer Role | Technical Complexity & Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-000` | TCB Path Constants Migration | M0 (Sprint 1) | 🟢 Easy | **Junior Developer** | String/path constant updates across `.importlinter`, CI YAML, and path-drift unit tests. Low risk, simple file updates. |
| `TASK-001` | Pure Domain Data Models | M0 (Sprint 1) | 🟢 Easy | **Junior Developer** | Immutable Pydantic models with zero I/O. Straightforward data modeling (enums, typed fields, tz-aware datetimes, integer budget types). |
| `TASK-013` | Typed Tri-State `GateReport` | B4 (Sprint 1) | 🟢 Easy | **Junior Developer** | Pure domain status type (`PASSED`, `FAILED`, `NONE`) with mapping rules. Small scope, clear exit criteria, simple fixtures. |
| `TASK-002` | Wire-Serializable Port Protocols | M0 (Sprint 1) | 🟡 Medium | **Normal Developer** | Defining 9 `Protocol` boundaries in `ports/`. Must strictly enforce `async` signatures, serializable payloads, zero live object handles. |
| `TASK-004` | WorkflowStep Node & Socket Types | M0 (Sprint 1) | 🟡 Medium | **Normal Developer** | Generic typed `WorkflowStep[In, Out]` node and socket generic typing. Requires strong Pyright-strict typing mastery. |
| `TASK-005` | Conformance Meta-Suite Harness | M0 (Sprint 2) | 🟡 Medium | **Normal Developer** | Parametrized test runner for port adapters. Must include meta-tests asserting the suite fails if an adapter parameter list is empty. |
| `TASK-006` | Mock Adapter Set & Cassettes | M0 (Sprint 2) | 🟡 Medium | **Normal Developer** | Implement mock adapters for every port plus deterministic replay cassettes. Byte-for-byte replay verification under 50ms. |
| `TASK-010` | Manifest-Driven Repo Cache | B1 (Sprint 2) | 🟡 Medium | **Normal Developer** | Standalone utility cloning and resolving git base commits from task manifests. Content-addressed offline cache management. |
| `TASK-011` | Local Model Provider Adapter | B2b (Sprint 2) | 🟡 Medium | **Normal Developer** | OpenAI-compatible HTTP adapter implementing `ModelProvider`. Token ceiling enforcement, HTTP/2 SSE streaming with `httpx`. |
| `TASK-014` | Task-Manifest Tooling & Validity Canary | A/A Floor | 🟡 Medium | **Normal Developer** | Manifest pinning and bidirectional canary validation (gold patch passes, empty patch fails). Schema validation & exclusion logging. |
| `TASK-017` | Git Workspace & Worktree Adapter | M1a (Sprint 3) | 🟡 Medium | **Normal Developer** | `Workspace` + `WorktreeManager` over `git` CLI via `asyncio.subprocess`. All paths repo-relative strings; worktree lifecycle management. |
| `TASK-021` | Worktree & AST Performance Timers | M1a (Sprint 3) | 🟡 Medium | **Normal Developer** | Instrument worktree creation and AST parse latencies. Benchmarking script publishing hardware/method metadata for F1 decision. |
| `TASK-026` | SQLite Trajectory Store Adapter | M1a (Sprint 4) | 🟡 Medium | **Normal Developer** | Durable append-only event log in SQLite WAL mode. Bus consumer pattern with no ORM. Replay byte-for-byte deterministic. |
| `TASK-025` | Architect/Editor Dual-Model Seam | M2 (Sprint 6) | 🟡 Medium | **Normal Developer** | Decoupling architectural planning from code editing. Modular multi-model delegation (ships disabled pending ablation). |
| `TASK-032` | Per-Node Digest Memoization | M2 (Sprint 6) | 🟡 Medium | **Normal Developer** | Subtree re-execution skipping keyed by `sha256(node_kind, impl_version, payload)`. Proper DAG invalidation traversal. |
| `TASK-003` | Kernel Dispatch & Policy Engine | M0 (Sprint 2) | 🔴 Hard | **Senior Developer** | TCB authorization choke point (`kernel/dispatch.py`). Capability grant verification at point-of-effect. Strict bypass prevention architecture. |
| `TASK-018` | Built-in Tool Registry & Execution Container | M1a (Sprint 3) | 🔴 Hard | **Senior Developer** | Frozen tool catalog with `untrusted-external` provenance labelling at construction. Podman container execution separated from judge. |
| `TASK-019` | TCB Evaluator Implementation | M1a (Sprint 3) | 🔴 Hard | **Senior Developer** | TCB judge executing task test commands in Podman containers. Verification of test command SHA256 hashes; mapping exit codes to `GateReport`. |
| `TASK-020` | Declarative Topology Executor | M1a (Sprint 3) | 🔴 Hard | **Senior Developer** | Core engine parsing and executing schema-validated workflow graphs. Static check validation (5 checks) with typed error enforcement. |
| `TASK-022` | Headless Engine API & Event Bus | M1a (Sprint 3) | 🔴 Hard | **Senior Developer** | Central `engine.py` exposing append-only event stream via `anyio` bus. Bounded queue management, strict backpressure handling. |
| `TASK-023` | Bounded Repair Loop Node | M1a+ (Sprint 4) | 🔴 Hard | **Senior Developer** | Statically unrolled repair loop (`evaluate → repair → apply → evaluate`). Per-iteration budget carving; `NONE` tri-state failure routing bypass. |
| `TASK-024` | L5 Dialogue Context Compactor | M2 (Sprint 6) | 🔴 Hard | **Senior Developer** | Deterministic structural compaction of context dialogue (L5 only). Type system enforced protection preventing mutation of layers L1–L4. |
| `TASK-031` | 5-Layer Prompt Prefix & Cache Architecture | M2 (Sprint 6) | 🔴 Hard | **Senior Developer** | Context assembler with 5 fixed layers (L1–L5) and $\le 4$ cache breakpoints. Byte-identical prefix stability floor enforcement for prompt caching. |
| `TASK-034` | ResourceGovernor Ledger | M1a/M3 | 🔴 Hard | **Senior Developer** | Atomic budget ledger (micro-USD, tokens, wall-clock ms). Refuses effects without a live lease. Hierarchical child lease refunds to parent reservations. |
| `TASK-030a` | Shell AST Classifier | M2/M3 | 🔴 Hard | **Senior Developer** | Parsing shell command invocation to Tree-Sitter ASTs. Capability-widening classification (`Reject`/`AskRuleMatch`/`AskFailClosed`). |
| `TASK-012` | Statistical Engine & A/A Variance Floor | A/A Floor | 🔥 Very Hard | **Senior Specialist** *(Statistics)* | Exact McNemar test, Holm–Bonferroni FWER correction ($\alpha = 0.05$), Monte-Carlo power simulation for $N$ derivation, seeded bootstrap. |
| `TASK-016` | Evaluation Container & B3 Canary | B3 (Sprint 5) | 🔥 Very Hard | **Senior Specialist** *(Container Security)* | Rootless Podman isolation (`--network none`, `--cap-drop all`, digest-only images). Fixes `.pth` host leakage. Automated broken-candidate canary. |
| `TASK-030b` | TaintGate Provenance & Red-Team Gate | M2/M3 | 🔥 Very Hard | **Senior Specialist** *(AppSec / Injection)* | Multi-span taint propagation model (`UNTRUSTED_EXTERNAL`). Security predicate in policy engine enforcing zero grant leakage on injection corpus. |
| `TASK-015` | Comparative-Lift Rig (`HarnessUnderTest`) | Post-Floor | 🔥 Very Hard | **Senior Specialist** *(ML Eval Rigs)* | Paired benchmark execution runner comparing bare model, AETHER, and OpenHands across identical task instances, models, and evaluators. |
| `TASK-033` | Best-of-N Cache Sequencing | M3 (Sprint 8) | 🔥 Very Hard | **Senior Specialist** *(LLM Systems)* | Sequential warming of shared prompt prefixes on candidate 1 before releasing candidates 2..N to prevent cold cache fan-out penalties. |
| `TASK-035` | Conditional Branching & Best-of-N Fan-Out | M3 (Sprint 8) | 🔥 Very Hard | **Senior Specialist** *(Distributed DAG)* | Multi-candidate parallel DAG fan-out execution. Conditional edge routing (`on_pass`, `on_fail`, `on_instrument_error`) with mandatory join barriers. |

---

### Team Allocation Summary

* 🟢 **Junior Developer (3 Tasks)**: High-velocity startup tasks (TCB path constants, pure domain models, tri-state gate report).
* 🟡 **Normal Developer (12 Tasks)**: Port interfaces, mock adapters, git worktrees, local model adapters, SQLite event logs, digest memoization.
* 🔴 **Senior Developer (10 Tasks)**: Kernel dispatch, evaluator, topology executor, event bus, bounded repair loop, context compactor, resource governor ledger.
* 🔥 **Senior Specialist (6 Tasks)**:
  1. **Statistical Expert**: Statistical engine & A/A floor ($N$ power derivation, McNemar).
  2. **Container Security Expert**: Podman container sandbox & `.pth` leak prevention.
  3. **AppSec / Injection Expert**: TaintGate provenance tracking & red-team prompt injection tests.
  4. **ML Evaluation Expert**: Comparative paired benchmark runner.
  5. **LLM Systems Expert**: Best-of-N prompt cache sequencing.
  6. **Distributed DAG Expert**: Best-of-N fan-out DAG execution engine.