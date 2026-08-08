---
status: rationale
updated: 2026-08-06
---

# Sprint 01 Plan — Foundations & Instrument Unblocking

* **Goal**: Land the TCB path migration, core pure domain models, wire-serializable ports with mock adapters and the conformance meta-suite, the manifest-driven repository cache (B1), and the typed tri-state gate (B4).
* **Target Milestone**: [M0](../milestones.md#milestone-m0--pure-domain--wire-protocols) · [B1](../milestones.md#blocker-b1--manifest-driven-upstream-repository-cache) · [B2a](../milestones.md#blocker-b2--local-openai-compatible-endpoint) · [B4](../milestones.md#blocker-b4--typed-instrument-error-handling)
* **Tripwire Window**: 5 Business Days (2026-08-06 to 2026-08-12)
* **Position in the plan**: [`sprints/README.md`](README.md)

> **This sprint runs two tracks in parallel.** Serially its tripwires sum to ~7 days against a 5-day window. **Track 1 — architecture**: Tasks 1, 2, 4, 5 (M0, ~3d). **Track 2 — instrument**: Tasks 3 and 6 (B1 + B4, ~3d), which depend on nothing in Track 1. They share only Task 0, which blocks both. One developer across both tracks trips the [ADR-0009](../../decisions/0009-gates-are-the-schedule.md) tripwire on day one — that is the signal to staff the second track or re-scope, never to compress the estimate.

> **Task 0 is blocking and lands first.** It is not a formality: until it merges, [ADR-0006](../../decisions/0006-tcb-boundary-and-meta-loop-authority.md) is enforced by nothing while CI reports green. Every other task in this sprint creates `src/aether/` files, and each one that lands ahead of Task 0 widens that window.

---

## Sprint Backlog Items

### Task 0: Migrate TCB Path Constants (`TASK-000`) — **BLOCKING, FIRST PR**
* **Target Seam**: `.importlinter`, `.github/workflows/ci.yml`, `tests/unit/test_path_constant_drift.py`
* **Specification Pointer**: [ADR-0006 "The trap this ADR must not fall into"](../../decisions/0006-tcb-boundary-and-meta-loop-authority.md), [`milestones.md` M0 Exit Gate 0](../milestones.md#milestone-m0--pure-domain--wire-protocols)
* **Acceptance Criteria**:
  1. `.importlinter` `root_package` and the `tcb-isolation` contract name `src/aether/…`; CI `TCB_PATHS` likewise. Lands **in the same change as the first `src/aether/` file**.
  2. **Negative acceptance**: `tests/unit/test_path_constant_drift.py` demonstrably **fails** when the constants select only `src/sagiha/` paths. A contract that selects no file forbids nothing and passes green — that is the failure mode being closed, so passing is not evidence.
  3. `import-linter` reports every contract as matching at least one module; zero vacuous contracts.

### Task 1: Implement Pure Domain Data Models (`TASK-001`)
* **Target Seam**: `src/aether/domain/`
* **Specification Pointer**: [`spec.md` §2 (I1)](../../spec.md#2-invariants), [AGENTS.md Guideline 2](../../../AGENTS.md)
* **Acceptance Criteria**:
  1. Frozen Pydantic models for tasks, trajectories, budgets/leases, taint spans, gates, and events (`ConfigDict(frozen=True, extra="forbid")`).
  2. `import-linter` contract `domain-is-pure` passes green in CI.
  3. All datetimes are timezone-aware; currency is integer micro-USD (float budget arithmetic is banned by type).

### Task 2: Define Port Protocols With Mock Adapters (`TASK-002`, `TASK-005`, `TASK-006`)
* **Target Seam**: `src/aether/ports/`, `src/aether/adapters/mock/`, `tests/conformance/`
* **Specification Pointer**: [`spec.md` §4](../../spec.md#4-ports), [ADR-0005 rev. 2](../../decisions/0005-eight-ports-adapter-first.md), [`spec.md` §2 (I2, I3)](../../spec.md#2-invariants)
* **Acceptance Criteria**:
  1. Each protocol lands **in the same change as a mock adapter and its conformance test**, with its **first real adapter named and owned** — the [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md) rev. 2 clause. A protocol without a named real adapter does not land this sprint.
  2. The conformance meta-suite is **one parametrized suite, N adapters**, and **fails when a port's parameter list is empty**.
  3. Reflection meta-test passes over every protocol: all methods `async`; no `Path`, file handle, callable, generator, live object, or `dict[str, Any]`; **no `Grant` in any public signature**.
* **Note**: the ratified set is nine protocols on eight boundaries. Landing all nine is permitted *only* under criterion 1; any protocol whose real adapter cannot be named waits rather than shipping as an interface against an imagined implementation.

### Task 3: Build Manifest-Driven Upstream Repository Cache (`TASK-010`)
* **Target Seam**: `src/aether/measurement/repo_cache.py`, `scripts/resolve_swebench_bases.py`
* **Specification Pointer**: [`measurement.md` §2 (B1)](../../measurement.md#2-instrument-blockers), [ADR-0002](../../decisions/0002-no-number-before-the-floor.md)
* **Acceptance Criteria**:
  1. The repository set is **derived from the pinned task manifest**, never hard-coded. Adding a task from a new repo requires no code change. *(SWE-bench Verified spans 12 repos; Pro spans materially more — a cache scoped to 12 defers the primary battlefield by a milestone.)*
  2. Resolves **100% of base commits for the pinned floor-manifest task set** with zero `fatal: invalid reference:` errors.
  3. Cache is **content-addressed and offline-replayable**: a re-run with the network disabled resolves every base commit from cache. *(The previous gate, "zero network errors", was environment luck rather than a capability.)*

### Task 4: Kernel Dispatch & Policy Engine Choke Point (`TASK-003`)
* **Target Seam**: `src/aether/kernel/dispatch.py`, `src/aether/kernel/policy.py`
* **Specification Pointer**: [`spec.md` §5](../../spec.md#5-execution), [`spec.md` §2 (I5, I8)](../../spec.md#2-invariants), [ADR-0006](../../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
* **Acceptance Criteria**:
  1. `authorize → verify grant → acquire lease → dispatch → release`. **`verify` runs immediately before the effect**, not at authorization — arguments change between issuance and use, and a resumed run can carry a stale grant.
  2. Architecture test proves **no bypass path**: no adapter is invoked outside `dispatch.py`.
  3. **The concrete `PolicyEngine` lives in `kernel/`, never `adapters/`** ([`spec.md` §4](../../spec.md#4-ports) residency rule). Put it in `adapters/` and `tcb-isolation` silently stops covering it.
  4. Grants are kernel-internal — **no `Grant` appears in any public port signature**.
* **Why it is in this sprint**: M0 Exit Gate 3 (`tcb-isolation`) needs `kernel/policy` to exist for the contract to select anything, and Task 0's rule is that a contract selecting nothing forbids nothing.

### Task 5: Implement WorkflowStep Node & Socket Types (`TASK-004`)
* **Target Seam**: `src/aether/workflow/step.py`
* **Specification Pointer**: [ADR-0013 (M0)](../../decisions/0013-workflow-dag-phased.md)
* **Acceptance Criteria**:
  1. `WorkflowStep[In, Out]` lands with socket types; steps receive **no adapter handles** — effects reach a dispatch facade injected by the executor, so the choke point is unavoidable by type.
  2. Pyright strict check passes with zero errors.

### Task 6: Typed Tri-State `GateReport` (`TASK-013`) — pulled forward from M2
* **Target Seam**: `src/aether/domain/gate.py`
* **Specification Pointer**: [`measurement.md` §2 (B4)](../../measurement.md#2-instrument-blockers), [`milestones.md` B4](../milestones.md#blocker-b4--typed-instrument-error-handling)
* **Acceptance Criteria**:
  1. `GateStatus` is `PASSED` / `FAILED` / `NONE`, with `instrument_error` populated **iff** `NONE`.
  2. Negative test: a fixture mapping exit-127 to `FAILED` fails the suite.
* **Why here**: B4 is a pure domain type and a **precondition of the A/A floor** ([`roadmap.md`](../roadmap.md)). Left at M2 it would have let instrument errors into the floor's denominator.

---

## Explicitly not in this sprint

**`TASK-021` (the two F1 timers) moved to [Sprint-02](./sprint-02.md).** It was listed here and could not have been built: the worktree timer wraps `TASK-017`'s git adapter and the AST timer wraps a tree-sitter indexer, and neither exists at M0. Its gate is M1a Exit Gate 4, not an M0 gate. [ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md)'s *"two timers land in the first working slice"* means the first **working** slice — M1a, where something runs.

**No adapters beyond mocks.** `TASK-011`/`017`/`018`/`019` land in Sprint-02 with M1a Gate 3. Each is *named* here as the real adapter behind its mock, which is what [ADR-0005](../../decisions/0005-eight-ports-adapter-first.md) rev. 2 requires — naming, not building.

---

## Daily Sprint Definition of Done

1. `ruff check --fix` and `ruff format` pass without errors.
2. `pyright` strict type checking passes with 0 errors.
3. `import-linter` passes **and no contract is vacuous** — every contract selects at least one module.
4. `python scripts/docs_budget.py --max 15000` passes in CI. *(Corrected from `--max 54000`, which matched neither CI nor any recorded decision — CI has run the 15,000 ceiling throughout.)*
5. `python scripts/check_links.py` passes — zero dead relative links.
6. `pytest tests/unit/test_docs_gates.py` passes — both docs gates proven able to fail.
7. Every stub raises. No stub returns a plausible value, and no exception is swallowed into `[]`.
