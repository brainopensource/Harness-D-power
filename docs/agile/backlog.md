---
status: rationale
updated: 2026-08-07
---

# AETHER v3.0.0 — Product & Technical Backlog

This backlog catalogs all Epics and User Stories for building AETHER v3.0.0. All tasks map directly to normative rules in [`docs/spec.md`](../spec.md), [`docs/measurement.md`](../measurement.md), or [`docs/decisions/`](../decisions/README.md).

**Every exit gate in [`milestones.md`](./milestones.md) has a task here that funds it.** The reverse check is the one that matters: a gate with no funded task is a tripwire guaranteed to fire, and a tripwire that always fires gets ignored — which is [ADR-0009](../decisions/0009-gates-are-the-schedule.md)'s own reversal condition.

---

## Epic 0: Enforcement Migration (Milestone M0 — **blocking**)

### TASK-000: Migrate TCB Path Constants to `src/aether/` — ✅ DONE (Sprint 1)
* **Description**: Move `.importlinter` `tcb-isolation` targets and CI `TCB_PATHS` from `src/sagiha/…` to `src/aether/…`, **in the same change as the first `src/aether/` file**.
* **Target Files**: `.importlinter`, `.github/workflows/ci.yml`, `tests/unit/test_path_constant_drift.py`
* **Normative Specs**: [ADR-0006 "The trap this ADR must not fall into"](../decisions/0006-tcb-boundary-and-meta-loop-authority.md), [`milestones.md` M0 Gate 0](./milestones.md#milestone-m0--pure-domain--wire-protocols)
* **Exit Criteria**: The drift test **demonstrably fails** when the constants select only `src/sagiha/`. No contract selects zero modules.
* **Priority**: **First PR of Sprint-01.** Until it lands, ADR-0006 is enforced by nothing while CI reports green.

---

## Epic 1: TCB Kernel & Core Domain (Milestone M0)

### TASK-001: Pure Domain Data Models — ✅ DONE (Sprint 1)
* **Description**: Implement immutable Pydantic domain models in `src/aether/domain/`. Zero I/O dependencies.
* **Target Files**: `src/aether/domain/*.py`
* **Normative Specs**: [`spec.md` §2 (I1)](../spec.md#2-invariants), [AGENTS.md Guideline 2](../../AGENTS.md)
* **Exit Criteria**: `import-linter` contract `domain-is-pure` passes green. All datetimes tz-aware; budget arithmetic is integer-only by type.

### TASK-002: Wire-Serializable Port Protocols — ✅ DONE (Sprint 1)
* **Description**: Define typed `Protocol` boundaries for the 8 core port areas (9 protocols) in `src/aether/ports/`.
* **Target Files**: `src/aether/ports/*.py`
* **Normative Specs**: [`spec.md` §4](../spec.md#4-ports), [ADR-0005 rev. 2](../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I2, I3)](../spec.md#2-invariants)
* **Exit Criteria**: Each protocol lands with a mock adapter, a conformance test, **and its first real adapter named**. Reflection meta-test passes: all `async`, no `Path`/handle/callable/generator/live object, no `dict[str, Any]`, **no `Grant` in any public signature**.

### TASK-003: Kernel Dispatch & Policy Engine Choke Point — ✅ DONE (Sprint 1)
* **Description**: Build the TCB authorization and dispatch choke point.
* **Target Files**: `src/aether/kernel/dispatch.py`, `src/aether/kernel/policy.py`
* **Normative Specs**: [`spec.md` §5](../spec.md#5-execution), [`spec.md` §2 (I5, I8)](../spec.md#2-invariants), [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Exit Criteria**: Grants verified immediately prior to effect execution. Architecture test proves no bypass path. **The concrete `PolicyEngine` lives in `kernel/`, never `adapters/`** ([`spec.md` §4](../spec.md#4-ports) residency rule).

### TASK-004: WorkflowStep Node & Socket Types — ✅ DONE (Sprint 1)
* **Description**: Implement typed `WorkflowStep[In, Out]` and socket types.
* **Target Files**: `src/aether/workflow/step.py`
* **Normative Specs**: [ADR-0013 (M0)](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Pyright strict passes with zero errors. Steps receive **no adapter handles** — effects reach a dispatch facade injected by the executor.

### TASK-005: Conformance Meta-Suite Harness — ✅ DONE (Sprint 1)
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

## Sprint 3.5 — Phase 0 Lock (code complete)

Correctness + decoupling: six dead defects fixed, node registry keyed by kind, edit-format seam, retrieval multi-file, system layer seed, second topology.

### TASK-036: SWE-bench Per-Instance Image Resolution
* **Description**: Pull evaluation images, resolve to digests, run validity canary on 15-task sample.
* **Target Files**: `scripts/build_floor_manifest.py`, `benchmarks/manifests/`
* **Normative Specs**: [`measurement.md` §2 (B3)](../measurement.md#2-instrument-blockers)
* **Status**: Deferred to post-floor.

### TASK-037: EditFormat Seam — Unified Diff & Whole-File Codeblock ✅ DONE
* **Description**: Protocol + two implementations swappable per node via YAML `params.edit_format`.
* **Target Files**: `src/aether/workflow/edit_format.py`, `src/aether/workflow/nodes/apply.py`, `workflows/linear_repair_wholefile_v1.yaml`
* **Normative Specs**: [`spec.md` §7](../spec.md#7-measurement)
* **Exit Criteria**: One conformance suite, both pass. Unified diff (default + --3way fallback); whole-file (regex + AST validation).

### TASK-038: Node Registry Keyed by Kind ✅ DONE
* **Description**: `engine.run()` takes registry mapping; executor resolves `steps[node["kind"]]` from `params`.
* **Target Files**: `src/aether/engine.py`, `src/aether/workflow/executor.py`
* **Normative Specs**: [ADR-0014](../decisions/0014-workflow-topology-is-data.md)
* **Exit Criteria**: Two generate nodes legal in one topology. Implementations swappable from data.

---

## Epic 2: Measurement Rig & Instrument Blockers

### TASK-010: Manifest-Driven Upstream Repository Cache (Blocker B1) — ✅ DONE (Sprint 1)
* **Description**: Standalone utility cloning and resolving base commits for the repositories **named by the pinned manifest**.
* **Target Files**: `src/aether/measurement/repo_cache.py`, `scripts/resolve_swebench_bases.py`
* **Normative Specs**: [`measurement.md` §2 (B1)](../measurement.md#2-instrument-blockers), [ADR-0002](../decisions/0002-no-number-before-the-floor.md)
* **Exit Criteria**: Repo set derived from the manifest, never hard-coded. 100% of base commits resolve for the floor manifest. Cache is content-addressed and **offline-replayable**.

### TASK-011: Local Model Provider Adapter (Blocker B2b) — ✅ DONE (Sprint 2)
* **Description**: `ModelProvider` adapter for the local OpenAI-compatible endpoint. Named as the first **real** adapter satisfying TASK-002's mock clause for this port.
* **Target Files**: `src/aether/adapters/model_provider/openai_compatible.py`
* **Normative Specs**: [`measurement.md` §2 (B2)](../measurement.md#2-instrument-blockers), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md)
* **Exit Criteria**: Passes the `ModelProvider` conformance suite. Enforces the request's token ceilings — conservation is kernel policy, not adapter courtesy.

### TASK-012: Statistical Engine & A/A Variance Floor — ✅ DONE (Sprint 3)
* **Description**: Port `e0/statistics.py` verbatim (exact McNemar, Holm–Bonferroni, seeded bootstrap), then add the rev. 2 layer: derived-N power simulation and the family gatekeeper.
* **Target Files**: `src/aether/measurement/statistics.py`, `src/aether/measurement/families/`
* **Normative Specs**: [`measurement.md` §3](../measurement.md#3-the-aa-variance-floor), [ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md), [`spec.md` §9](../spec.md#9-standing-rules) (predecessor-code clause — provenance in the module docstring)
* **Exit Criteria**: Pinned JSON fixtures pass. **The module refuses to compute corrected p-values for an undeclared family.** The power simulation is seeded and re-runnable from a family file alone.

### TASK-013: Typed Tri-State `GateReport` (Blocker B4) — ✅ DONE (Sprint 1)
* **Description**: The typed distinction between *test failed* and *instrument failed*. Pulled forward from M2 — it is a pure domain type and a **precondition of the A/A floor**.
* **Target Files**: `src/aether/domain/gate.py`, `src/aether/measurement/evaluator.py`
* **Normative Specs**: [`measurement.md` §2 (B4)](../measurement.md#2-instrument-blockers), [`milestones.md` B4](./milestones.md#blocker-b4--typed-instrument-error-handling)
* **Exit Criteria**: Exit-127, uncollectable tests and test-command-hash mismatch all yield `NONE`, never `FAILED`. `NONE` outcomes are **excluded from the resolve-rate denominator** and reported separately. Negative test required.

### TASK-014: Task-Manifest Tooling & Bidirectional Validity Canary — ✅ DONE (Sprint 3)
* **Description**: Build, pin and validate task manifests; run the per-task canary; publish exclusions.
* **Target Files**: `src/aether/measurement/manifest.py`, `src/aether/measurement/schemas/manifest_schema.yaml`
* **Normative Specs**: [`measurement.md` §4.2–4.3](../measurement.md#42-splits-and-why-they-are-pinned), [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published), [`schemas_and_contracts.md` §2](../development/schemas_and_contracts.md)
* **Exit Criteria**: A task enters a manifest only if the **gold patch passes and the empty patch fails** on our instrument. **Exclusions are published with a reason** — silent exclusion is the overfitting vector. Manifest and split assignment are TCB; a change is a new hash.

### TASK-016: Evaluation Container & B3 Canary (Blocker B3) — ✅ DONE (Sprint 3)
* **Description**: Rootless Podman evaluation container — the isolation that makes a candidate diff visible to the gate scoring it.
* **Target Files**: `src/aether/adapters/sandbox/podman.py`, `containers/eval/`
* **Normative Specs**: [`measurement.md` §2 (B3)](../measurement.md#2-instrument-blockers), [`tech_stack_and_infra.md` §3](../development/tech_stack_and_infra.md), [ADR-0008](../decisions/0008-shell-ast-classifies.md)
* **Exit Criteria**: `--network none`, `--cap-drop all`, `--security-opt no-new-privileges`, read-only root, image **created from digest, never tag**. Two mounts only: the task worktree (RW) and pinned image layers (RO) — **no `.pth` leakage by construction**. **Canary: a deliberately broken candidate must fail evaluation**, and the canary runs in the A/A floor environment before the floor run.
* **Why it matters**: the `.pth` leak is the one instrument defect that *produced numbers*.

### TASK-019: Evaluator Implementation (TCB) — ✅ DONE (Sprint 2; containerized in Sprint 3 via TASK-016)
* **Description**: The judge. Runs the task's pinned test command in the evaluation container and returns a tri-state `GateReport`.
* **Target Files**: `src/aether/measurement/evaluator.py`
* **Normative Specs**: [`spec.md` §4](../spec.md#4-ports) (TCB port residency), [`spec.md` §2 (I7)](../spec.md#2-invariants), [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Exit Criteria**: **Lives in `measurement/`, never `adapters/`** — the residency rule is what makes `tcb-isolation` select it. Verifies the test command against the manifest's `test_command_hash` before running; a mismatch is `NONE`, not a result. `import-linter` proves it cannot import `agency/` or `workflow/`.
* **Named as**: the first real adapter for the `Evaluator` port under [ADR-0005](../decisions/0005-eight-ports-adapter-first.md) rev. 2.

### TASK-015: Comparative-Lift Rig (`HarnessUnderTest`) — ✅ DONE (Sprint 3, seam + bare-model arm; OpenHands arm still out of scope)
* **Description**: A runner seam producing paired outcomes for (harness, model, manifest) through **our** evaluator. Arms: bare-model baseline, AETHER, OpenHands.
* **Target Files**: `src/aether/measurement/runner.py`
* **Normative Specs**: [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md) (measurement is a tool, not a port)
* **Exit Criteria**: Same model, same manifest, same evaluator across arms. **Without this the mission statement is unsubstantiable** — [`spec.md` §9](../spec.md#9-standing-rules) forbids citing competitors' published numbers as evidence. Scheduled after the floor, before any public claim.

---

## Epic 3: Walking Skeleton & Engine (Milestone M1a)

### TASK-020: Declarative Topology Executor — ✅ DONE (Sprint 2)
* **Description**: Executor running a schema-validated linear graph `retrieve → generate → apply → evaluate`, plus the TCB topology validator.
* **Target Files**: `src/aether/workflow/executor.py`, `src/aether/workflow/validator.py`, `src/aether/workflow/nodes/*.py`, `workflows/linear_v1.yaml`
* **Normative Specs**: [ADR-0013 (M1a)](../decisions/0013-workflow-dag-phased.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md), [`schemas_and_contracts.md` §1](../development/schemas_and_contracts.md)
* **Exit Criteria**: The executor **refuses** any topology failing a static check, with a typed error naming the failed check. Each of the five checks has a malformed fixture proving it can fail. **No `--force` flag exists.**

### TASK-021: Performance Timers (Worktree & AST Parse) — ✅ DONE (Sprint 2)
* **Description**: Instrument worktree creation and AST parse-and-validate.
* **Target Files**: `src/aether/measurement/timers.py`
* **Normative Specs**: [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md)
* **Exit Criteria**: Latencies published to [`docs/rationale/benchmarks/performance_timers.md`](../rationale/benchmarks/README.md) **with hardware and method recorded**. These two numbers decide the F1 fork. A run showing nothing is recorded as showing nothing.

### TASK-022: Headless Engine API & Event Bus — ✅ DONE (Sprint 2)
* **Description**: `engine.py` headless API emitting an append-only typed event stream generated from `domain/events.py`.
* **Target Files**: `src/aether/engine.py`, `src/aether/kernel/bus.py`, `src/aether/domain/events.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients), [ADR-0013](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Event-catalog drift check passes. **Events never drive node scheduling** — a sensor that must cause work enqueues a task through the engine API. Display consumers are drop-oldest; the trajectory store and harvester are never dropped.

### TASK-017: Git Workspace & Worktree Adapter — ✅ DONE (Sprint 2)
* **Description**: `Workspace` + `WorktreeManager` over the `git` CLI via `asyncio.subprocess`.
* **Target Files**: `src/aether/adapters/workspace/git_cli.py`
* **Normative Specs**: [ADR-0005](../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I3)](../spec.md#2-invariants), [`tech_stack_and_infra.md` §3.2](../development/tech_stack_and_infra.md)
* **Exit Criteria**: Passes both conformance suites. **All paths are repo-relative strings — no `Path` crosses the port** (I3). One worktree per candidate under a run-scoped root. This is where the worktree-creation timer (`TASK-021`) lives.
* **Named as**: the first real adapter for the `Workspace`/`WorktreeManager` boundary.

### TASK-018: Built-in Tool Registry & Tool-Execution Container — ✅ DONE (Sprint 2, uncontained; **its own** container image remains open — Sprint 3 containerized the evaluator, not the tool registry)
* **Description**: `ToolRegistry` adapter with the built-in tool set, executing in a **separate** container from the evaluator.
* **Target Files**: `src/aether/adapters/tools/builtin.py`, `containers/tools/`
* **Normative Specs**: [ADR-0005](../decisions/0005-eight-ports-adapter-first.md), [ADR-0015](../decisions/0015-taintgate-provenance-model.md), [ADR-0016](../decisions/0016-mcp-integration-trust-model.md)
* **Exit Criteria**: Catalog **frozen at composition** (I6). **Tool outputs are labelled `untrusted-external` at construction**, not at point of use. Separate image and separate lease class from the evaluator, so a runaway tool loop cannot starve the judge.
* **Named as**: the first real adapter for `ToolRegistry`. MCP ([ADR-0016](../decisions/0016-mcp-integration-trust-model.md)) is a second adapter of the same port, later.

### TASK-026: SQLite Trajectory Store Adapter — ✅ DONE (Sprint 2)
* **Description**: Durable append-only event log; a bus consumer like any other.
* **Target Files**: `src/aether/adapters/trajectory_store/sqlite.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients), [ADR-0005](../decisions/0005-eight-ports-adapter-first.md)
* **Exit Criteria**: Passes conformance. WAL mode, no ORM. **Never dropped under backpressure** — display consumers are drop-oldest, the durable log and the measurement harvester are not. Replay from it is byte-for-byte deterministic.
* **Named as**: the first real adapter for `TrajectoryStore`.

### TASK-023: Repair Node & Bounded-Iteration Construct — ✅ DONE (Sprint 3)
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

### TASK-034: `ResourceGovernor` Reserve / Commit / Release — ✅ DONE (Sprint 2)
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

Complexity is scored **0–5** (six levels), weighing knowledge domain required, number of interacting sub-tasks/constraints, and blast radius if the task is done wrong — not raw line count. Derived from a full read of `spec.md`, `measurement.md`, `milestones.md`, all 17 ADRs, and the `development/` engineering docs (protocols, schemas, tech stack).

**Sprint tags below are grounded in [`sprints/sprint-01.md`](./sprints/sprint-01.md), [`sprint-02.md`](./sprints/sprint-02.md) and [`sprint-03.md`](./sprints/sprint-03.md) — the only three sprints planned in full.** Sprint 3 is explicitly "the last sprint planned in full"; Sprint 4 onward is sized only after the A/A floor (Sprint 3, Task 5) reports per-task wall-clock ([`roadmap.md`](./roadmap.md), sprint-03.md). Tasks below that milestone are tagged with their milestone only, not a fabricated sprint number.

| Score | Level | What it takes |
| :---: | :--- | :--- |
| 0 | Trivial | Mechanical edit, no domain knowledge, single concern |
| 1 | Very Easy | One clear concept, closed scope, no concurrency/security/algorithmic depth |
| 2 | Easy | Some protocol/domain modeling across several files, still low risk |
| 3 | Medium | Real integration surface (multiple ports/files) or a non-trivial algorithm; several constraints to reconcile correctly |
| 4 | Hard | Deep architectural knowledge (concurrency, security, container isolation, TCB residency); many interacting invariants; expensive to get wrong |
| 5 | Very Hard | Specialist domain (applied statistics, container/security engineering, adversarial red-teaming, cross-harness evaluation); largest blast radius; often no reference implementation to copy from |

Every row is worked by **The Developer** — there is one team, not a role hierarchy — so the second column states *why* the task lands where it does instead of *who* should do it.

### Sprint 1 — Foundations & Instrument Unblocking (done)

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-000` | TCB Path Constants Migration | M0 (Sprint 1) | **1** · Very Easy | Mechanical constant swap, no new logic | Renames path constants across `.importlinter`, CI YAML, and one drift test. No runtime behavior changes — the only risk is sequencing: ADR-0006 itself names the trap of this migration passing vacuously if it lands one commit later than the first `src/aether/` file. The exit criterion is a negative test proving the drift check *can* fail. |
| `TASK-001` | Pure Domain Data Models | M0 (Sprint 1) | **2** · Easy | Nine files, zero I/O, no branching logic | Immutable Pydantic models spanning `ids`, `task`, `taint`, `budget`, `gate`, `model_io`, `workspace`, `tools`, `events` — including a discriminated `ModelStreamEvent` union and `NewType` ids. Breadth over depth: no I/O, no concurrency. The discipline is holding I1 (zero imports) and I3 (wire-serializability — tz-aware datetimes, integer-only budgets) across every field, not algorithmic difficulty. |
| `TASK-002` | Wire-Serializable Port Protocols | M0 (Sprint 1) | **3** · Medium | 9 protocols, each with its own wire-safe payload types | Defines `ModelProvider`, `Workspace`/`WorktreeManager`, `ToolRegistry`, `Indexer`, `PolicyEngine`, `ResourceGovernor`, `TrajectoryStore`, `Evaluator` — each carrying its own frozen payload types (`ModelStreamEvent` union, `TaintSpan`-bearing messages, `EffectRequest`/`PolicyDecision`, `Lease`/`Actuals`). No single protocol is hard; holding I2/I3's rules (async-only, no `Path`/handle/callable/generator, no `dict[str, Any]`, no `Grant` in a public signature) invariant across all nine simultaneously is the real work, since TASK-005's reflection meta-test checks every one generically. |
| `TASK-005` | Conformance Meta-Suite Harness | M0 (Sprint 1) | **3** · Medium | One reflection suite that must hold for every current *and future* port | A single parametrized suite plus a reflection meta-test asserting async-only methods, no live-object payloads, no `Grant`, tz-aware datetimes — generically, over whatever ports are registered. Getting the reflection logic right once is moderate; getting it wrong reproduces the exact failure ADR-0005 exists to prevent — a port whose adapter list is empty, silently passing. |
| `TASK-006` | Mock Adapter Set & Cassettes | M0 (Sprint 1) | **3** · Medium | Mocks for 9 ports plus a byte-exact replay engine | Every port needs a mock that raises on unimplemented paths rather than faking a plausible result, plus a cassette format replaying byte-for-byte deterministically at 100 turns / <50 ms with no network and no container. The determinism bar is the harder half — it's what makes the whole ablation cadence from M2 onward practically runnable rather than aspirational. |
| `TASK-010` | Manifest-Driven Repo Cache | B1 (Sprint 1) | **2** · Easy | A cloning cache with clear inputs and outputs | Standalone utility deriving the repo set from the pinned manifest — never hard-coded — content-addressed and offline-replayable. No AETHER dependency, no security surface, no concurrency, and it single-handedly unblocks every benchmark number that has ever been attempted (B1). |
| `TASK-003` | Kernel Dispatch & Policy Engine Choke Point | M0 (Sprint 1) | **4** · Hard | The one choke point every effect in the system must pass through | Implements `authorize → verify grant → acquire lease → dispatch → release` with **re-verification at effect-time, not authorization-time** — arguments can drift between issuance and use, and a resumed run can carry a stale grant, a genuinely subtle TOCTOU-shaped correctness requirement. It must also pass an architecture test proving *no second path exists* to any adapter, and its concrete `PolicyEngine` must physically live inside `kernel/` (never `adapters/`) for the import-linter TCB contract to select it at all. The single highest-leverage module in the codebase — every other port's effects funnel through it. |
| `TASK-004` | WorkflowStep Node & Socket Types | M0 (Sprint 1) | **2** · Easy | Generics and Pyright-strict discipline, no engine yet | `WorkflowStep[In, Out]` generic node, socket types, and an `input_digest()` stub. Self-contained — ADR-0013 deliberately phases the executor out to M1a — so the bar is strict generic typing the later validator can check edges against, not architecture. |
| `TASK-013` | Typed Tri-State `GateReport` | B4 (Sprint 1) | **1** · Very Easy | One enum, one mapping rule | `GateStatus` (`PASSED`/`FAILED`/`NONE`) plus the rule sending exit-127, uncollectable tests, and test-command-hash mismatches to `NONE` instead of `FAILED`. Small code volume, but this exact mapping is what keeps instrument errors out of the A/A floor's denominator (B4). |

### Sprint 2 — Real Adapters & the Walking Skeleton (done)

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-011` | Local Model Provider Adapter | B2b (Sprint 2) | **3** · Medium | First real adapter — it sets the precedent every later provider follows | An async `httpx` `ModelProvider` streaming SSE deltas (`TextDelta`/`ToolCallDelta`/`UsageEvent`/`StopEvent`) with enforced token ceilings. Moderate streaming/protocol work, but it's also the adapter proving out the port shape and satisfying TASK-002's "named first real adapter" entry rule — everything that later calls a model goes through what this task establishes. |
| `TASK-017` | Git Workspace & Worktree Adapter | M1a (Sprint 2) | **3** · Medium | Git-over-subprocess with a strict no-`Path`-crosses-the-port rule | `Workspace` + `WorktreeManager` over the `git` CLI via `asyncio.subprocess`, every path a repo-relative string (I3), one worktree per candidate under a run-scoped root. The concrete surface (`read`/`write`/`apply_patch`/`diff`, `create`/`destroy`/`list_active`) is already specified; the real work is subprocess correctness and patch-application edge cases (rejected hunks), plus hosting the worktree-creation timer TASK-021 depends on. |
| `TASK-018` | Built-in Tool Registry & Execution Container | M1a (Sprint 2) | **4** · Hard | A catalog that must be frozen, and outputs labeled untrusted before anyone reads them | `ToolRegistry` adapter executing in a container **separate** from the evaluator (own image, own lease class, so a runaway tool loop can't starve the judge). Every tool output must be labeled `untrusted-external` **at construction**, not at point of use — a timing requirement that interacts directly with the TaintGate model (ADR-0015). Also the first adapter that has to honor I6 (catalog frozen at composition, no runtime registration). |
| `TASK-019` | TCB Evaluator Implementation | M1a (Sprint 2) | **4** · Hard | The judge itself — must be provably unreachable from the code it grades | Runs the manifest's pinned test command inside the evaluation container and returns a typed tri-state `GateReport`, verifying the test-command hash before running (a drift is `NONE`, never a result). The harder constraint is architectural: it must physically live in `measurement/`, never `adapters/`, so `import-linter`'s `tcb-isolation` contract can prove `agency/`/`workflow/` cannot import it (I7 — the agent that writes code cannot modify the tests grading it). |
| `TASK-020` | Declarative Topology Executor | M1a (Sprint 2) | **4** · Hard | Five static graph checks with no escape hatch | A JSON-Schema (Draft 2020-12) structural pass plus five hand-written checks — socket-type compatibility across every edge, evaluator-termination (no path may route around the judge), bounded iteration, declared fan-out, and per-node budget annotation — with **no `--force` flag** and a typed error naming the failed check. `evaluator_termination` is a real graph-reachability property, not a schema field; ADR-0014 calls this component "TCB-adjacent" precisely because a bug here lets a topology bypass I7. |
| `TASK-022` | Headless Engine API & Event Bus | M1a (Sprint 2) | **4** · Hard | The one stream every client in the system reads from | The headless `engine.py` API and append-only typed event bus every surface (TUI, CLI, CI, a future GUI) consumes with no privileged access. Requires correct backpressure under concurrency — drop-oldest for display consumers, **never** dropped for the trajectory store or measurement harvester — plus an event catalog generated from `domain/events.py` with a drift check. Nearly everything else in the system is either a producer or consumer of what this task builds. |
| `TASK-034` | ResourceGovernor Ledger | M1a (Sprint 2) / M3 | **4** · Hard | A ledger that makes stale budget accounting structurally impossible, not just discouraged | Implements `reserve → commit → release` as an atomic, integer-only ledger the dispatcher refuses to bypass — no effect executes without a live lease, which is what makes after-the-fact accounting (the predecessor's actual Best-of-N failure) unrepresentable rather than merely policed. The subtlety is in the edges: an overrun records a typed event *and* debits reality rather than silently correcting, and a child lease's release must refund its **parent** reservation, not the global pool — what makes N-way fan-out cancellation correct. Lands in Sprint 2 for the M1a reserve/commit/release gate; child-lease fan-out semantics are exercised again at M3. |
| `TASK-021` | Worktree & AST Performance Timers | M1a (Sprint 2) | **1** · Very Easy | Two stopwatches and an honest write-up | Times worktree creation and AST parse-and-validate, publishes with hardware and method recorded. Simple instrumentation with outsized downstream leverage: these two numbers directly decide ADR-0001's Python-vs-Rust (F1) fork. |
| `TASK-026` | SQLite Trajectory Store Adapter | M1a (Sprint 2) | **2** · Easy | An append-only SQLite log, no ORM, no cleverness | Durable event log in WAL mode, behaving as one more bus consumer (`append`/`replay`/`latest_seq`). Well-specified and contained; the only real constraint — never dropped under backpressure, alongside the measurement harvester — is a policy decision enforced by TASK-022, not extra code here. |

### Sprint 3 — The Repair Edge and the Floor (code + instruments done; the floor run itself is deferred)

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-016` | Evaluation Container & B3 Canary | B3 (Sprint 3) | **5** · Very Hard | Container isolation where the one bug that shipped before was invisible | Rootless Podman with `--network none`, `--cap-drop all`, `--security-opt no-new-privileges`, read-only root, exactly two mounts (RW worktree, RO pinned image layers by digest — never tag), plus a canary proving a deliberately broken candidate fails, run **inside the A/A floor environment before the floor itself**. This is the exact defect class (B3, the `.pth` leak) that silently produced fabricated numbers last time. It demands real namespace/mount/capability fluency, and a subtle mistake here invalidates a whole benchmark's results, not a bug report. |
| `TASK-014` | Task-Manifest Tooling & Validity Canary | A/A Floor (Sprint 3) | **3** · Medium | Bidirectional validation against a real, sometimes-broken task set | Builds and pins manifests, then runs a per-task canary requiring the gold patch to pass *and* the empty patch to fail on our own instrument, publishing every exclusion with a reason. Not algorithmically hard, but operationally heavy — roughly 30% of public Pro tasks were estimated broken in a mid-2026 audit, so this is triage at scale, not clean-room logic. |
| `TASK-023` | Bounded Repair Loop Node | M1a+ (Sprint 3) | **4** · Hard | `vision.md`'s single largest lever on score, and it must stay a bounded loop, never an infinite one | Statically unrolls `evaluate →(fail, k)→ repair → apply → evaluate` to `max_iterations` (1–16) so the DAG stays acyclic by construction. Three constraints carry the real difficulty: the validator must reject an unbounded or over-bound block, each iteration reserves its **own** budget through the governor triple, and a `GateReport` of `NONE` must never route into repair — repairing against a broken instrument would teach the loop to fix the harness's own bugs. Named in `vision.md` as the single largest lever on score, so correctness here has outsized leverage on every later benchmark number. |
| `TASK-012` | Statistical Engine & A/A Variance Floor | A/A Floor (Sprint 3) | **5** · Very Hard | The instrument that decides whether every future number in this project is allowed to exist | Ports the predecessor's 259-LOC `e0/statistics.py` verbatim (exact McNemar, Holm–Bonferroni, seeded bootstrap — the one asset from the prior codebase that verified line-by-line), then adds real new complexity: a seeded Monte-Carlo power simulation deriving N per gate family from a pre-registered discordance assumption, target power ≥0.80, and the Holm-adjusted α at that hypothesis's rank — plus a gatekeeper that **refuses to compute corrected p-values for an undeclared family**. Demands genuine applied-statistics fluency (why a fixed N=50 silently discards 9 of 10 true improvements is not obvious without running the simulation), and its correctness gates every admission decision the project will ever make. |
| `TASK-015` | Comparative-Lift Rig (`HarnessUnderTest`) | Sprint 3 (bare-model arm only) / Post-Floor (full) | **5** · Very Hard | Apples-to-apples comparison across harnesses that were never built to be compared | A `HarnessUnderTest` seam producing paired outcomes for bare-model, AETHER, and OpenHands, all routed through **our own** evaluator, same model, same manifest. Sprint 3 lands only the seam plus the bare-model arm; the OpenHands arm is explicitly deferred to after the floor. The hard part is integration, not volume: wrapping a third-party OSS harness uniformly enough to be comparable, without breaking the paired design McNemar assumes. Without this task the mission statement is literally unsubstantiable — `spec.md` §9 forbids citing a competitor's own published numbers as evidence. |

### M2 / M3 — not yet sprint-planned

Sprint 3 is the last sprint written in full; these land once M2-abl is sized off the floor's per-task wall-clock (`roadmap.md`). `TASK-032` is explicitly named as "the first task of the next sprint" in `sprint-03.md`, so it's first in line below.

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-032` | Per-Node Digest Memoization | M2, Gate 1 (next sprint) | **3** · Medium | Cache invalidation, the classic hard problem, scoped to a DAG | Keys node execution on `sha256(node_kind, impl_version, canonical_payload)` and must invalidate **exactly** the descendants of a changed node — no more, no less. A correctness-sensitive DAG-traversal problem: over-eager invalidation defeats the ablation-speed purpose of the whole task, under-eager invalidation silently reuses stale results inside a benchmark run. |
| `TASK-031` | 5-Layer Prompt Prefix & Cache Architecture | M2, Gates 3 & 6 | **4** · Hard | Five layers that must be byte-stable, provider quirks and all | Context assembler enforcing L1–L4 append-only-within-a-run and ≤4 `cache_control` breakpoints, with the CI-gated metric being **harness-side** byte-identical-prefix stability over a fixed replay — deliberately not a provider-reported hit rate, since provider cache semantics diverge (explicit Anthropic `cache_control` blocks vs. implicit OpenAI-compatible prefix caching) and the B2 local endpoint may expose none at all. The five-layer concept is simple; getting layer-immutability and the replay-based measurement both right across provider-specific emission logic is where the difficulty sits. |
| `TASK-025` | Architect/Editor Dual-Model Seam | M2, Gate 4 | **3** · Medium | A config-gated seam that ships off by policy, not because it's unfinished | Decouples `architect.py` (planning, no write tools) from `editor.py` (surgical edits) behind a config switch defaulting to single-model, riding the `RoutingModelProvider` composite already established by TASK-011. ADR-0007 is explicit that "the seam costs little to build" — the discipline is architectural cleanliness of the plan/edit boundary and honoring the ships-disabled default; if its ablation doesn't clear the floor, the code is deleted outright rather than left dormant. |
| `TASK-024` | L5 Dialogue Context Compactor | M2, Gate 5 | **3** · Medium | Compaction structurally forbidden from touching four of the five layers | Deterministic structural compaction (drop superseded file snapshots, collapse resolved tool exchanges) scoped to L5 only — the assembler exposes no API to touch L1–L4, so that guarantee is a type-level property this task doesn't have to enforce itself. The remaining work is real but bounded: get a long-task fixture to complete inside the context window via compaction alone, with no model-generated summarization (a separate, later-ablated mechanism). |
| `TASK-030a` | Shell AST Classifier | M2/M3 (CI-gated, not milestone-gated) | **4** · Hard | A classifier that must never be mistaken for a security boundary | Parses shell commands to a `tree-sitter-bash` AST and drives the `Reject \| AskRuleMatch \| AskFailClosed` taxonomy plus a `widens_capability` flag, with auto-denial bounded at 3 consecutive / 20 total before the run halts. The classification surface is genuinely large (command substitution, variable indirection, interpreters invoked on attacker-controlled input all defeat static analysis) — but the harder discipline is documentary: no security claim may ever attach to this parser, because the sandbox — not this classifier — is the actual perimeter (ADR-0008). |
| `TASK-030b` | TaintGate Provenance & Red-Team Gate | M2/M3 (CI-gated, not milestone-gated) | **5** · Very Hard | The mechanism itself is five lines; the corpus proving it holds is the whole job | Deterministic propagation (`any untrusted span consumed ⇒ untrusted-derived output`) is genuinely simple code. What makes this Very Hard is the enforcing predicate in the TCB `PolicyEngine` — a capability-widening request fails closed when any justifying span is untrusted or untrusted-derived — validated against a **pinned adversarial injection corpus** whose CI gate is *zero capability grants*, with a required negative test proving a deliberately permissive predicate makes the corpus produce a grant. Applied-security work against an open-ended adversarial input space; deliberately split from TASK-030a because ADR-0015 explicitly calls out that conflating the two means "neither gets designed." |
| `TASK-035` | Conditional Branching & Best-of-N Fan-Out | M3, Gate 1 | **4** · Hard | Parallel candidates as real graph structure, with a lease tree to match | Adds conditional edges (`on_pass`/`on_fail`/`on_instrument_error`, the last routing only to a terminal flag node) and declared Best-of-N fan-out, where every fan-out site needs a declared join (unjoined fan-out leaks worktrees and leases) and N candidates carve N child leases from one parent reservation. Concurrency-correctness under `asyncio` fan-out plus a hierarchical lease/join model is real distributed-systems-shaped thinking, even single-process. |
| `TASK-033` | Best-of-N Cache Sequencing | M3, Gate 3 | **3** · Medium | A one-request barrier, built on infrastructure two other tasks already provide | Warms the shared prefix on candidate 1 and confirms it before releasing candidates 2..N, expressed in the schema as a `cache_sequencing` value the validator requires on every fan-out site. A coordination barrier over async fan-out (TASK-035) and the cache architecture (TASK-031) — real, but narrower than it sounds once those two exist; the fiddly part is reliably detecting "prefix confirmed warm" across providers with inconsistent cache-reporting semantics. |

---

### Complexity Distribution

* **Very Easy — 1 (3 tasks)**: `TASK-000`, `TASK-013`, `TASK-021` — mechanical or single-concept work with no concurrency, security, or algorithmic surface.
* **Easy — 2 (4 tasks)**: `TASK-001`, `TASK-004`, `TASK-010`, `TASK-026` — contained, well-specified I/O or data modeling with low risk.
* **Medium — 3 (10 tasks)**: `TASK-002`, `TASK-005`, `TASK-006`, `TASK-011`, `TASK-014`, `TASK-017`, `TASK-024`, `TASK-025`, `TASK-032`, `TASK-033` — real integration surface or a non-trivial algorithm, several constraints to reconcile.
* **Hard — 4 (10 tasks)**: `TASK-003`, `TASK-018`, `TASK-019`, `TASK-020`, `TASK-022`, `TASK-023`, `TASK-030a`, `TASK-031`, `TASK-034`, `TASK-035` — TCB-critical or concurrency/security-sensitive, many interacting invariants.
* **Very Hard — 5 (4 tasks)**: `TASK-012`, `TASK-015`, `TASK-016`, `TASK-030b` — specialist domain knowledge (applied statistics, container security, cross-harness evaluation, adversarial red-teaming), largest blast radius if wrong, little or no reference implementation to draw on.