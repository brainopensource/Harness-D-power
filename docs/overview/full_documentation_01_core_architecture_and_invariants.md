---
status: historical
retrieval: excluded
updated: 2026-08-07
superseded: 2026-08-07
---

# AETHER Full Documentation — Part 1: Core Architecture, Invariants & System Status

> [!WARNING]
> **Stale snapshot. Not authoritative, and not maintained.**
>
> This folder is a hand-written re-rendering of documents that already have an
> authoritative home, which `README.md` names as the one thing this tree forbids:
> *"if you find the same thing stated in two places, the second one is the bug."*
> It has already drifted — it cites `docs/development/`, `docs/fixes/` and
> `docs/future_improvements/`, none of which exist, and Part 2 covers only ADRs
> 0001–0018 of 21.
>
> For anything binding read [`spec.md`](../spec.md), [`measurement.md`](../measurement.md),
> [`PHASE-0-LOCK.md`](../PHASE-0-LOCK.md), [`decisions/`](../decisions/README.md) and
> [`STATUS.md`](../STATUS.md). Tagged `retrieval: excluded` so no retrieval surfaces it
> and the link gate does not check it; see `TASK-084`.


> **Original Source Documents:** [`AGENTS.md`](../../AGENTS.md), [`docs/spec.md`](../spec.md), [`docs/vision.md`](../vision.md), [`docs/STATUS.md`](../STATUS.md), [`docs/README.md`](../README.md), [`docs/development/core_skeletons_and_protocols.md`](../development/core_skeletons_and_protocols.md), [`docs/development/schemas_and_contracts.md`](../development/schemas_and_contracts.md), [`docs/development/system_workflows_and_diagrams.md`](../development/system_workflows_and_diagrams.md), [`docs/development/tech_stack_and_infra.md`](../development/tech_stack_and_infra.md), [`docs/development/generated/aether_event_catalog.md`](../development/generated/aether_event_catalog.md), [`docs/concepts/rewrite_v300_project_vision.md`](../concepts/rewrite_v300_project_vision.md), [`docs/concepts/rewrite_v300_context.md`](../concepts/rewrite_v300_context.md), and [`docs/workflows/`](../workflows/).

---

## 1. Executive Summary & System Vision

**AETHER** (Autonomous Engineering & Topology Harness for Evaluated Repair) is a state-of-the-art (SOTA) autonomous coding harness built on capability security, microkernel dispatch, declarative DAG topology execution, and rigorous, falsifiable evaluation gates.

### 1.1 The Dual-Metric Doctrine
AETHER rejects vanity metrics and uncalibrated benchmark claims. Every evaluation report MUST publish two numbers simultaneously:

1. **Absolute Resolve Rate**: Pass@1 percentage on benchmark suites (SWE-bench Verified and SWE-bench Pro).
2. **Harness Lift ($\Delta$)**: The exact resolve rate delta between an unassisted bare-model call and the same model running inside AETHER on identical tasks:
   $$\Delta = \text{Pass@1}_{\text{AETHER}} - \text{Pass@1}_{\text{BareModel}}$$

> [!IMPORTANT]
> **Normative Rule ([ADR-0004](../decisions/0004-benchmark-targets.md))**: An absolute resolve rate is **never published without its harness lift**. Lift is the committed engineering target ($\Delta \ge +10$ percentage points); absolute resolve rates fluctuate based on base model capability.

---

## 2. Core Architectural Invariants (I1 – I11)

Every architectural rule in AETHER is mechanically enforced in CI via automated tooling (`import-linter`, `pyright --strict`, `pytest`, custom AST checkers). An unenforced rule is considered a wish, not an invariant.

```mermaid
graph TD
    Sub[Subagent / Agent Logic] -->|1. Effect Request| Policy[PolicyEngine (TCB)]
    Policy -->|2. Verify Grant & Taint| Choke[kernel/dispatch.py (Choke Point)]
    Choke -->|3. Acquire Lease| Gov[ResourceGovernor]
    Gov -->|4. Execute Side Effect| Adapter[Port Adapter]
    Adapter -->|5. Audit Log| Bus[EventBus & TrajectoryStore]
```

### Invariant Catalog Table

| # | Invariant | Description & Architectural Requirement | Mechanical Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **I1** | **Pure Domain** | `src/aether/domain/` models are pure Pydantic/dataclass structures with zero I/O, DB, filesystem, or HTTP dependencies. | `import-linter` contract (`domain-is-pure`) |
| **I2** | **Typed Ports** | All system I/O boundaries cross an explicit `typing.Protocol` interface defined in `src/aether/ports/`. | `pyright --strict` type checking |
| **I3** | **Wire-Serializable Ports** | Every port method is `async`. Only serializable payloads cross boundaries—no live file handles, callables, generators, `Path` objects, or `dict[str, Any]`. | Reflection test suite over all ports |
| **I4** | **Adapter Substitutability** | Every concrete adapter under `src/aether/adapters/` must pass the exact same parametrized conformance test suite in CI. | Shared conformance test matrix (`tests/conformance/`) |
| **I5** | **Single Dispatch Choke Point** | All side-effects pass through `src/aether/kernel/dispatch.py`. Verification occurs at **point-of-effect**, not authorization time. | AST search test proving zero adapter bypass |
| **I6** | **Frozen Extension Resolution** | Tools, adapters, and skills register once at composition time and freeze. Runtime discovery or filesystem scanning is forbidden. | Composition freeze test |
| **I7** | **Generator $\ne$ Evaluator** | The agent writing code can never modify the tests grading it (`tests_unmodified` hard gate). | `tests_unmodified` hard gate in `measurement/` |
| **I8** | **Immutable TCB** | Kernel, measurement evaluator, gates, statistics, task manifests, and CI workflows cannot be modified by agents or meta-loops. | `import-linter` (`tcb-isolation`) + CI path hash checks |
| **I9** | **Hard Gates Admit; Proxies Rank** | Learned proxy rankers may order candidate patches but can never admit them or override a gate failure. | Type-level `rank()` vs `admit()` protocol separation |
| **I10** | **Prompt Cache is Architecture** | Context prefixes use 5 fixed layers (L1–L5) with explicit `cache_breakpoint` pins; harness-side prefix stability is tracked. | CI floor on byte-identical prefix stability over replay |
| **I11** | **Taint Cannot Acquire Authority** | Context spans carry provenance labels (`trusted-system`, `operator`, `agent`, `untrusted-external`, `untrusted-derived`). Untrusted content fails closed on capability requests. | Pinned adversarial injection corpus in CI ([ADR-0015](../decisions/0015-taintgate-provenance-model.md)) |

---

## 3. Package Hierarchy & Import Lattice Rules

Dependencies in AETHER flow strictly downward. Components that judge execution (`kernel/`, `measurement/`) can **never import from the components being judged** (`agency/`, `workflow/`).

### 3.1 Directory Layout (`src/aether/`)

```
src/aether/
├── domain/          # Pure Pydantic domain models — zero I/O dependencies (I1)
├── ports/           # Async, wire-serializable Protocols (I2, I3)
├── kernel/          # Trusted Computing Base (TCB) — dispatch, bus, governor, policy (I5, I8)
├── agency/          # Agent execution loop, prompt assemblers, context compactor, roles
├── adapters/        # Concrete implementations of wire ports
├── measurement/     # TCB — evaluator, hard gates, statistics, runner, harvester (I7, I8)
├── workflow/        # Declarative WorkflowStep DAG + schema/validator/executor (ADR-0013, ADR-0014)
├── evolution/       # Offline optimization — strictly isolated (ADR-0006)
├── engine.py        # Headless API — single surface for CLI/TUI/GUI clients
└── composition.py   # Explicit dependency wiring (zero magic DI containers)
```

### 3.2 Import Lattice Hierarchy

```
engine  >  workflow  >  agency  >  kernel  >  adapters  >  ports  >  domain
```

* **TCB Isolation Contract**: `src/aether/kernel/` and `src/aether/measurement/` may not import `agency/` or `workflow/`.
* **Offline Isolation Contract**: `src/aether/evolution/` imports no higher than `ports/` and is imported by nothing in the runtime path.
* **Lattice Order Rule ([ADR-0018](../decisions/0018-agency-below-workflow.md))**: `workflow` sits above `agency` in `.importlinter` to allow workflow nodes to declaratively instantiate role capabilities without breaking import contracts.

---

## 4. Capability Authorization (CAR Model) & Taint Security

AETHER implements a capability-security authorization architecture to safeguard against prompt injection, unauthorized side-effects, and resource exhaustion.

### 4.1 Dispatch Flow & Verification Lifecycle
Every side-effect follows a strict choke-point pipeline:

1. **Authorization Request**: Node requests an `EffectRequest` through `PolicyEngine.authorize()`.
2. **Grant Verification**: `kernel/dispatch.py` re-verifies the capability grant immediately before executing the effect (eliminating TOCTOU timing vulnerabilities).
3. **Lease Acquisition**: `ResourceGovernor` carves budget allocations (tokens/USD) into an active `Lease`.
4. **Adapter Dispatch**: The underlying adapter executes the physical I/O operation.
5. **Lease Release**: Realized consumption is debited against actuals, and unused budget is returned.

### 4.2 Taint Gate Provenance Model ([ADR-0015](../decisions/0015-taintgate-provenance-model.md))

All data ingested into the system is wrapped in `TaintSpan` metadata:

* `trusted-system`: Hardcoded system prompts and TCB invariants.
* `operator`: Direct input from human operator.
* `agent`: Content generated by LLM completion.
* `untrusted-external`: Repository files, issue bodies, terminal stdout, web search results, and tool outputs.
* `untrusted-derived`: Any prompt snippet or completion derived from an untrusted span.

> **Security Rule**: Any capability request that widens authority (e.g., file writes, shell execution, network access) **fails closed** if any contributing input span carries `untrusted-external` or `untrusted-derived` taint.

---

## 5. Hexagonal Ports & Wire Serializability

AETHER defines **9 core wire protocols** across 8 boundaries in `src/aether/ports/`:

```python
# Protocol Interface Requirements (I2, I3)
# 1. Every method MUST be async.
# 2. Payload types MUST be Pydantic models or NewType primitive wrappers.
# 3. No live file handles, generators, callables, or Path objects in public signatures.
```

1. **`ModelProvider`**: Streaming/non-streaming LLM completions, SSE delta parsing, token usage metrics.
2. **`Workspace`**: Codebase file reads/writes, patch applications, and diff generation over relative paths.
3. **`WorktreeManager`**: Isolated Git branch and worktree creation, destruction, and lifecycle tracking.
4. **`ToolRegistry`**: Tool schema registration and capability execution.
5. **`PolicyEngine` (TCB)**: Security authorization, grant issuance, and policy decision evaluation.
6. **`ResourceGovernor`**: Token and USD budget reservations, atomic lease commits, and ledger tracking.
7. **`TrajectoryStore`**: Durable append-only event log storage and sequence replay.
8. **`Evaluator` (TCB)**: Containerized test command execution and tri-state `GateReport` scoring.
9. **`Indexer`**: Symbol table, AST node search, and code graph retrieval.

> [!NOTE]
> **TCB Port Residency**: Concrete implementations of TCB ports (`PolicyEngine`, `Evaluator`) reside inside TCB paths (`src/aether/kernel/`, `src/aether/measurement/`), **never under `src/aether/adapters/`**.

---

## 6. Event Bus & Event Catalog

The event bus (`src/aether/kernel/bus.py`) provides append-only, typed event distribution across client interfaces and persistent stores.

### Core Event Catalog
* `RunStarted`: Run initialization with configuration hash and task manifest payload.
* `StepStarted` / `StepCompleted`: Workflow step execution lifecycle.
* `ModelCallStarted` / `ModelCallCompleted`: Model invocation with token usage and latency.
* `ToolExecutionStarted` / `ToolExecutionCompleted`: Tool execution with taint labels.
* `RepairIterationStarted`: Repair loop iteration trigger with attempt index.
* `EvaluationCompleted`: Evaluator verdict containing tri-state `GateReport`.
* `RunCompleted`: Terminal run outcome with total usage and final resolve status.

---

## 7. Current Operational Status (As-Built)

As recorded in [`docs/STATUS.md`](../STATUS.md):

* **Sprints Completed**: Sprints 1, 2, 3, and 3.5 are 100% complete.
* **Walking Skeleton & Repair**: 4-node linear graph (`retrieve → generate → apply → evaluate`) and bounded repair loop ($k \le 3$) operational.
* **Sandbox Perimeter**: Isolated rootless Podman / Docker fallback evaluation container verified green (`test_b3_canary.py` 7/7 passing).
* **CI Quality Gates**: 100% green on `ruff format`, `ruff check`, `pyright --strict`, `lint-imports`, and `pytest`.
* **Recorded Deviations**:
  - Uncontained tool execution on host (containerized at M2).
  - I9 type separation (`rank()` vs `admit()`) pending `TASK-067`.
  - `aether.evolution` import contract target vacuous until Milestone M5.

---

## 8. Codebase & Tech Stack Rules

* **Python Runtime**: `>=3.13,<3.14`.
* **Package Manager**: `uv` (`uv.lock` committed, `uv sync --frozen` in CI).
* **Async I/O**: stdlib `asyncio` (`TaskGroup`, `asyncio.timeout`). **No `anyio`, no `trio`**.
* **Formatting & Types**: `ruff format`, `ruff check --fix`, `pyright --strict`, `lint-imports` strictly enforced in CI.
* **Documentation Rules**: Frontmatter `status:` required (`normative`, `rationale`, or `historical`). 15,000-word ceiling on normative files (`scripts/docs_budget.py`).
