---
status: rationale
updated: 2026-08-07
---

# AETHER v3.0.0 — Product & Technical Backlog

This backlog catalogs all Epics and User Stories for building AETHER v3.0.0. All tasks map directly to normative rules in [`docs/spec.md`](../spec.md), [`docs/measurement.md`](../measurement.md), or [`docs/decisions/`](../decisions/README.md).

**Every exit gate in [`milestones.md`](./milestones.md) has a task here that funds it.** The reverse check is the one that matters: a gate with no funded task is a tripwire guaranteed to fire, and a tripwire that always fires gets ignored — which is [ADR-0009](../decisions/0009-gates-are-the-schedule.md)'s own reversal condition.

---

## Scheduling ledger

**A task is either *scheduled* or it is in the pool. There is no third state, and this table is the only place that decides which.**

The epics below group tasks by *subject*; they do not schedule anything. A task is **scheduled** only when a sprint file in [`sprints/`](./sprints/README.md) names it. Everything else carries a **milestone tag only** — which fixes its *position* in [`roadmap.md`](./roadmap.md)'s dependency DAG without committing a date. That distinction is [ADR-0009](../decisions/0009-gates-are-the-schedule.md)'s: an unmeasured duration used as a schedule commitment is the thing it forbids, and M2-abl's wall-clock is an output of Sprint 4's floor.

### Scheduled — has a sprint file

| Sprint | State | Tasks |
| :--- | :--- | :--- |
| [**01**](./sprints/sprint-01.md) | ✅ done | `000` `001` `002` `003` `004` `005` `010` `013` |
| [**02**](./sprints/sprint-02.md) | ✅ done | `011` `017` `018`\* `019` `020` `021` `022` `026` `034` |
| [**03**](./sprints/sprint-03.md) | ✅ done *(floor deferred to 04)* | `012` `014` `015`\* `016` `023` |
| **03.5** *(no plan file — retro-recorded)* | ✅ done | `037` `038` `039` `040` `041` |
| [**04**](./sprints/sprint-04.md) | 📋 planned | `049` `049b` `050` `051` `052` `062` + **the A/A floor run** |
| [**05**](./sprints/sprint-05.md) | 📋 planned | `006` `053` `054` `055` `056` `057` `058` |

\* **Marked done with unmet exit criteria.** `TASK-018`'s tool container and `TASK-015`'s OpenHands arm are both open, both stated in the task's own prose, and both scan as ✅. See [`coverage_audit.md`](./coverage_audit.md).

### Pool — milestone-tagged, not scheduled

| Milestone | Tasks | Blocked until |
| :--- | :--- | :--- |
| **M2-eng** | `032` `064` `065` `066` `068` `069` | Sprint 4's per-task wall-clock sizes it |
| **M2-abl** | `024` `025` `031`→`056` `070` | The floor. Ablation wall-clock is `derived_N × tasks × arms` |
| **M3** | `033` `035` `059` `060` `061` `067` | M2 |
| **M4** | `036` `042` `043` `044` `045` `046` `048` `071` `072` `073` `074` `015b` | M3 + the floor |
| **CI-gated, no milestone** | `030a` `030b` | Gated by the I11 red-team corpus, not by a milestone |
| **Post-M1b** | `063` `075` | Land with the first client that renders them |
| **Post-M4** | `evolution/` · meta-loop | Deliberately deferred ([`coverage_audit.md`](./coverage_audit.md) G6) |

### The promotion rule

A pool task becomes scheduled when **all four** hold. Anything less is a wish with a task id.

1. Its milestone's predecessors have closed their exit gates in `milestones.md`.
2. Its own exit criteria are falsifiable — and where it adds a gate, that gate ships with a test proving it **can fail** ([`measurement.md` §5](../measurement.md#5-gate-design)).
3. A sprint file names it, with target files and a definition of done.
4. If it produces a number, the family is declared *before* any arm runs ([ADR-0003](../decisions/0003-statistical-admission-protocol.md)).

The complexity tables in [§Backend Roadmap](#backend-roadmap-complexity--developer-assignment) follow the same split: one table per **scheduled** sprint, and one table for the **pool**, tagged by milestone only. A projected ten-sprint arc — explicitly non-binding — is in [`release_plan.md`](./release_plan.md).

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

### TASK-039: Repair Step Source Context Re-reading ✅ DONE
* **Description**: `RepairStep` re-reads worktree files via `self._dispatch.read()` and embeds current file state into repair prompts.
* **Target Files**: `src/aether/workflow/nodes/repair.py`
* **Normative Specs**: [ADR-0010](../decisions/0010-context-prefix-layers.md)

### TASK-040: Engine Registry File Forwarding & Auto-Files Topology ✅ DONE
* **Description**: `engine.py` forwards `params.get("entry_files")` to `RepairStep`; created `linear_repair_autofiles_v1.yaml`.
* **Target Files**: `src/aether/engine.py`, `workflows/linear_repair_autofiles_v1.yaml`
* **Normative Specs**: [ADR-0014](../decisions/0014-workflow-topology-is-data.md)

### TASK-041: Dynamic Task Instruction & Auto-File Discovery ✅ DONE
* **Description**: `scripts/run_local_check.py` auto-discovers task `.py` files and injects `run_tests.py` assertions into task instructions.
* **Target Files**: `scripts/run_local_check.py`
* **Normative Specs**: [`spec.md` §7](../spec.md#7-measurement)

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

### TASK-049: I7 Enforcement — `tests_unmodified` Gate (Milestone M1a++R) — **blocks the floor**
* **Description**: The invariant [`spec.md` §2](../spec.md#2-invariants) names as I7's mechanism does not exist in this tree: `grep -rn "tests_unmodified" src/aether/` returns nothing. The evaluator must refuse to score a candidate whose test files differ from the manifest's pinned hashes.
* **Target Files**: `src/aether/measurement/evaluator.py`, `src/aether/domain/gate.py`, `src/aether/workflow/edit_format.py`
* **Normative Specs**: [`spec.md` §2 (I7)](../spec.md#2-invariants), [`measurement.md` §2 (B4)](../measurement.md#2-instrument-blockers), [`measurement.md` §5](../measurement.md#5-gate-design)
* **Exit Criteria**: A candidate that modified a pinned test file yields **`GateStatus.NONE` with `instrument_error` populated** — never `PASSED`, never `FAILED`. **Negative test required**: removing the gate must make the suite go red. The last-resort `.py`-token inferrer at `edit_format.py:198-202` is deleted — an unlabelled fence with no resolvable target returns *no edit*, not a guessed one (it reproducibly targeted `run_tests.py`).
* **Why it matters**: without it, the generator can edit its own evaluator, and every resolve rate measured on this instrument is unfalsifiable.

### TASK-049b: Demote Test-Source Injection to a Named Ablation Arm (Milestone M1a++R) — **blocks the floor**
* **Description**: `scripts/run_local_check.py` injects the full text of `run_tests.py` into the task instructions. That measures assertion-fitting, not bug-fixing, and breaks the pre-registered baseline.
* **Target Files**: `scripts/run_local_check.py`, `src/aether/domain/config.py`
* **Normative Specs**: [`measurement.md` §4.1](../measurement.md#41-the-baseline-is-part-of-the-instrument)
* **Exit Criteria**: Injection is reachable **only** via `AblationFlags.inject_test_source`, default `False`, and the flag is part of the run's config hash so any run using it says so in its own instrument tuple. The default path shows the model no test source.

### TASK-062: Non-Interactive Subprocess Hardening (Milestone M1a++R)
* **Description**: Three host-side spawn sites inherit stdin and the whole host environment, and one has no timeout at all. `adapters/tools/builtin.py:110-120` runs `create_subprocess_shell` with no `stdin`, no `env` and no deadline — the `BudgetDims(wall_clock_ms=30000)` passed by `generate.py:189` is a cost *estimate* the governor reserves against and nothing enforces. `measurement/evaluator.py:56` builds `_EVAL_ENV = {**os.environ, ...}` and hands the operator's full shell environment — API keys included — to model-written code on the uncontained path.
* **Target Files**: `src/aether/adapters/subprocess_env.py` (new), `adapters/tools/builtin.py`, `measurement/evaluator.py`, `adapters/workspace/git_cli.py`
* **Normative Specs**: [`measurement.md` §2 (B4)](../measurement.md#2-instrument-blockers), [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published), [`spec.md` §5](../spec.md#5-execution)
* **Exit Criteria**: `stdin=DEVNULL` and an **environment allowlist** (not `{**os.environ}`) at every host spawn site; every subprocess carries an `asyncio.wait_for` deadline **derived from the lease**, not a decorative estimate. `CI=1` enters through the container's `--env` allowlist as a declared part of the evaluation environment — changing it is a new manifest hash. **Negative test**: a command that would block on stdin must fail fast rather than hang to the timeout.
* **Why it matters**: a hung tool call runs to timeout, returns `GateStatus.NONE`, and `NONE` is **excluded from the resolve-rate denominator**. An interactive prompt nobody answers therefore shrinks N *non-randomly* — repositories that prompt are systematically dropped — and it is invisible in the aggregate. Deterministic non-interactivity is a precondition for the floor meaning what it says. See [`proposal_competitors_execution_mechanics_evaluation.md`](../fixes/proposal_competitors_execution_mechanics_evaluation.md) §2.

### TASK-063: Live Log Telemetry on the Lossy Channel Only
* **Description**: A `LogLineEmitted` event carrying stdout/stderr lines as they arrive, so a TUI or GUI can show `12/45 tests passed…` without waiting for the command to finish.
* **Target Files**: `src/aether/domain/events.py`, `adapters/sandbox/podman.py`, `adapters/tools/builtin.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients), [ADR-0013](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Delivered **only to `drop_oldest` subscribers**. The durable trajectory store keeps the `tail_biased()` summary it already keeps — per-line rows on the `"never"` channel would make replay ordering depend on OS pipe scheduling rather than on the topology, weakening `TASK-026`'s byte-determinism. Event-catalog drift check regenerated.
* **Status**: Post-M1b — lands with the first client that renders it. No correctness payoff, so it does not compete with the floor.

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
* **`TASK-067` — execution-based candidate ranker, lands with this task.** `workflow_schema.yaml:105-108` already declares `rank_by` with the constraint written in: *"Rankers ORDER candidates and may never ADMIT one (I9) — admission is the evaluate node, always."* There is no ranker, so Best-of-N would be an N× cost multiplier taking the first-pass candidate. Proposed selector: run the repository's **visible** test suite against each candidate and rank by pass count — zero inference tokens, it is execution not generation. **The trap:** if the visible suite includes the gate's tests, the ranker becomes a shadow evaluator and the harness selects on the answer. The manifest must record the visible/hidden partition per task, and a task where they cannot be separated is **excluded with a published reason** (`TASK-014`'s rule). The gate stays the sole admitter.
* **Also in scope, deferred here deliberately — background/async effect execution.** Kimi CLI's `run_in_background` pattern was evaluated and refused at M1 ([`proposal_competitors_execution_mechanics_evaluation.md`](../fixes/proposal_competitors_execution_mechanics_evaluation.md) §1): a process outliving its lease makes `actuals` arrive after `release()`, which is the after-the-fact accounting `TASK-034` exists to make unrepresentable; a completion event waking the executor inverts `spec.md` §8 (*events never schedule nodes*); and a wall-clock-dependent completion point breaks `TASK-026`'s byte-deterministic replay. If it lands at all it lands **here**, as a bounded construct that carries a child lease and a declared join — the same model as fan-out — or it is not expressible in a valid topology.

### TASK-034: `ResourceGovernor` Reserve / Commit / Release — ✅ DONE (Sprint 2)
* **Description**: The budget triple as an atomic ledger.
* **Target Files**: `src/aether/kernel/governor.py`
* **Normative Specs**: [`spec.md` §5](../spec.md#5-execution), [`tech_stack_and_infra.md` §4.5](../development/tech_stack_and_infra.md)
* **Exit Criteria**: The dispatcher **refuses any effect without a live lease**, making after-the-fact accounting structurally unrepresentable. Integer arithmetic only. Overrun records a typed `BudgetOverrun` event and debits reality. **A child lease's release refunds the parent, not the global pool.**
* **Why it matters**: budget-recorded-after-the-fact was H2 in the predecessor's refactor plan, and it worsens under Best-of-N fan-out.

---

## Epic 5: Capability, Composition & Abstraction (M1b → M3)

Source: [`proposal_abstraction_and_harness_composition.md`](../fixes/proposal_abstraction_and_harness_composition.md).
**None of these produces a number**, so [ADR-0002](../decisions/0002-no-number-before-the-floor.md) does not gate them — they may run in parallel with the floor. The M1b subset is sequenced **before M2** because `TASK-031`, `TASK-024` and `TASK-033` all target `src/aether/agency/context/`, a package that does not exist.

> **This epic spans three milestones — it is a subject grouping, not a sprint.** Only the **M1b** tasks are scheduled (Sprint 5): `050` `051` `052` `053` `054` `055` `056` `057` `058`. The rest sit in the pool: `059` `060` `061` are **M3** and TCB or TCB-adjacent; `064` `065` `066` `068` `069` are **M2-eng**; `070` is **M2-abl**. The [scheduling ledger](#scheduling-ledger) is authoritative.

### TASK-050: Move Effect Payloads to `domain/effects.py`
* **Description**: `ReadArgs`, `WriteArgs`, `ApplyPatchArgs`, `ShellArgs` are pure frozen models defined in `composition.py` (lines 36-62), the same module that imports `OpenAICompatibleProvider`, `BuiltinToolRegistry` and `GitCliWorkspace` at module scope. Every node imports them from there.
* **Target Files**: `src/aether/domain/effects.py` (new), `src/aether/composition.py`, `src/aether/workflow/nodes/*.py`
* **Normative Specs**: [`spec.md` §2 (I1)](../spec.md#2-invariants), [`spec.md` §3](../spec.md#3-structure)
* **Exit Criteria**: `import aether.workflow.nodes.retrieve` **does not import `httpx` or any `aether.adapters` module** — verified today as importing three of them. Negative test proves the check can fail. This is the precondition for any out-of-process extraction ([ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md)).

### TASK-051: One `worktree_path`, Not Four
* **Description**: Worktree layout is an invariant expressed four times: `measurement/evaluator.py:71`, `adapters/tools/builtin.py:53`, `adapters/indexer/tree_sitter.py:24`, and `adapters/workspace/git_cli.py:39`.
* **Target Files**: `src/aether/domain/workspace.py` + the four call sites
* **Exit Criteria**: One definition on `WorktreeRef`. One copy is inside the TCB — the judge and the tool registry must be provably unable to disagree about where a worktree is.

### TASK-052: `Envelope` Base for Node Payloads
* **Description**: `RetrievedContext`, `GeneratedPatch`, `AppliedPatch` and `EvaluatedCandidate` each re-declare `task` + `worktree`; three re-declare `iteration`.
* **Target Files**: `src/aether/domain/envelope.py` (new), `src/aether/workflow/nodes/*.py`
* **Exit Criteria**: Socket types are unchanged — `validator.check_socket_compatibility` still distinguishes all four. A field added to the envelope is a one-file change.

### TASK-053: ADR-0018 + Lattice Change — `workflow` above `agency`
* **Description**: `spec.md` §3 declares `agency/` with a `context/` subpackage. It does not exist, because `.importlinter`'s `aether-layers` makes `aether.agency` and `aether.workflow` **independent siblings**, so a `WorkflowStep` importing prompt logic from `agency/` breaks a 9-for-9 contract. The arrangement was chosen when `agency/` was empty.
* **Target Files**: `.importlinter`, `docs/decisions/0018-agency-below-workflow.md` (new), `docs/spec.md` §3
* **Normative Specs**: [`spec.md` §3](../spec.md#3-structure), [ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Exit Criteria**: `lint-imports` stays **9/9 with `agency` populated**. `agency/` still cannot import `workflow/`, `measurement/` or the evaluator — the TCB direction is unchanged. The ADR carries a reversal condition. **No contract may select zero modules** ([`measurement.md` §5](../measurement.md#5-gate-design)).

### TASK-054: `ContextSource` Protocol + First Implementations
* **Description**: "Read these files into a prompt block" is implemented twice with different semantics — `retrieve.py:67-93` (byte budget, publishes `missing`) and `repair.py:122-132` (no budget, swallows errors). Unify as a protocol with a registry, following `edit_format.py`'s template exactly.
* **Target Files**: `src/aether/agency/capabilities/sources.py`, `src/aether/agency/registry.py`
* **Normative Specs**: [ADR-0010](../decisions/0010-context-prefix-layers.md), [ADR-0015](../decisions/0015-taintgate-provenance-model.md)
* **Exit Criteria**: One file-reading path with one byte-budget policy. **A block's `Provenance` label is a property of its source, declared once** — not hand-constructed at the 10 current `TaintSpan(...)` call sites. `SymbolSource` wraps `TreeSitterIndexer`, which today passes conformance and is **reachable from no node and no topology**.

### TASK-055: `Inference` + `OutputParser` Protocols
* **Description**: The model-call-and-collect idiom is written four times (`architect.py:88`, `architect.py:142`, `repair.py:180`, `generate.py:146`), and all four reserve `BudgetDims(prompt_tokens=self._max_tokens)` — `max_tokens` is a *completion* ceiling. One bug, four sites.
* **Target Files**: `src/aether/agency/capabilities/inference.py`, `parsers.py`
* **Exit Criteria**: One implementation. `ToolLoop` (today's `MAX_ROUNDS` loop, reachable only from `generate`) becomes usable by **any** role. Reservation uses `completion_tokens` and is priced, not zero.

### TASK-056: `PromptAssembler` — the Five-Layer Prefix *(this is `TASK-031`, relocated)*
* **Description**: `TASK-031` with a real home. It cannot be built today: prompt layering is `f"{instructions}\n\n## Header\n{text}"` inside `architect.py:92-96` and `architect.py:145-152`, so there is no object that holds the layers.
* **Target Files**: `src/aether/agency/context/assembler.py`
* **Normative Specs**: [ADR-0010](../decisions/0010-context-prefix-layers.md), [`spec.md` §2 (I10)](../spec.md#2-invariants)
* **Exit Criteria**: Unchanged from `TASK-031`. Layer order L1–L5; ≤4 breakpoints; CI floor on **harness-side byte-identical-prefix stability over a fixed replay** — *not* a provider-reported hit rate, which the local endpoint may not expose at all.
* **Note**: this replaces `TASK-031`'s target file. It is not an additional task and must not be double-counted.

### TASK-057: `ModelNode` + `RoleSpec` Catalog
* **Description**: `ArchitectStep`, `GenerateStep`, `RepairStep` and `ReflectorStep` differ by their context sources and their parser, and by little else. One `ModelNode` plus four data declarations replaces three files.
* **Target Files**: `src/aether/agency/nodes/model_node.py`, `src/aether/agency/roles.py`; deletes `workflow/nodes/{architect,generate,repair}.py`
* **Normative Specs**: [ADR-0007](../decisions/0007-architect-editor-seam.md), [ADR-0014](../decisions/0014-workflow-topology-is-data.md)
* **Exit Criteria**: **A golden-prompt equivalence test**: every shipped topology produces byte-identical prompts before and after. Old classes stay one release, deleted once the test passes. Defining a new role is a data change, not a class. Closes `TASK-047`'s missing coverage — including *a test that the architect's plan reaches the generate node's prompt*, currently unasserted.

### TASK-058: `RunConfig` Domain Model
* **Description**: `engine.run()` takes 15 loose keyword arguments; several behaviours are reachable only from `scripts/run_local_check.py`. A frontend cannot render a form for a signature, and a config file cannot round-trip one.
* **Target Files**: `src/aether/domain/config.py`, `src/aether/engine.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients), [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published)
* **Exit Criteria**: `engine.run(config: RunConfig)` — one parameter. `sha256(RunConfig)` **is** `measurement.md` §6's instrument tuple, replacing hand-assembly. CLI/TUI/GUI forms generate from `model_json_schema()`. **The engine refuses `split: holdout | sealed` while `noise-floor.md` holds no number** — enforcement in the engine, not a warning in a UI.

### TASK-059: `ExecutionStrategy` Seam — **TCB**
* **Description**: `executor.py` hard-codes two traversals: `_topological_order` (line 96, a 1:1 `edge_map` that silently drops a second outgoing edge) and `_run_repair_unroll` (line 213). Promote them to registered strategies so `TASK-035` adds a strategy rather than rewriting `execute()`.
* **Target Files**: `src/aether/workflow/strategies.py`, `executor.py`, `validator.py`
* **Normative Specs**: [ADR-0013](../decisions/0013-workflow-dag-phased.md), [`spec.md` §6](../spec.md#6-trusted-computing-base)
* **Exit Criteria**: The graph stays acyclic and every bound stays **static** — a strategy may not introduce a runtime-unbounded loop. Each strategy's bound has a malformed fixture proving the check can fail (`TASK-020`'s rule, inherited). **Human review mandatory; not a meta-loop auto-commit** ([ADR-0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)).

### TASK-060: Topology Fragments (`schema_version: 1.1.0`) — **TCB-adjacent**
* **Description**: Seven topologies in `workflows/` share `apply → evaluate` and the same repair-block shape by re-typing them. Adding a node kind is a seven-file edit. Give the data layer a composition operator.
* **Target Files**: `src/aether/workflow/schemas/workflow_schema.yaml`, `validator.py`, `workflows/fragments/`
* **Normative Specs**: [ADR-0014](../decisions/0014-workflow-topology-is-data.md), [`spec.md` §4](../spec.md#4-ports) (additive-only versioning)
* **Exit Criteria**: **Expansion happens before validation** — the five static checks run on the fully expanded graph and are not modified, so a fragment cannot smuggle a node past the judge. Fragments are hash-pinned like topologies (ADR-0014: *every cross-reference is by hash, never by filename*). Three malformed fixtures: self-referential cycle, judge-bypass, node-id collision. 1.0.0 topologies keep validating.

### TASK-061: Declarative Arm Files
* **Description**: An ablation arm is a function today. It should be the hash-pinned data a topology already is: topology hash + routes + manifest + split + seed.
* **Target Files**: `src/aether/measurement/arms/`, `runner.py`
* **Normative Specs**: [ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md), [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published)
* **Exit Criteria**: A gate family names arm hashes. A run's full instrument tuple is one hash. Depends on `TASK-058`.

### TASK-064: Localization `ContextSource` Set — **SWE-bench precondition**
* **Description**: There is no localization step. `RetrieveStep` reads the files a node's YAML *names* (`retrieve.py:57-65`); `Task` carries no file list; the only discovery mechanism is `run_local_check.py:56-62`, which globs **every** `.py` under a task directory. That works for the synthetic internal manifest (one `mod.py` per task) and returns **the entire repository** on a real SWE-bench instance, where `max_bytes` then truncates in alphabetical order.
* **Target Files**: `src/aether/agency/capabilities/sources.py`
* **Normative Specs**: [ADR-0011](../decisions/0011-no-lsp-adapter.md) (syntax tier only), [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published)
* **Exit Criteria**: `LexicalSource` (identifiers and tracebacks from the issue text → grep), `SymbolSource` (`TreeSitterIndexer.search`), `TestPathSource` (failing test's imports → modules under test), `HistorySource` (`git log -S<identifier>`). **Deterministic and seeded** — a retrieval set that varies run to run makes reproducibility unsatisfiable. Files not retrieved are published in `RetrievedContext.missing`. **Each source is separately ablatable.**
* **Why it matters**: `STATUS.md` records the SWE-bench floor as blocked on per-instance images (`TASK-036`). That is true and incomplete — **with every image built, the harness still has no mechanism for choosing which files to open.** See [`proposal_sota_gap_analysis.md`](../fixes/proposal_sota_gap_analysis.md) §2.

### TASK-065: Retrieval-Recall Diagnostic
* **Description**: For each unresolved task, did the gold patch's files appear in the retrieved set?
* **Target Files**: `src/aether/measurement/` (offline analysis over the trajectory store)
* **Exit Criteria**: One published number per run, separating *"never shown the file"* from *"shown the file and failed"*. It decides whether effort goes into retrieval or generation, and nothing else in the plan produces it. **The premise that localization dominates SWE-bench failures is a widely-reported hypothesis this project has not measured** ([`spec.md` §9](../spec.md#9-standing-rules)); this task is the experiment that settles it on our own instrument.

### TASK-066: `SearchReplaceFormat` — the Third Edit Format
* **Description**: Unified diff is fragile for small models (well-formed diffs with wrong context lines); whole-file *"burns output tokens proportional to file size"* by `edit_format.py`'s own admission. SEARCH/REPLACE blocks are the middle — no context lines to reproduce, output proportional to the change.
* **Target Files**: `src/aether/workflow/edit_format.py`, `workflows/`
* **Exit Criteria**: One class, one registry entry, the existing conformance suite unmodified — the module docstring already states this is the intended extension shape. Ablatable on arrival against both incumbents.

### TASK-068: Capability Attenuation per `RoleSpec`
* **Description**: `ArchitectStep` is read-only because it happens not to call `dispatch.write` — a property of the code, not of the architecture. Nothing prevents a role declaration from naming a write-capable tool and editing the worktree before the judge runs.
* **Target Files**: `src/aether/agency/roles.py`, `src/aether/workflow/dispatch_facade.py`
* **Normative Specs**: [ADR-0017](../decisions/0017-subagent-capability-attenuation.md) (*a sub-agent is a subgraph; capabilities only narrow*), [`spec.md` §5](../spec.md#5-execution)
* **Exit Criteria**: A `RoleSpec` declares its permitted `effect_class` set; the `DispatchFacade` handed to that node is **attenuated at construction**. `ARCHITECT` is `{read, model}` **by type**, and a plan node attempting a write is denied at the choke point rather than trusted not to try. Negative test required.

### TASK-069: Turn Budget and Loop Detection
* **Description**: `generate.py:77` hard-codes `MAX_ROUNDS = 4` with no repeated-call detection, so a model reissuing the same failing tool call burns four round trips every time.
* **Target Files**: `src/aether/agency/capabilities/inference.py` (after `TASK-055`)
* **Exit Criteria**: Turn ceiling comes from node params, not a class constant; an identical consecutive tool call short-circuits the loop and is recorded.

### TASK-070: `RunConfig.mode` — Benchmark vs Interactive
* **Description**: The two modes have opposite correctness requirements. In benchmark mode an `ASK_*` policy decision must **fail closed** — a human in the loop is a human in the measurement, and a run that blocks for approval has an unbounded wall-clock *and* a human contributing to the resolve rate.
* **Target Files**: `src/aether/domain/config.py`, `src/aether/kernel/dispatch.py`
* **Exit Criteria**: `mode` enters the config hash, so `measurement.md` §6's instrument tuple records which mode produced a result. Benchmark mode also forces cross-task memory off and retrieval deterministic.

### TASK-071: SWE-bench Manifest Build & Validity Canary at Scale (Milestone M4)
* **Description**: Build and pin a real-world task manifest for SWE-bench (Verified and Pro) reusing `TASK-014`'s tooling. Run a bidirectional validity canary asserting that gold patches pass and empty patches fail on our isolated evaluation container environment. Publish exclusions with reasons (~30% of public Pro tasks were estimated broken in prior audits).
* **Target Files**: `scripts/build_swe_manifest.py`, `benchmarks/manifests/swe_bench_verified_pinned.yaml`, `benchmarks/manifests/swe_bench_pro_pinned.yaml`
* **Normative Specs**: [`measurement.md` §2 (B3)](../measurement.md#2-instrument-blockers), [`measurement.md` §6](../measurement.md#6-pre-publication-verification-gate)
* **Exit Criteria**: 100% of non-excluded tasks pass the bidirectional canary in the containerized floor environment. Exclusion manifest published with hash.

### TASK-072: SWE-bench A/A Noise Floor (Milestone M4)
* **Description**: Execute the A/A noise floor protocol over the pinned SWE-bench manifest. Characterize instrument variance, derive benchmark-specific $p_{01}$ and $p_{10}$ discordance rates, and compute the required minimum sample size $N$ for SWE-bench capability admission runs.
* **Target Files**: `scripts/run_swe_aa_floor.py`, `docs/rationale/benchmarks/swe_noise_floor.md`
* **Normative Specs**: [ADR-0002](../decisions/0002-no-number-before-the-floor.md), [ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md), [`measurement.md` §3](../measurement.md#3-the-aa-variance-floor)
* **Exit Criteria**: Report published with exact McNemar discordance, derived $N$ for power $\ge 0.80$, per-task wall-clock distributions, and zero instrument errors ($NONE$).

### TASK-073: Paired Lift Run (Bare-Model vs AETHER) (Milestone M4)
* **Description**: Execute paired lift runs comparing bare unassisted model calls vs. full AETHER harness execution using the exact same base model on the pinned SWE-bench manifest under [`measurement.md` §4.1](../measurement.md#41-the-baseline-is-part-of-the-instrument)'s pre-registered baseline.
* **Target Files**: `src/aether/measurement/runner.py`, `scripts/run_paired_lift.py`
* **Normative Specs**: [ADR-0004](../decisions/0004-benchmark-targets.md), [`measurement.md` §4](../measurement.md#4-the-lift-target-delta-is-the-committed-number)
* **Exit Criteria**: Paired McNemar $p$-value and Holm–Bonferroni corrected confidence intervals computed. Lift target ($\Delta \ge +10$ points) verified or falsified.

### TASK-074: Publication Run on SEALED Dataset (Milestone M4)
* **Description**: Execute the final publication run on the SEALED split satisfying all 7 pre-publication verification conditions of [`measurement.md` §6](../measurement.md#6-pre-publication-verification-gate).
* **Target Files**: `scripts/run_sealed_publication.py`, `docs/rationale/benchmarks/publication_sealed.md`
* **Normative Specs**: [`measurement.md` §6](../measurement.md#6-pre-publication-verification-gate)
* **Exit Criteria**: All 7 conditions satisfied: single hash instrument tuple, zero unhandled errors, exact McNemar $p$-value, Holm-Bonferroni correction, budget audit passed, raw trajectory log archived, and container digest verified.

### TASK-015b: OpenHands Arm Through Our Evaluator (Milestone M4)
* **Description**: Integrate the OpenHands arm into `HarnessUnderTest` (`TASK-015`), routing OpenHands execution through our containerized TCB `Evaluator` for true apples-to-apples comparative benchmarking against AETHER on the same manifest.
* **Target Files**: `src/aether/measurement/runner.py`, `src/aether/adapters/openhands_runner.py`
* **Normative Specs**: [`spec.md` §9](../spec.md#9-standing-rules) (no self-reported competitor metrics), [`measurement.md` §4](../measurement.md#4-the-lift-target-delta-is-the-committed-number)
* **Exit Criteria**: OpenHands arm executes on pinned manifest through our evaluator; paired McNemar comparison generated against AETHER arm.

### TASK-075: Read-Only TUI Client over Event Bus (Post-`TASK-058`)
* **Description**: Build a standalone read-only TUI client (`tui/`) that subscribes to `engine.py`'s lossy event stream channel. Provides live terminal progress, node status, and telemetry without holding privileged grants.
* **Target Files**: `src/aether/tui/`, `scripts/run_tui.py`
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients-and-event-streams), [`spec.md` §3](../spec.md#3-structure)
* **Exit Criteria**: Read-only TUI displays execution graph progression and live telemetry from `engine.run()` with zero direct access to kernel dispatch or evaluator.


---

## Epic 6: Per-Node Model Routing & Hybrid Economics (post-floor)

Source: [`proposal_workflows_hybrids_improvements.md`](../fixes/proposal_workflows_hybrids_improvements.md).
`workflows/hybrid_architect_editor_v1.yaml` is committed and **cannot run**: `params.base_url` is dropped by the architect factory (`engine.py:112-117`) and one provider is built for the whole run (`engine.py:178`). **These tasks build routing; they do not authorise an arm.** Any hybrid arm is admitted through [ADR-0003](../decisions/0003-statistical-admission-protocol.md) after the floor, or not at all.

### TASK-042: `RoutingModelProvider` — Per-Node Endpoint & Credential Routing
* **Description**: A `ModelProvider` composite selecting a concrete provider per `ModelRequest.model`. The name is already an unbuilt promise in `openai_compatible.py:79-80`.
* **Target Files**: `src/aether/adapters/model_provider/routing.py`, `engine.py`, `composition.py`
* **Normative Specs**: [ADR-0005](../decisions/0005-eight-ports-adapter-first.md) (**second adapter of an existing port, not a new port**), [ADR-0007](../decisions/0007-architect-editor-seam.md), [`spec.md` §2 (I6)](../spec.md#2-invariants)
* **Exit Criteria**: Passes the existing `ModelProvider` conformance suite **unmodified**. Routes frozen at composition — a topology naming an unrouted endpoint raises **at load**, matching `UnregisteredNodeKind`'s precedent. API keys resolve from the environment and **never appear in a topology file**. Negative test for an unknown route.

### TASK-043: Node-Scoped Pricing
* **Description**: `pricing.py:71-73` short-circuits on the *run's* `base_url`, so once TASK-042 lands, a paid call still prices at `PRICES["local"]` = $0.00.
* **Target Files**: `src/aether/measurement/pricing.py`, `composition.py`
* **Normative Specs**: [ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md) §4
* **Exit Criteria**: A run mixing a local node and a paid node reports **non-zero** `usd_micros`. **Negative test required** — a paid call mispriced as local must make the suite fail. Without this, cost per resolved task is `$0.0000` for every arm and the non-inferiority check passes **vacuously**.

### TASK-044: Reserve the Dollar Estimate, Not Zero
* **Description**: Nodes reserve `BudgetDims(prompt_tokens=max_tokens)`; `usd_micros` is filled only at commit, so the run ceiling is checked against zero and an overrun is detected on the *next* reserve.
* **Target Files**: `src/aether/workflow/nodes/*` (or `agency/capabilities/inference.py` after TASK-055)
* **Normative Specs**: [`spec.md` §5](../spec.md#5-execution)
* **Exit Criteria**: A run seeded below the cost of its first call is denied **at that call**. Also fixes the completion/prompt dimension error.

### TASK-045: Enforce the Per-Node Budget — **TCB**
* **Description**: `executor.py:174` reserves the node budget; `executor.py:194` releases it with **no commit**. The declared figure constrains nothing.
* **Target Files**: `src/aether/workflow/executor.py`, `dispatch_facade.py`
* **Exit Criteria**: A node whose effects exceed its declared budget is **denied at the choke point**, and the denial names the node. **This is what makes "the architect node costs at most $0.05" a fact rather than a comment.** Touches TCB — human review required.

### TASK-046: Wire `reflector`, or Delete It
* **Description**: `ReflectorStep` is registered at `engine.py:119-124` and referenced by no topology and no test.
* **Normative Specs**: `TASK-025`'s own rule — *a disabled code path nobody measures is debt, not optionality*
* **Exit Criteria**: One of: a topology exercising it end-to-end with a test, or the node and its `NODE_SOCKETS` entry deleted. **Not both, and not neither.** Superseded by `TASK-057` if the role catalog lands first.

### TASK-048: Provenance for Planner Output
* **Description**: `ArchitectStep` concatenates model output into `payload.instructions`; the next node labels `instructions` as `Provenance.OPERATOR` (`generate.py:97`). Planner output derived from repo files acquires operator provenance in two hops.
* **Normative Specs**: [ADR-0015](../decisions/0015-taintgate-provenance-model.md), [`spec.md` §2 (I11)](../spec.md#2-invariants)
* **Exit Criteria**: A planner span carries its own label rather than being merged into an `OPERATOR` string. **Largely absorbed by `TASK-054`**, which makes labels a property of the source. **Recorded caveat**: labelling repo content `untrusted-external` as `spec.md` §5 requires would make `DefaultPolicyEngine` fail closed on *every* shell tool call — a defensible sequencing choice pending `TASK-030a`, but it must appear in `STATUS.md`'s deviations section, because I11 currently reads as enforced.

---

## Epic 7: Benchmark Delivery & Public Claims (Milestone M4 — Competitor & Leaderboard Validation)

Source: [`coverage_audit.md`](coverage_audit.md) §1 (Gap G1 resolution). Funds the mission statement in [`vision.md`](../vision.md) §1 and [`measurement.md`](../measurement.md) §4 to compete on SWE-bench Verified and SWE-bench Pro.

### TASK-071: SWE-bench Manifest Build & Canary at Scale (Milestone M4)
* **Description**: Build, pin, and bidirectionally validate SWE-bench Verified & Pro task manifests at scale, reusing `TASK-014`'s tooling. Screen every task with the bidirectional canary (gold patch passes, empty patch fails).
* **Target Files**: `src/aether/measurement/manifest.py`, `benchmarks/manifests/swebench_verified_v1.yaml`, `benchmarks/manifests/swebench_pro_v1.yaml`
* **Normative Specs**: [`measurement.md` §4.2–4.3](../measurement.md#42-splits-and-why-they-are-pinned), [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published)
* **Exit Criteria**: Published exclusion list with explicit typed reasons for broken tasks (~30% of public Pro tasks estimated broken). Manifest hashes pinned in TCB.

### TASK-072: SWE-bench A/A Floor Run (Milestone M4)
* **Description**: Execute the A/A variance floor on the real SWE-bench manifest to derive suite-specific discordance rates ($p_{01}, p_{10}$) and per-task wall-clock metrics.
* **Target Files**: `docs/rationale/benchmarks/swebench_noise_floor.md`
* **Normative Specs**: [`measurement.md` §3](../measurement.md#3-the-aa-variance-floor), [ADR-0002](../decisions/0002-no-number-before-the-floor.md)
* **Exit Criteria**: Discordance rates and N per gate family derived specifically for SWE-bench repositories and test runners; instrument tuple recorded.

### TASK-073: Paired Lift Run (Bare-Model vs AETHER) (Milestone M4)
* **Description**: Paired evaluation run comparing the bare-model baseline against AETHER on the pinned SWE-bench manifest under identical model endpoints and seeds.
* **Target Files**: `src/aether/measurement/runner.py`, `docs/rationale/benchmarks/swebench_lift_report.md`
* **Normative Specs**: [`measurement.md` §4](../measurement.md#4-target-benchmarks-and-required-lift), [ADR-0003 rev. 2](../decisions/0003-statistical-admission-protocol.md)
* **Exit Criteria**: McNemar $p$-value and Holm–Bonferroni adjusted significance calculated by `TASK-012`; pre-registered lift target ($\ge +10$ points) evaluated.

### TASK-074: Publication Run on SEALED (Milestone M4)
* **Description**: Execute the final publication evaluation run on the SEALED split, strictly adhering to all seven conditions of `measurement.md` §6.
* **Target Files**: `docs/rationale/benchmarks/publication_sealed_report.md`
* **Normative Specs**: [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published)
* **Exit Criteria**: All 7 publication criteria satisfied: manifest hash, model fingerprint, topology hash, container digests, lockfile hash, seed, and derived N power requirements met.

### TASK-015b: OpenHands Arm via Evaluator (Milestone M4)
* **Description**: Complete the comparative-lift rig (`HarnessUnderTest`) by integrating the OpenHands arm through our own evaluator container for apples-to-apples competitive evaluation.
* **Target Files**: `src/aether/measurement/runner.py`, `src/aether/adapters/comparative/openhands.py`
* **Normative Specs**: [`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published), [`spec.md` §9](../spec.md#9-standing-rules)
* **Exit Criteria**: OpenHands trajectory executed against our pinned manifest and scored by our TCB evaluator. Direct McNemar comparison enabled.

### TASK-075: Read-Only TUI over Event Bus (Post-M1b Client)
* **Description**: Implement a terminal user interface (TUI) as a read-only consumer of the headless engine event bus, addressing gap G5.
* **Target Files**: `src/aether/client/tui.py` (new)
* **Normative Specs**: [`spec.md` §8](../spec.md#8-clients), [ADR-0013](../decisions/0013-workflow-dag-phased.md)
* **Exit Criteria**: Renders real-time execution events without holding any execution authority or adapter handles. Form generated from `RunConfig.model_json_schema()`.

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
| M1a++R · 1 `tests_unmodified` I7 gate | `TASK-049` |
| M1a++R · 2 test-source injection demotion | `TASK-049b` |
| M1a++R · 3 non-interactive subprocesses | `TASK-062` |
| M1b · 1 `agency` below `workflow` lattice | `TASK-053` |
| M1b · 2 `ContextSource` & provenance | `TASK-054` |
| M1b · 3 single `Inference` & `OutputParser` | `TASK-055` |
| M1b · 4 5-layer prompt prefix stability | `TASK-056` |
| M1b · 5 `ModelNode` + `RoleSpec` data roles | `TASK-057` |
| M1b · 6 `RunConfig` domain model & floor guard | `TASK-058` |
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
| M4 · 1 SWE-bench manifest & canary at scale | `TASK-071` |
| M4 · 2 SWE-bench A/A floor | `TASK-072` |
| M4 · 3 paired lift run | `TASK-073` |
| M4 · 4 publication run on SEALED | `TASK-074` |
| M4 · 5 OpenHands comparative arm | `TASK-015b` |

**Not gate-funding, and deliberately so** — these support the gates above rather than closing one: `TASK-006` (mocks and cassettes), `TASK-014` (manifests and validity canary), `TASK-015` (comparative-lift rig), `TASK-022` (engine and bus), `TASK-026` (trajectory store), `TASK-030a`/`TASK-030b` (shell classifier and TaintGate — gated by the I11 red-team corpus in CI rather than by a milestone), `TASK-075` (read-only TUI).

**Gate gaps closed**: M1a++R, M1b, and M4 exit gates are now explicitly mapped to funding tasks, eliminating the G1 and G4 coverage holes.


---

## Backend Roadmap Complexity & Developer Assignment

Complexity is scored **0–5** (six levels), weighing knowledge domain required, number of interacting sub-tasks/constraints, and blast radius if the task is done wrong — not raw line count. Derived from a full read of `spec.md`, `measurement.md`, `milestones.md`, all 17 ADRs, and the `development/` engineering docs (protocols, schemas, tech stack).

**Sprint tags below are grounded in the sprint files in [`sprints/`](./sprints/README.md).** Sprint 3 was written as "the last sprint planned in full" because sizing past the floor needs the floor's per-task wall-clock. That still holds for **M2-abl and everything after it**. Sprints 4 and 5 are now planned in full anyway, and the reason is a narrow one: neither is sized by inference wall-clock. Sprint 4 is instrument repair plus the floor run itself; Sprint 5 is a refactor that produces no number and calls no model in anger. Tasks past Sprint 5 remain tagged with their milestone only, never a fabricated sprint number.

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
| `TASK-018` | Built-in Tool Registry & Execution Container | M1a (Sprint 2) | **3** · Medium *(rev.)* | A frozen catalog with construction-time taint labeling; the container half didn't ship | `ToolRegistry` adapter (`adapters/tools/builtin.py`, 120 LOC): two tools (`read_file`, `bash`), catalog frozen as a tuple in `__init__` (I6), every `ToolResult` labeled `untrusted-external` at construction (ADR-0015). **The "separate container, own lease class" isolation named in the original rationale never landed** — the module's own docstring says it "runs uncontained this sprint via `asyncio.subprocess`", and [`coverage_audit.md`](./coverage_audit.md) independently flags the tool container as still open. What's actually in the tree is a small, uncontained adapter — real but not the concurrency/security-isolation work a Hard rating implies. Re-promotes to Hard once the container lands. |
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
| `TASK-014` | Task-Manifest Tooling & Validity Canary | A/A Floor (Sprint 3) | **4** · Hard *(rev.)* | TCB-resident, hash-pinned, and larger than the triage framing suggests | `measurement/manifest.py` (414 LOC) + `measurement/validity.py` (94 LOC) — 508 LOC, more than every other Sprint-1–3 module except `statistics.py`. It is **TCB**, under the same `aether-tcb-isolation` contract as `TASK-019`'s Evaluator (also rated Hard): the module's own docstring states it "cannot import `aether.adapters`, `aether.workflow` or `aether.agency`". On top of the bidirectional canary (gold passes *and* empty fails), it enforces schema-validated pins, sha256-identified immutability (a change is a new manifest, never an edit), and deterministic dev/holdout/sealed split assignment — several TCB-residency constraints stacked on the triage work, not triage alone. |
| `TASK-023` | Bounded Repair Loop Node | M1a+ (Sprint 3) | **4** · Hard | `vision.md`'s single largest lever on score, and it must stay a bounded loop, never an infinite one | Statically unrolls `evaluate →(fail, k)→ repair → apply → evaluate` to `max_iterations` (1–16) so the DAG stays acyclic by construction. Three constraints carry the real difficulty: the validator must reject an unbounded or over-bound block, each iteration reserves its **own** budget through the governor triple, and a `GateReport` of `NONE` must never route into repair — repairing against a broken instrument would teach the loop to fix the harness's own bugs. Named in `vision.md` as the single largest lever on score, so correctness here has outsized leverage on every later benchmark number. |
| `TASK-012` | Statistical Engine & A/A Variance Floor | A/A Floor (Sprint 3) | **5** · Very Hard | The instrument that decides whether every future number in this project is allowed to exist | Ports the predecessor's 259-LOC `e0/statistics.py` verbatim (exact McNemar, Holm–Bonferroni, seeded bootstrap — the one asset from the prior codebase that verified line-by-line), then adds real new complexity: a seeded Monte-Carlo power simulation deriving N per gate family from a pre-registered discordance assumption, target power ≥0.80, and the Holm-adjusted α at that hypothesis's rank — plus a gatekeeper that **refuses to compute corrected p-values for an undeclared family**. Demands genuine applied-statistics fluency (why a fixed N=50 silently discards 9 of 10 true improvements is not obvious without running the simulation), and its correctness gates every admission decision the project will ever make. |
| `TASK-015` | Comparative-Lift Rig (`HarnessUnderTest`) | Sprint 3 (bare-model arm only) / Post-Floor (full) | **4** · Hard *(rev.)* | The seam and the pre-registered baseline, not the cross-harness integration | `measurement/runner.py` (304 LOC): a `HarnessUnderTest` protocol plus `BareModelHarness` — one completion, the official SWE-bench template with its hash recorded, no execution feedback, temperature/seed pinned. The module's own docstring is explicit that "**Sprint 3 ships the seam plus the bare-model arm only**… The OpenHands arm is explicitly out of scope." The genuinely Very-Hard part — wrapping a third-party OSS harness uniformly enough to be paired-comparable — is exactly what shipped in *neither* Sprint 3 nor this row; it is tracked and independently rated Very Hard as `TASK-015b`. Rating this row at the same level double-counts that difficulty against work not yet done here. |

### Sprint 3.5 — Phase 0 Lock (code complete)

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-037` | EditFormat Seam — Unified Diff & Whole-File | Phase 0 (Sprint 3.5) | **2** · Easy | Swappable edit format via YAML params | Unified diff (with --3way fallback) and whole-file (regex + AST validation) swappable per node without code changes. |
| `TASK-038` | Node Registry Keyed by Kind | Phase 0 (Sprint 3.5) | **2** · Easy | Dynamic node resolution from YAML topology | Maps node kinds dynamically from `params`, allowing multiple generate nodes in one topology. |
| `TASK-039` | Repair Step Source Context Re-reading | Phase 0 (Sprint 3.5) | **2** · Easy | Worktree context re-read via dispatch | Re-reads worktree files using `_dispatch.read()` to embed updated file state into repair prompts. |
| `TASK-040` | Engine Registry & Auto-Files Topology | Phase 0 (Sprint 3.5) | **2** · Easy | Engine parameter forwarding | Forwards entry files to `RepairStep` and adds auto-file discovery repair topology. |
| `TASK-041` | Dynamic Task Instruction & Discovery | Phase 0 (Sprint 3.5) | **2** · Easy | Auto-discovers task files and assertions | Discovers task `.py` files and injects `run_tests.py` assertions into task instructions. |

### Sprint 4 — Instrument Restoration and the Floor (planned: [`sprint-04.md`](./sprints/sprint-04.md))

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-049` | I7 Enforcement (`tests_unmodified`) | M1a++R | **3** · Medium | The invariant the whole measurement rests on, currently enforced by nothing | Hashes the manifest's pinned test files and refuses to score a candidate that changed them, mapping a mismatch to `NONE` rather than `FAILED` — the B4 discipline applied to a second failure mode. Not algorithmically hard; the difficulty is that it lands in `measurement/evaluator.py`, which is TCB, and that it must ship with a negative test proving the gate can fail. Also deletes the `.py`-token inferrer, which reproducibly wrote model output into `run_tests.py`. |
| `TASK-049b` | Demote Test-Source Injection | M1a++R | **1** · Very Easy | A default flipped, and an honesty property restored | Mechanically small — a flag with a `False` default plumbed into the config hash. Its weight is entirely in what it means: with injection on, the harness measures whether a model can satisfy an assertion it was shown, which is not the benchmark. Every Sprint 3.5 resolve rate was produced this way. |
| `TASK-050` | Effect Payloads to `domain/` | M1b | **1** · Very Easy | A file move that removes an import edge nobody intended | Four frozen models leave `composition.py`. No behaviour changes. The exit criterion is a new negative test — importing a node must not import `httpx` — which fails today and is the reason the task exists. |
| `TASK-051` | One `worktree_path` | M1b | **1** · Very Easy | Delete three copies of an invariant | Four independent definitions of where a worktree lives, one of them inside the TCB evaluator. Mechanical, and the payoff is that the judge and the tool registry become structurally unable to disagree. |
| `TASK-052` | `Envelope` Base for Payloads | M1b | **2** · Easy | Data modelling with one subtle constraint | Four payload types share a base. The care needed is that socket types must stay distinguishable — collapsing them into one type would defeat `check_socket_compatibility`, which is the validator's whole job. |
| `TASK-062` | Non-Interactive Subprocess Hardening | M1a++R | **3** · Medium | `stdin=DEVNULL`, env allowlist, lease timeouts | Host spawn hardening to prevent interactive prompts from non-randomly shrinking the sample denominator `N`. |
| **Sprint 4 Task 5** | **Take the A/A Variance Floor** | A/A Floor | **5** · Very Hard | Unchanged from `sprint-03.md` Task 5 — deferred by decision, not by difficulty | The instrument is complete and rehearsed (`run_aa_floor.py --dry-run`, zero API calls). What makes it Very Hard is that its outputs — p₀₁/p₁₀ discordance and per-task wall-clock — size every later admission run and every remaining sprint. Blocking precondition: the B3 canary executes **in the floor environment** first. |

### Sprint 5 — The Capability Layer (planned: [`sprint-05.md`](./sprints/sprint-05.md))

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-053` | ADR-0018 + Lattice Change | M1b | **3** · Medium | One line of config, and an architectural decision behind it | Moving `aether.agency` from an independent sibling of `workflow` to a layer beneath it is a two-line `.importlinter` edit. The work is the ADR: justifying that the TCB direction is unchanged (`agency` still cannot reach `workflow`, `measurement` or the evaluator), and writing a reversal condition. Blast radius is high if wrong — a lattice that permits the judge to be imported by the judged is the one failure this project is built to prevent. |
| `TASK-054` | `ContextSource` + Implementations | M1b | **3** · Medium | The seam that makes retrieval ablatable, and provenance declarable once | Five implementations behind one protocol, following `edit_format.py`'s registry template. The real design work is that a block's `Provenance` label becomes a property of its source rather than a decision made at 10 scattered `TaintSpan(...)` call sites — which is how repository content and test tracebacks both ended up labelled `AGENT`. Also the first thing that makes `TreeSitterIndexer` reachable. |
| `TASK-055` | `Inference` + `OutputParser` | M1b | **3** · Medium | Collapse four copies of the model-call idiom into one | Straightforward extraction, with one correctness fix folded in: all four current sites reserve a *completion* ceiling in the `prompt_tokens` dimension. `ToolLoop` moving behind the protocol is what lets a planner role use tools at all, which it cannot today. |
| `TASK-056` | `PromptAssembler` (**was `TASK-031`**) | M1b / M2 Gates 3 & 6 | **4** · Hard | Five layers that must be byte-stable, provider quirks and all | Unchanged in difficulty from `TASK-031`; what changes is that it now has a home. The gated metric stays **harness-side** prefix stability over a fixed replay, deliberately not a provider hit rate — OpenAI-compatible endpoints cache implicitly and the local endpoint may report nothing. Getting layer-immutability and the replay measurement both right across providers is where the difficulty sits. |
| `TASK-057` | `ModelNode` + `RoleSpec` | M1b | **3** · Medium | Three node classes become one node and four data rows | Mechanically a consolidation; the risk is behavioural drift in prompts, which is why the exit criterion is a **golden-prompt equivalence test** over every shipped topology rather than unit coverage. Old classes stay one release. Absorbs `TASK-047`'s missing tests. |
| `TASK-058` | `RunConfig` Domain Model | M1b | **2** · Easy | Signature work with outsized downstream leverage | Fifteen keyword arguments become one frozen model. Low code risk. What it buys is disproportionate: `sha256(RunConfig)` becomes `measurement.md` §6's instrument tuple, GUI/CLI/TUI forms generate from one JSON schema, and the engine gains a place to **refuse a HOLDOUT run while the floor is empty**. |
| `TASK-006` | Mock Adapter Set & Record/Replay Cassettes | M0 / Sprint 5 | **3** · Medium | Mocks for 9 ports + byte-exact replay engine | Re-scheduled to Sprint 5 per G2 gap resolution. Builds the cassette replay engine ("100 turns under 50 ms, byte-for-byte deterministic") required for affordable M2 ablations and golden-prompt tests. |

### The pool — M2 / M3 / M4 / M5, milestone-tagged and unscheduled

**Every row below carries a milestone, never a sprint number.** A milestone fixes a task's
position in [`roadmap.md`](./roadmap.md)'s dependency DAG; a sprint number would be a date, and
the two quantities that would set one — derived N and per-task wall-clock — are outputs of
Sprint 4's floor. Rows move up into a sprint table via the [promotion rule](#the-promotion-rule),
one at a time, as the gates ahead of them close.

These land once M2-abl is sized off the floor's per-task wall-clock (`roadmap.md`). `TASK-032` was named "the first task of the next sprint" in `sprint-03.md`; it now follows Sprint 5, because `TASK-031`/`TASK-056` and `TASK-024` both target `agency/context/` and cannot start before that package exists.

| Task ID | Feature / Component | Milestone | Complexity | The Developer — why | Technical Complexity & Rationale |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `TASK-032` | Per-Node Digest Memoization | M2, Gate 1 (Sprint 6) | **3** · Medium | Cache invalidation, the classic hard problem, scoped to a DAG | Keys node execution on `sha256(node_kind, impl_version, canonical_payload)` and must invalidate **exactly** the descendants of a changed node — no more, no less. A correctness-sensitive DAG-traversal problem: over-eager invalidation defeats the ablation-speed purpose of the whole task, under-eager invalidation silently reuses stale results inside a benchmark run. |
| `TASK-031` | *(→ `TASK-056`, Sprint 5)* 5-Layer Prompt Prefix & Cache Architecture | M2, Gates 3 & 6 | **4** · Hard | Five layers that must be byte-stable, provider quirks and all | **Relocated to `TASK-056` — same task, real target directory. Do not double-count.** Context assembler enforcing L1–L4 append-only-within-a-run and ≤4 `cache_control` breakpoints, with the CI-gated metric being **harness-side** byte-identical-prefix stability over a fixed replay. |
| `TASK-025` | Architect/Editor Dual-Model Seam | M2, Gate 4 | **3** · Medium | A config-gated seam that ships off by policy, not because it's unfinished | Decouples `architect.py` (planning, no write tools) from `editor.py` (surgical edits) behind a config switch defaulting to single-model, riding the `RoutingModelProvider` composite already established by TASK-011. |
| `TASK-024` | L5 Dialogue Context Compactor | M2, Gate 5 | **3** · Medium | Compaction structurally forbidden from touching four of the five layers | Deterministic structural compaction (drop superseded file snapshots, collapse resolved tool exchanges) scoped to L5 only. |
| `TASK-030a` | Shell AST Classifier | M2/M3 (CI-gated) | **4** · Hard | A classifier that must never be mistaken for a security boundary | Parses shell commands to a `tree-sitter-bash` AST and drives the `Reject \| AskRuleMatch \| AskFailClosed` taxonomy plus a `widens_capability` flag. |
| `TASK-030b` | TaintGate Provenance & Red-Team Gate | M2/M3 (CI-gated) | **5** · Very Hard | The mechanism itself is five lines; the corpus proving it holds is the whole job | Deterministic propagation (`any untrusted span consumed ⇒ untrusted-derived output`) with enforcing predicate in TCB `PolicyEngine` validated against pinned adversarial injection corpus. |
| `TASK-035` | Conditional Branching & Best-of-N Fan-Out | M3, Gate 1 | **4** · Hard | Parallel candidates as real graph structure, with a lease tree to match | Adds conditional edges (`on_pass`/`on_fail`/`on_instrument_error`) and declared Best-of-N fan-out with child leases. |
| `TASK-067` | Candidate Ranker (I9 Type Separation) | M3, Gate 1 | **4** · Hard | Ranks candidates by visible test passes without admitting them | Implements type-level `rank()` vs `admit()` separation (G3 gap resolution). Visible test execution ranker; evaluate node remains sole admitter. |
| `TASK-033` | Best-of-N Cache Sequencing | M3, Gate 3 | **3** · Medium | A one-request barrier, built on infrastructure two other tasks already provide | Warms shared prefix on candidate 1 before releasing candidates 2..N. |
| `TASK-059` | `ExecutionStrategy` Seam (TCB) | M3 / Post-M1b | **4** · Hard | Modular graph execution strategy registry | Promotes static graph traversal routines to registered strategies. |
| `TASK-060` | Topology Fragments (TCB-adjacent) | M3 / Post-M1b | **4** · Hard | Composability operator for workflow YAMLs | Hash-pinned fragment macro expansion prior to validation. |
| `TASK-061` | Declarative Arm Files | M3 / Post-M1b | **2** · Easy | Hash-pinned ablation arm configuration | Converts arm definition functions to hash-pinned data files. |
| `TASK-064` | Localization `ContextSource` Set | M4 / Post-M1b | **3** · Medium | Syntax-tier localization source set | `LexicalSource`, `SymbolSource`, `TestPathSource`, `HistorySource` for repository file localization on real SWE-bench instances. |
| `TASK-065` | Retrieval-Recall Diagnostic | M4 / Post-M1b | **3** · Medium | Offline analysis over trajectory store | Determines if gold patch files were retrieved in unresolved tasks. |
| `TASK-066` | `SearchReplaceFormat` | M4 / Post-M1b | **3** · Medium | Middle ground between unified diff and whole file | SEARCH/REPLACE block edit format adapter. |
| `TASK-068` | Capability Attenuation per `RoleSpec` | M3 / Post-M1b | **3** · Medium | Role-based capability narrowing | Attenuates `DispatchFacade` based on `RoleSpec.permitted_effect_classes` (ADR-0017). |
| `TASK-069` | Turn Budget and Loop Detection | M3 / Post-M1b | **2** · Easy | Consecutive identical tool call short-circuit | Configurable turn limits and loop detection in inference loop. |
| `TASK-070` | `RunConfig.mode` Benchmark vs Interactive | M3 / Post-M1b | **2** · Easy | Strict fail-closed policy in benchmark mode | Forces fail-closed `ASK_*` decisions and deterministic retrieval under benchmark mode. |
| `TASK-042` | `RoutingModelProvider` | M3 / Post-M1b | **3** · Medium | Multi-provider composite adapter | Routes model requests by model name to local or external providers. |
| `TASK-043` | Node-Scoped Pricing | M3 / Post-M1b | **2** · Easy | Per-node cost tracking | Accurate pricing across hybrid local/cloud topologies. |
| `TASK-044` | Reserve Dollar Estimate | M3 / Post-M1b | **2** · Easy | Pre-execution monetary budget reservation | Checks node dollar budget ceiling at reserve time. |
| `TASK-045` | Enforce Per-Node Budget (TCB) | M3 / Post-M1b | **3** · Medium | Hard choke point node budget enforcement | Denies node execution at dispatch if node budget is exceeded. |
| `TASK-046` | Wire `reflector` or Delete It | M3 / Post-M1b | **1** · Very Easy | Resolves dead code | Either adds test topology for reflector or removes unreferenced step. |
| `TASK-048` | Provenance for Planner Output | M3 / Post-M1b | **3** · Medium | Preserves planner output taint span | Avoids mislabeling repo-derived planner output as operator input. |
| `TASK-063` | Live Log Telemetry | Post-M1b (Client) | **2** · Easy | Lossy channel streaming for UI progress | Emits streaming log lines for TUI/GUI display without corrupting trajectory determinism. |
| `TASK-075` | Read-Only TUI over Event Bus | Post-M1b (Client) | **2** · Easy | Event bus terminal user interface | Read-only TUI surface for headless engine monitoring (G5 gap resolution). |
| `TASK-071` | SWE-bench Manifest & Canary at Scale | M4 | **3** · Medium | Pins SWE-bench Verified & Pro task manifests | Screens tasks bidirectionally with validity canary, closing gap G1. |
| `TASK-072` | SWE-bench A/A Floor Run | M4 | **4** · Hard | Derives SWE-bench-specific discordance & N | Characterizes real benchmark noise floor, closing gap G1. |
| `TASK-073` | Paired Lift Run (Bare-Model vs AETHER) | M4 | **4** · Hard | Statistical lift comparison on SWE-bench | Paired McNemar evaluation against baseline, closing gap G1. |
| `TASK-074` | Publication Run on SEALED | M4 | **3** · Medium | Evaluates SEALED split per `measurement.md` §6 | Satisfies all 7 publication criteria for leaderboard claims (G1). |
| `TASK-015b` | OpenHands Arm via Evaluator | M4 | **5** · Very Hard | Runs third-party harness through our TCB evaluator | Enables direct apples-to-apples competitor claim (G1). |

---

### Complexity Distribution

* **Very Easy — 1 (7 tasks)**: `TASK-000`, `TASK-013`, `TASK-021`, `TASK-046`, `TASK-049b`, `TASK-050`, `TASK-051` — mechanical or single-concept work with no concurrency, security, or algorithmic surface.
* **Easy — 2 (18 tasks)**: `TASK-001`, `TASK-004`, `TASK-010`, `TASK-026`, `TASK-037`, `TASK-038`, `TASK-039`, `TASK-040`, `TASK-041`, `TASK-043`, `TASK-044`, `TASK-052`, `TASK-058`, `TASK-061`, `TASK-063`, `TASK-069`, `TASK-070`, `TASK-075` — contained, well-specified I/O or data modeling with low risk.
* **Medium — 3 (26 tasks)**: `TASK-002`, `TASK-005`, `TASK-006`, `TASK-011`, `TASK-017`, `TASK-018`, `TASK-024`, `TASK-025`, `TASK-032`, `TASK-033`, `TASK-036`, `TASK-042`, `TASK-045`, `TASK-048`, `TASK-049`, `TASK-053`, `TASK-054`, `TASK-055`, `TASK-057`, `TASK-062`, `TASK-064`, `TASK-065`, `TASK-066`, `TASK-068`, `TASK-071`, `TASK-074` — real integration surface or a non-trivial algorithm, several constraints to reconcile.
* **Hard — 4 (16 tasks)**: `TASK-003`, `TASK-014`, `TASK-015`, `TASK-019`, `TASK-020`, `TASK-022`, `TASK-023`, `TASK-030a`, `TASK-031`/`TASK-056`, `TASK-034`, `TASK-035`, `TASK-059`, `TASK-060`, `TASK-067`, `TASK-072`, `TASK-073` — TCB-critical or concurrency/security-sensitive, many interacting invariants.
* **Very Hard — 5 (5 tasks)**: `TASK-012`, `TASK-015b`, `TASK-016`, `TASK-030b`, `A/A Floor Run` — specialist domain knowledge (applied statistics, container security, cross-harness evaluation, adversarial red-teaming), largest blast radius if wrong, little or no reference implementation to draw on.

**Counts are of distinct task ids in this file.** `TASK-031` and `TASK-056` are one task listed under two ids during the relocation and are counted once.

**Revised against code, 2026-08-07**: `TASK-018` (4→3), `TASK-014` (3→4), `TASK-015`/Sprint-3 row (5→4) — see each row's *(rev.)* rationale for the code evidence (file paths, LOC, and what shipped vs. what the original rationale assumed).

---

## Next Steps & Future Roadmap (Post-Sprint 5)

Sprints 1 through 5 take the AETHER codebase from foundation to **Milestone M1b**, establishing the pure domain, wire-serializable ports, walking skeleton, instrument restoration, and the modular capability layer. 

As mandated by [ADR-0009](../decisions/0009-gates-are-the-schedule.md) and [`sprints/README.md`](./sprints/README.md), tasks beyond Sprint 5 are deliberately unsized and unscheduled until the **Sprint 4 A/A Floor** produces exact per-task wall-clock metrics. 

Once Sprint 5 completes and the floor wall-clock metrics are established, the team will plan the next development phases as follows:

### Phase 1: Sprint 6 & Milestone M2 (Engine Efficiency & Ablation Cadence — M2-eng & M2-abl)
- **Sprint 6 Planning**: Size and execute Sprint 6 starting with `TASK-032` (Per-Node Digest Memoization) and deploying `TASK-006`'s cassette replay engine to make ablation runs deterministic and fast (<50 ms per turn).
- **M2 Ablation Suite**: Execute formal statistical ablations for prompt prefix stability (`TASK-056`), dialogue context compaction (`TASK-024`), and the Architect/Editor dual-model seam (`TASK-025`).

### Phase 2: Milestone M3 (Advanced DAG Branching, Fan-Out & Statistical Admission)
- **Graph & Lease Concurrency**: Implement Best-of-N fan-out (`TASK-035`), cache sequencing (`TASK-033`), and child leases (`TASK-034`).
- **Candidate Selection & Invariants**: Land `TASK-067` (Candidate Ranker) enforcing type-level `rank()` vs `admit()` separation to satisfy invariant **I9**.
- **Family Gatekeeper**: Enforce statistical admission through the pre-registered family gatekeeper (`TASK-012`).

### Phase 3: Milestone M4 (Benchmark Delivery & Leaderboard Validation — Resolving Gap G1)
- **Manifest Scale & Canary**: Build, pin, and screen real SWE-bench Verified and Pro manifests with the bidirectional validity canary (`TASK-071`, `TASK-036`).
- **SWE-bench Noise Floor**: Take the SWE-bench-specific A/A variance floor (`TASK-072`) to derive suite-specific discordance rates ($p_{01}, p_{10}$) and derived sample sizes $N$.
- **Comparative Lift & Competitor Claim**: Run paired lift evaluations comparing bare-model baseline vs AETHER (`TASK-073`) and execute the OpenHands arm through our TCB evaluator (`TASK-015b`).
- **Publication & Telemetry**: Execute the publication run on the SEALED split (`TASK-074`) satisfying all 7 requirements of `measurement.md` §6, backed by localization sources (`TASK-064`, `TASK-065`) and the read-only TUI (`TASK-075`).

### Phase 4: Milestone M5 (Meta-Loop & Self-Redesign — Resolving Gap G6)
- **Evolution Package**: Activate `src/aether/evolution/` under strict TCB isolation, implementing subagent capability attenuation (ADR-0017) and topology self-redesign mechanisms (ADR-0006, ADR-0014).