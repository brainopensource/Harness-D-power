# AETHER Full Documentation — Part 1: Core Architecture, Invariants & System Status

> **Original Source Documents:** [`AGENTS.md`](../../AGENTS.md), [`docs/spec.md`](../spec.md), [`docs/vision.md`](../vision.md), [`docs/STATUS.md`](../STATUS.md), [`docs/README.md`](../README.md).  
> **Purpose:** This document provides a complete, grounded, and condensed summary of AETHER's core architecture, system invariants, security models, import lattice rules, and current operational status.

---

## 1. System Vision & Core Metrics

**AETHER** is a state-of-the-art (SOTA) autonomous coding harness built around LLMs. It surrounds language models with tools, workspaces, memory, capability security, and statistical feedback loops. 

### The Dual-Metric Doctrine
AETHER always measures **two numbers together**:
1. **Absolute Resolve Rate**: Pass@1 percentage on benchmark suites (SWE-bench Pro and Verified).
2. **Harness Lift ($\Delta$)**: The exact resolve rate delta between a bare unassisted model call and the same model running inside AETHER on identical tasks.

> [!IMPORTANT]
> **Normative Rule**: An absolute resolve rate is **never published without its harness lift** ([ADR-0004](../decisions/0004-benchmark-targets.md)). Lift is the committed engineering target; absolute resolve rates vary by base model capability.

---

## 2. Core Architectural Invariants (I1 – I11)

Every invariant in AETHER is mechanically enforced by automated tools in CI (`import-linter`, `pyright --strict`, custom AST checkers). An unenforced rule is considered invalid.

| # | Invariant | Description | Enforced By |
| :--- | :--- | :--- | :--- |
| **I1** | **Pure Domain** | `src/aether/domain/` models are pure Pydantic/dataclass structures with zero I/O, DB, filesystem, or HTTP dependencies. | `import-linter` (`domain-is-pure`) |
| **I2** | **Typed Ports** | All system I/O boundaries cross an explicit `typing.Protocol` interface in `src/aether/ports/`. | `pyright --strict` |
| **I3** | **Wire-Serializable Ports** | Every port method is `async`. Only serializable payloads cross boundaries—no live file handles, generators, callables, or `Path` objects. | Reflection test suite over all ports |
| **I4** | **Adapter Substitutability** | Every concrete adapter under `src/aether/adapters/` must pass the exact same parametrized conformance test suite in CI. | Shared conformance test matrix |
| **I5** | **Single Dispatch Choke Point** | Every effect (file read/write, shell execution, model call, container test) passes through `kernel/dispatch.py`. Capability grants are verified at point-of-effect, not authorization time. | Architectural AST search test |
| **I6** | **Frozen Extension Resolution** | Tools, adapters, and skills register once at composition time and freeze. Runtime registration raises an error. | Composition freeze test |
| **I7** | **Generator $\ne$ Evaluator** | The agent writing code can never modify the tests grading it (`tests_unmodified` hard gate). | `tests_unmodified` hard gate |
| **I8** | **Immutable TCB** | Kernel, measurement evaluator, gates, statistics, benchmark task manifests, and CI workflows cannot be modified by agent or meta-loop. | `import-linter` (`tcb-isolation`) + CI hash check |
| **I9** | **Hard Gates Admit; Proxies Rank** | Learned proxy scorers may order candidate patches but can never admit them or override a gate failure. | Type-level `rank()` vs `admit()` protocol split |
| **I10** | **Prompt Cache is Architecture** | Context prefixes use 5 fixed layers (L1–L5) with explicit `cache_breakpoint` pins; harness-side prefix stability is tracked. | CI floor on byte-identical prefix rate |
| **I11** | **Taint Cannot Acquire Authority** | Context spans carry provenance labels (`trusted-system`, `operator`, `agent`, `untrusted-external`, `untrusted-derived`). Untrusted content cannot grant capability. | Pinned injection corpus in CI ([ADR-0015](../decisions/0015-taintgate-provenance-model.md)) |

---

## 3. Structural Package Hierarchy & Import Lattice

Dependencies in AETHER flow strictly downward. The components that judge execution (`kernel/`, `measurement/`) can **never import from the things being judged** (`agency/`, `workflow/`).

### Directory Layout (`src/aether/`)
```
src/aether/
├── domain/          # Pure Pydantic models — zero I/O (I1)
├── ports/           # Async, wire-serializable Protocols (I2, I3)
├── kernel/          # Trusted Computing Base (TCB) — dispatch, bus, governor, policy (I5, I8)
├── agency/          # Agent execution loop, prompt assemblers, compactor, roles
├── adapters/        # Concrete implementations of wire ports
├── measurement/     # TCB — evaluator, hard gates, statistics, runner, harvester
├── workflow/        # Declarative WorkflowStep DAG + schema/validator/executor (ADR-0013, ADR-0014)
├── evolution/       # Offline optimization — strictly isolated (ADR-0006)
├── engine.py        # Headless API — single surface for CLI/TUI/GUI clients
└── composition.py   # Explicit dependency wiring (zero magic DI containers)
```

### Import Lattice Hierarchy
```
engine  >  (agency, workflow)  >  kernel  >  adapters  >  ports  >  domain
```

* **TCB Isolation Rule**: `kernel/` and `measurement/` may not import `agency/` or `workflow/`.
* **Offline Isolation Rule**: `evolution/` imports no higher than `ports/` and is imported by nothing.
* **Lattice Order Update**: `workflow` sits above `agency` in `.importlinter` to allow node roles to declaratively import capability protocols ([`proposal_abstraction_and_harness_composition.md`](../fixes/proposal_abstraction_and_harness_composition.md)).

---

## 4. Capability Authorization (CAR) & Taint Model

AETHER enforces a capability-security authorization model:

```
authorize → verify grant → acquire budget lease → dispatch → release lease
```

1. **Point-of-Effect Verification**: Capability verification occurs in `kernel/dispatch.py` *immediately before* executing the side effect, preventing stale grants or parameter tampering.
2. **Taint Gate Provenance Spans**:
   * Repository files, issue bodies, terminal stdout, web search, and tool results are labeled `untrusted-external` at birth.
   * Prompts or completions consuming any untrusted span produce `untrusted-derived` outputs.
   * **Policy Rule**: Any tool execution request that widens capability fails closed if any input span is `untrusted-external` or `untrusted-derived`.

---

## 5. Hexagonal Ports & Wire Serializability

AETHER defines **9 core wire protocols** across 8 boundaries in `src/aether/ports/`:
1. `ModelProvider`: LLM completion and streaming requests.
2. `Workspace`: Codebase workspace access and file operations.
3. `WorktreeManager`: Isolated Git branch and worktree lifecycle management.
4. `ToolRegistry`: Tool schema registration and capability execution.
5. `PolicyEngine` (TCB): Security authorization and grant verification.
6. `ResourceGovernor`: Token and USD budget reservation and tracking.
7. `TrajectoryStore`: Durable append-only event log persistence.
8. `Evaluator` (TCB): Isolated container test execution and gate scoring.
9. `Indexer`: Symbol table and AST code graph retrieval.

> [!NOTE]
> **TCB Port Residency**: Concrete implementations of TCB ports (`PolicyEngine`, `Evaluator`) live directly inside TCB directories (`kernel/`, `measurement/`), **never inside `adapters/`**.

---

## 6. Current Operational Status (As-Built)

As verified in [`docs/STATUS.md`](../STATUS.md):
* **Sprints Completed**: Sprints 1, 2, 3, and 3.5 are fully implemented.
* **Walking Skeleton & Bounded Repair**: Core `ModelNode`, `EvaluateStep`, `RepairStep` ($k \le 3$), and `TracebackTrimmer` are operational.
* **Local Verification**: Verified locally using Ollama (`qwen2.5-coder:32b`) and Podman container sandboxes.
* **CI Quality Gates**: 100% green on `ruff format`, `ruff check`, `pyright --strict`, `lint-imports`, and pytest suites.
* **Pending Action**: Sprint 4 will execute the A/A noise floor run to unlock public benchmark claim publishing per [ADR-0002](../decisions/0002-no-number-before-the-floor.md).

---

## 7. Codebase & Tech Stack Conventions

* **Python Runtime**: `>=3.13,<3.14`.
* **Package Manager**: `uv` (`uv.lock` committed, `uv sync --frozen` in CI).
* **Async I/O**: strictly stdlib `asyncio` (`TaskGroup`, `asyncio.timeout`). **No `anyio`, no `trio`**.
* **Linting/Formatting**: `ruff format`, `ruff check --fix`, `pyright --strict`, `lint-imports` (via import-linter) are strictly enforced in CI.

---

## 8. Documentation Constraints

* **15,000-Word Budget**: Normative documents are subject to a strict 15,000-word ceiling enforced by `scripts/docs_budget.py` in CI.
* **Frontmatter Requirement**: Every document must declare a `status:` frontmatter (`normative`, `rationale`, or `historical`). Documents lacking this will cause CI to fail.
* **Code Wins**: Documentation navigates, but the code in `src/aether/ports/` acts as the single source of truth for contracts.
