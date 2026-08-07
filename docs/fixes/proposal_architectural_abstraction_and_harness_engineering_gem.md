---
status: rationale
updated: 2026-08-07
---

# Complementary Specification: Front-End Engine Integration & Polyglot Wire Contracts

> [!NOTE]
> **Source of Truth Notice**: This document is a **complementary specification** to the primary backend architecture proposal: [`proposal_abstraction_and_harness_composition.md`](./proposal_abstraction_and_harness_composition.md). All backend node refactoring (`ModelNode`), role catalogs (`RoleSpec`), capability protocols (`ContextSource`, `Inference`, `OutputParser`), import lattice updates, and topology fragments are governed by `proposal_abstraction_and_harness_composition.md`.

---

## Executive Summary

This document specifies the complementary frontend and polyglot integration contracts that build upon the refactored AETHER backend core:

1. **Headless Engine & Frontend Integration**: How the frontend (Terminal CLI, Textual TUI, Web GUI) inspects, parameterizes, and drives runs using the unified `RunConfig` (`src/aether/domain/config.py`, TASK-058 — not yet built) domain model and append-only event stream.
2. **Polyglot & Out-of-Process Wire Protocol Contracts**: How out-of-process sidecars written in **Rust** (Tree-sitter AST symbol resolution) or **Go** (Podman container sandbox orchestration) interface with AETHER's wire ports via Invariant I3 without modifying backend kernel logic.

---

## 1. Config-Driven Frontend Orchestration (`RunConfig` & Event Stream)

### 1.1 Declarative Schema & UI Generation

Following the introduction of the frozen `RunConfig` domain model ([`proposal_abstraction_and_harness_composition.md` §3.2](./proposal_abstraction_and_harness_composition.md#32-the-asymmetry-to-fix)), the frontend UI no longer handles loose keyword arguments. 

```
+-----------------------------------------------------------------------------------+
|                           UNIFIED FRONTEND ENGINE INTERFACE                       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  FRONTEND SURFACES:                                                               |
|  - Terminal Ink CLI (apps/cli)   - Tauri/React Flow GUI (apps/desktop)            |
|                                                                                   |
|                                         |                                         |
|                                         v  (RunConfig JSON Payload)               |
|                                                                                   |
|  HEADLESS ENGINE API:                                                             |
|  `engine.run(config: RunConfig)`                                                  |
|                                                                                   |
|                                         |                                         |
|                                         v  (Append-Only Event Stream)             |
|                                                                                   |
|  EVENT STREAM SUBSCRIBERS:                                                        |
|  - Live Log View      - Taint Audit Panel    - Budget Meter    - Diff Reviewer    |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

1. **Auto-Generated Forms**: The frontend renders configuration forms (node parameters, budget ceilings, model endpoint routes) directly from `RunConfig.model_json_schema()`.
2. **Reproducible Run Hashes**: The run configuration is content-addressed as `sha256(RunConfig)`, ensuring 100% exact reproduction across CLI, TUI, and GUI runs.

### 1.2 Interactive Canvas & Subgraph Visualizer (`apps/desktop`)

With the addition of Topology Fragments (`schema_version: 1.1.0`), the React Flow canvas (`xyflow`) renders two display states:

* **Collapsed View**: Composite steps (e.g. `use: edit_and_judge`) render as a single node with an indicator badge.
* **Expanded Subgraph View**: Users click to expand the composite fragment, revealing its internal sub-nodes (`apply -> evaluate -> repair`) and child-lease budget limits.

---

## 2. Polyglot Scaling & Wire Protocol Contracts (Rust / Go Integration)

### 2.1 The Relocatable Port Invariant (Invariant I3)

Invariant I3 mandates that **no live Python object, `Path`, open file handle, or generator crosses a port boundary**. Every payload is a pure Pydantic model serializable to JSON.

Because [`Dispatcher.dispatch()`](../../src/aether/kernel/dispatch.py#L83) passes `EffectRequest.descriptor` and returns `EffectOutcome.result_json` as JSON strings, any Python port adapter can be replaced by an out-of-process **Rust** or **Go** sidecar with zero changes to callers or kernel code.

```
+-----------------------------------------------------------------------------------+
|                             PYTHON KERNEL & WORKFLOW ENGINE                       |
|                             (aether.kernel / aether.workflow)                     |
+-----------------------------------------------------------------------------------+
                                          |
             JSON-RPC / Unix Socket Wire Protocol Boundary (Invariant I3)
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
        v                                 v                                 v
+-----------------------+     +-----------------------+     +-----------------------+
|   Python Adapter      |     |     Rust Adapter      |     |      Go Adapter       |
| (OpenAI / Subprocess) |     | (Tree-sitter AST)     |     | (Container Sandbox)   |
+-----------------------+     +-----------------------+     +-----------------------+
```

### 2.2 Wire Schema Specifications

#### Rust AST & Symbol Indexer Interface (`ports/indexer.py`)
```json
{
  "jsonrpc": "2.0",
  "method": "indexer.search_symbols",
  "params": {
    "worktree_path": "repo/src",
    "query": "def parse_diff",
    "max_results": 5
  },
  "id": 1
}
```

#### Go Container Sandbox Interface (`domain/sandbox.py` — **not** `ports/evaluator.py`)

> [!WARNING]
> **Correction (2026-08-07).** An earlier revision put `evaluator.evaluate` behind this wire
> protocol. That is not admissible: [`spec.md` §4](../spec.md#4-ports)'s TCB port-residency rule
> requires the concrete `Evaluator` to live in `measurement/`, never `adapters/`, because that is
> what makes `import-linter`'s `aether-tcb-isolation` contract *select* it — and selecting it is
> how I7 is enforced. Moving the judge out of process moves it out of the contract.
>
> The extractable component here is the **`SandboxRunner`** (`domain/sandbox.py`,
> `adapters/sandbox/podman.py`), which the evaluator calls. `RealEvaluator` stays in
> `measurement/` and keeps deciding `PASSED`/`FAILED`/`NONE` in-process; only container
> orchestration crosses the wire. The JSON below is corrected accordingly.
```json
{
  "jsonrpc": "2.0",
  "method": "sandbox.run",
  "params": {
    "container_spec": {
      "image_digest": "sha256:7c2c2467...",
      "network": "none",
      "read_only_root": true
    },
    "test_command": "pytest tests/unit/test_core.py"
  },
  "id": 2
}
```

### 2.3 Sidecar Adoption Triggers (ADR-0001 Alignment)

Per [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md), compiled sidecars are extracted **only when measured performance timers cross declared thresholds**:
* **Rust `SymbolIndexer`**: Extracted if AST parsing timer RT-1/RT-2 crosses threshold on a 1M-LOC repository.
* **Go `WorkspaceManager`**: Extracted if worktree creation timer RT-3 crosses threshold under Best-of-N fan-out ($N \ge 5$).
