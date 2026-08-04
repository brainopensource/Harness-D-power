---
title: SOTA Greenfield Autonomous Coding Harness Architecture & Evolution Plan
status: draft
version: 1.0.0
target_benchmark_score: ">80% SWE-bench"
architecture_pattern: Hexagonal / Port-Adapter / Microkernel
tech_stack: Rust Microkernel Core + Go/TS Control Plane & TUI + Python IAO/LLM Sidecar
---

# Greenfield SOTA Autonomous Coding Harness — Architectural Blueprint & Evolution Roadmap

## 1. Executive Summary & Vision

This document details the greenfield architectural specification, technology stack, security boundaries, and phased evolutionary roadmap for a commercial, high-performance **Autonomous Coding Harness System**.

The primary objective is to engineer an enterprise-grade, highly scalable, zero-rewrite architecture capable of achieving **>80% resolution accuracy on SWE-bench** (Lite/Verified) while maintaining microsecond-level dispatch choke points, complete capability authorization security, and strict separation between symbolic reasoning (LLMs) and infrastructure control planes.

---

## 2. Greenfield Polyglot Architecture & Tech Stack

To scale to multi-agent swarms without hitting Python's Global Interpreter Lock (GIL) overhead, memory bloat, or slow process dispatch, the architecture is split into three decoupled planes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTROL & USER INTERFACE PLANE                           │
│   • Go / TypeScript TUI & CLI (OpenCode / Claude Code CLI inspiration)     │
│   • gRPC / JSON-RPC / IPC Client                                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ gRPC / Protobuf / Unix Sockets
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    RUST HIGH-PERFORMANCE MICROKERNEL                        │
│   • Capability Authorization Engine (CAR Model / PolicyEngine choke point)  │
│   • Git Worktree Isolation Pool & Subprocess Sandbox Execution Engine       │
│   • Tree-Sitter AST Parsing & High-Performance Indexing (`tree-sitter-rs`)  │
│   • Trajectory Content-Addressed Storage (CAS) & Audit Logging              │
└───────────┬────────────────────────────────────────────────┬────────────────┘
            │ MCP / gRPC                                     │ IPC / Arrow
┌───────────▼───────────┐                        ┌───────────▼────────────────┐
│   TOOL LAYER (MCP)    │                        │  PYTHON IAO & PROMPT       │
│ Model Context Protocol│                        │  INTELLIGENCE SIDECAR      │
│ Local & Remote Tools  │                        │ (LLM SDKs, DSPy, Local GBDT│
└───────────────────────┘                        │  surrogate, LTM / Vector)  │
                                                 └────────────────────────────┘
```

### Stack Allocation
* **Rust Core Engine (Microkernel & Sandbox):**
  * **Role:** Capability security choke point (`PolicyEngine`), process/worktree pool management, AST indexing (`tree-sitter-rs`), trajectory CAS, and high-frequency dispatch.
  * **Inspiration:** [`src/grok_build`](file:///home/rock_dev/Code/Harness/src/grok_build).
* **Go / TypeScript (Control Plane & UI/TUI):**
  * **Role:** High-concurrency I/O multiplexing, terminal rendering (TUI), CLI command parsing, and Agent-to-Agent (A2A) protocol negotiation.
  * **Inspiration:** [`src/open_code`](file:///home/rock_dev/Code/Harness/src/open_code) & [`src/claude_code`](file:///home/rock_dev/Code/Harness/src/claude_code).
* **Python (Intelligence Sidecar & IAO):**
  * **Role:** Frontier LLM integrations (Google GenAI, Anthropic, OpenAI), prompt/DSPy optimization loops, and local surrogate reward/risk prediction models (IAO).
  * **Inspiration:** [`src/hermes_agent`](file:///home/rock_dev/Code/Harness/src/hermes_agent) & [`src/sagiha`](file:///home/rock_dev/Code/Harness/src/sagiha).

---

## 3. Structural Mechanics of Top SWE-Bench Performers (>80%)

High performance on SWE-bench requires specific harness mechanics rather than naive chat loops:

1. **Separation of Generator & Evaluator (Anthropic 3-Agent Pattern):**
   * Generator agents modify code within isolated Git worktrees.
   * A dedicated Evaluator agent with held-out unit test pipelines admits or rejects patches. The Generator can never self-certify its own patch.
2. **Precise AST Slicing (Tree-Sitter + Hybrid Search):**
   * Never feed raw, un-parsed full files to the prompt window. Extract exact call graphs, type definitions, and scope-sliced dependencies using `tree-sitter`.
3. **Isolated Parallel Worktree Pool:**
   * Sub-agents execute concurrently in zero-copy Git worktrees without file-locking conflicts. A dedicated `IntegrationAgent` handles rebases and conflict resolution before merging to main.
4. **IAO (Auxiliary Optimization Intelligence) Surrogate Filtering:**
   * Running full test suites on every intermediate proposal is expensive and slow. A lightweight local model (GBDT/Neural) predicts failure risk and surrogate reward, pruning 80% of bad branches before running heavy tests.
5. **Deterministic DMARTIC Execution Logs:**
   * Capture un-truncated stack traces, AST error nodes, and lint IDs, feeding empirical log evidence directly back into self-correction loops.

---

## 4. Synthesis of Cloned Open Source Reference Engines (`./src`)

| Reference Engine | Language / Core | Key Component / Pattern to Adopt |
| :--- | :--- | :--- |
| **`grok_build`** ([`src/grok_build`](file:///home/rock_dev/Code/Harness/src/grok_build)) | Rust | Zero-copy Git Worktree Manager, high-performance state machine, memory-safe execution dispatch. |
| **`open_code`** ([`src/open_code`](file:///home/rock_dev/Code/Harness/src/open_code)) | Go / `sqlc` | Clean terminal UX, high-concurrency subprocess orchestration, compile-time typed SQL schemas (`sqlc`). |
| **`claude_code`** ([`src/claude_code`](file:///home/rock_dev/Code/Harness/src/claude_code)) | TypeScript / MCP | Streaming tool calls, interactive human-in-the-loop permission approvals, sub-agent lifecycle management. |
| **`hermes_agent`** ([`src/hermes_agent`](file:///home/rock_dev/Code/Harness/src/hermes_agent)) | Python | Trajectory compression (`trajectory_compressor.py`), dynamic skill loading, mini-SWE runner execution loops. |
| **`sagiha`** ([`src/sagiha`](file:///home/rock_dev/Code/Harness/src/sagiha)) | Python MVP | Capability Security (`PolicyEngine.authorize()`), immutable test gates (`require_tests_unmodified`), clean hexagonal ports (`ports/`). |

---

## 5. Architectural Invariants for Zero-Rewrite Evolution

To ensure growth from MVP to enterprise scale without major refactorings:

1. **Contract-First API Design:**
   * Define frozen `.proto` / gRPC schemas (`kernel.proto`, `events.proto`, `agent_state.proto`) first.
   * Backend and Frontend develop in parallel against mock stubs generated directly from those schemas.
2. **Hexagonal Port-Adapter Isolation:**
   * Pure domain logic models have **zero I/O dependencies**.
   * All infrastructure dependencies (SQLite, Qdrant, Docker, Git Worktree, LLM providers) live behind typed, remotable **Port** protocols.
3. **Remotable Ports (Wire-Serializable):**
   * Port parameters must be Pydantic / Protobuf serializable payload objects. No raw file handles, callbacks, or live objects cross boundaries.
4. **Day 1 Evaluation-Driven Development (EDD):**
   * Configure [`princeton-nlp/SWE-bench_Lite`](file:///home/rock_dev/Code/Harness/princeton-nlp/SWE-bench_Lite) as an automated CI/CD gate from Day 1 to track performance deltas continuously.

---

## 6. Phased Evolutionary Roadmap

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Phase 0: System Architecture & Frozen Contracts (Weeks 1-2)            │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Phase 1: Decoupled MVP Engine + Day 1 SWE-Bench (Weeks 3-5)            │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Phase 2: Rust Core Engine & Parallel Worktree Pool (Weeks 6-9)        │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Phase 3: SOTA IAO Control Plane & Outer-Loop Swarms (Weeks 10-14)      │
 └────────────────────────────────────────────────────────────────────────┘
```

### Phase 0: Specification & Contract Locking (Weeks 1–2)
* **Goal:** Lock in all architectural decision records (ADRs) and interface boundaries.
* **Deliverables:**
  * Draft ADR-001 through ADR-004 (Microkernel, Security CAR Model, IPC, Memory).
  * Freeze Protobuf API schemas (`kernel.proto`, `events.proto`, `agent_state.proto`).
  * Threat Model & Capability Policy Matrix specification.

### Phase 1: Decoupled MVP Engine + Day 1 SWE-Bench (Weeks 3–5)
* **Goal:** Create working microkernel with automated evaluation benchmarking from Day 1.
* **Deliverables:**
  * Microkernel supporting single-agent execution in an isolated Git worktree.
  * Anthropic 3-Agent Loop (`Planner` → `Generator` → `Evaluator`).
  * AST Context Compactor using `tree-sitter`.
  * Automated [`SWE-bench_Lite`](file:///home/rock_dev/Code/Harness/princeton-nlp/SWE-bench_Lite) CI runner logging baseline scores.

### Phase 2: Rust Core Engine & Parallel Worktree Pool (Weeks 6–9)
* **Goal:** Migrate high-frequency execution choke points to Rust and enable parallel multi-agent swarms.
* **Deliverables:**
  * Rust Core Engine (inspired by `grok_build`) for worktree pool management and AST indexing.
  * Model Context Protocol (MCP) server & client integration.
  * DuckDB / SQLite structured trajectory store.
  * Go/TypeScript TUI for real-time inspection.

### Phase 3: SOTA IAO Control Plane & Outer-Loop Swarms (Weeks 10–14)
* **Goal:** Reach target benchmark performance (>80% on SWE-bench) with statistical control planes and self-evolution.
* **Deliverables:**
  * **Auxiliary Optimization Intelligence (IAO):** Local surrogate reward & risk predictor filtering candidate rollout branches.
  * **Integration Agent:** Dedicated merge/rebase conflict resolution for parallel agent worktrees.
  * **Recursive Harness Improvement (RHI):** Outer loop to evaluate and optimize prompt strategies, skills, and routing policies automatically against held-out benchmark suites.

---

## 7. Immediate Pre-Coding Action Plan

1. Create `docs/08-decisions/` ADR templates and write ADR-001 (Polyglot Core Architecture) and ADR-002 (CAR Security Model).
2. Establish `contracts/proto/` directory and draft the initial gRPC service definition (`kernel.proto`).
3. Verify local environment integration with [`princeton-nlp/SWE-bench_Lite`](file:///home/rock_dev/Code/Harness/princeton-nlp/SWE-bench_Lite) for baseline scoring.
