# **SAGIHA2 — Super AGI Meta-Harness Agent of Agents**

### **A World-Class, Self-Evolving Multi-LLM Orchestration Framework for Autonomous Software Engineering**

**Version:** Conceptual Design 1.0 (July 2026)  
**Classification:** PhD-level Agent Systems Architecture | SOTA Meta-Harness  

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a proposed architecture and architectural blueprint for the Meta Harness CoderAGI, not an imperative or immutable final solution. Further iterative prototyping, benchmarks, and practical evaluations will be conducted to refine and finalize the ultimate harness structure.

**Core Thesis:** The intelligence resides exclusively in the LLMs. The harness is a pure, modular, evolvable environment that supplies context, memory, tools, coordination, verification, and recursive self-improvement mechanisms. The system is designed so that its own source code becomes the primary artifact it optimizes until it can generate and evolve arbitrary software projects.

## **1\. Vision & Design Philosophy**

SAGIHA2 is not another agent framework. It is a **Meta-Harness**: a stable, hexagonal, plugin-based runtime whose primary purpose is to turn one or more frontier LLMs into a Super-Agent capable of orchestrating specialized sub-agents, executing long-horizon coding tasks, and continuously rewriting its own scaffolding under strict verification.  
**Foundational Principles**

> * LLMs own all intelligence, planning, creativity, and decision-making.  
> * The harness owns only: context assembly, memory, tool contracts, orchestration primitives, verification, observability, and safety boundaries.  
> * Zero coupling between domain logic and infrastructure (hexagonal \+ ports & adapters).  
> * Every functional block is an independently replaceable plugin (SQLite → TurboQuant, in-memory STM → Redis, etc.) without changing external contracts.  
> * SOLID \+ DRY \+ Clean Code \+ Dependency Injection everywhere.  
> * Model–Harness Co-evolution as first-class citizen.  
> * Separation of Generator and Evaluator (Anthropic 2026 pattern).  
> * Bounded Recursive Self-Improvement with held-out validation to prevent collapse and reward hacking.

## **2\. High-Level Architecture**

┌─────────────────────────────────────────────────────────────────────────────┐  
│                     Super-Orchestrator LLM (Primary Intelligence)           │  
│              (owns goals, decomposition, meta-reasoning, final decisions)   │  
└───────────────────────────────┬─────────────────────────────────────────────┘  
                                │ A2A \+ MCP \+ Typed Ports  
┌───────────────────────────────▼─────────────────────────────────────────────┐  
│                         SAGIHA2 Meta-Harness Kernel                         │  
│  • DI Container          • Lifecycle & Checkpoint Manager                   │  
│  • Event Bus             • Observability (OTel \+ Trajectory Store)          │  
│  • Cost & Budget Control • Safety & Autonomy Policies                       │  
│  • Plugin Discovery      • Self-Improvement Outer Loop Controller           │  
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────────┘  
    │      │      │      │      │      │      │      │      │  
┌───▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──────────────┐  
│ STM  ││ LTM ││Index││Graph││Tools││Res. ││Orch.││Eval ││ Meta-Improve    │  
│      ││     ││     ││     ││+MCP ││     ││     ││     ││ (Outer Loop)    │  
└──────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────────────────┘  
   ▲        ▲       ▲       ▲       ▲       ▲       ▲       ▲         ▲  
Adapters (plugins) — all interchangeable under stable Ports

**Key Separation**

> * **Inner Loop**: Task execution (DMARTIC \+ coding agents).  
> * **Outer Loop (Meta-Harness)**: Improvement of the harness itself (prompts, flows, adapters, policies) under held-out metrics.

## **3\. Functional Blocks (Plugin Architecture)**

Every block exposes a minimal, stable **Port** (Protocol / Interface). Implementations are pure adapters.

| Block | Port Name | Initial Adapter (Day 0) | Advanced SOTA Adapters | Responsibility |
| :---- | :---- | :---- | :---- | :---- |
| Short-Term Memory | ShortTermMemory | In-memory circular buffer / JSONL | Redis, LanceDB | Session context, step trajectories, compaction |
| Long-Term Memory | LongTermMemory | SQLite + sqlite-vec | Hybrid (LanceDB + Graphiti property graph) | Persistent knowledge, preferences, bi-temporal history |
| Indexing | Indexer | SQLite-FTS5 + Tree-sitter Python | Rust/Go Sidecar (tqdb / Tree-sitter gRPC) | Codebase AST, symbol resolution & TurboQuant vector search |
| Knowledge Graph | KnowledgeGraph | NetworkX / SQLite | Neo4j / FalkorDB + Graphiti | Code dependencies, ADR decisions, co-change volatility |
| Language Diagnostics | LSPAdapter | Local stdio LSP (`pygls`) | High-speed LSP Daemon Sidecar | Real-time type checking, syntax diagnostics & code actions |
| Tools & Scripts | ToolRegistry + Executor | Local functions + shell | Full MCP ecosystem (Stdio / HTTP-SSE) | Sandboxed execution surface & tool discovery |
| Research | Researcher | Web + local file search | Multi-source hybrid search | External knowledge acquisition |
| Orchestration | Orchestrator / Spawner | Native Async Microkernel (ReAct) | Dual-Process MCTS Worktree + A2A Multi-Agent | Agent lifecycle, state machine, DMARTIC engine |
| Evaluation | Evaluator | Pytest runner + linter | Multi-judge LLM + private PRM scoring | Independent quality gate |
| Meta-Improvement | MetaImprover | Propose-Evaluate-Accept | RHI / AIDE²-style outer loop | Self-evolution of harness prompts & scaffolding |

**Contract Guarantee**: Replacing any adapter (e.g., swapping Python AST indexer for a Rust gRPC sidecar) never requires changes to consumers.

## **4\. Core Workflows**

### **4.1 DMARTIC Cycle (Inner Loop — Dual-Process Cognitive Engine)**

The inner loop operates as a Dual-Process Cognitive Engine:
* **System 1 (Fast Execution):** Direct ReAct single-turn execution for low-complexity, localized edits.
* **System 2 (Slow Reasoning & Tree Search):** Monte Carlo Tree Search (MCTS) with parallel Git Worktree branching for multi-file refactoring and architectural changes.

Extended DMARTIC execution sequence:

> 1. **Concept** — Goal formulation, requirement parsing & hypothesis generation  
> 2. **Design** — Architectural plan & decomposition (System 1 direct plan vs. System 2 MCTS tree branch allocation)  
> 3. **Measure** — Baseline static analysis, LSP type diagnostics & test coverage collection  
> 4. **Analyze** — Query AST sidecar index, Graphiti temporal graph & TurboQuant vector store  
> 5. **Review** — Independent Evaluator Agent check (Plan Mode gate for high-risk actions)  
> 6. **Test** — Speculative execution inside parallel Git worktrees; immediate verification via LSP diagnostics & unit tests  
> 7. **Improve** — MCTS candidate selection & iterative refinement based on LSP errors and PRM scores  
> 8. **Control** — Security policy validation, budget check, merge winning worktree branch into main, invalidate stale graph facts  
> 9. **Self-Reflect** — Trajectory compaction & bi-temporal event log commit into LTM

### **4.2 Outer Loop — Recursive Harness Self-Improvement (RHI)**

> * Represent harness behavior as editable artifacts (prompts, YAML workflows, adapter code, policies).  
> * Outer agent proposes modifications.  
> * Evaluate on **held-out** task suite (never seen by the improver).  
> * Accept only if private score improves and no regression on safety/cost metrics.  
> * Version every accepted change with full trajectory and diff.  
> * Protect against reward hacking via multi-objective evaluation and adversarial test cases.

### **4.3 Multi-Agent Patterns Supported**

> * Supervisor + specialized workers  
> * Planner → Generator → Evaluator (Anthropic 3-agent pattern)  
> * Role-based crews (CrewAI-style)  
> * Peer-to-peer via A2A (Agent Cards + task lifecycle)  
> * Parallel execution via git worktrees / isolated sandboxes

## **5\. Protocols & Interoperability (2026 SOTA)**

> * **MCP (Model Context Protocol)**: Universal tool & resource layer. Every capability is an MCP server.  
> * **A2A (Agent-to-Agent)**: Peer discovery, task delegation, long-running stateful collaboration.  
> * Layered usage: Orchestrator uses A2A to talk to specialist agents; each agent uses MCP to talk to tools.

## **6\. Technology Stack (Recommended 2026\)**

**Runtime & Languages**

> * Primary Control Plane: Python 3.12+ (async-first, Pydantic v2 + typing.Protocol)  
> * High-Performance Sidecars: Rust & Go (compiled binaries for Tree-sitter AST parsing, tqdb vector quantization, and fast file indexing communicating via gRPC / IPC)  
> * Optional UI/IDE Layer: TypeScript / React

**Orchestration Core**

> * Native Async Microkernel: Deterministic event-bus and state machine kernel (zero external framework lock-in)  
> * LangGraph / Microsoft Agent Framework: Supported strictly as optional external adapters behind the `Orchestrator` Port

**Memory & Retrieval**

> * STM: In-memory sliding buffer → Redis  
> * LTM / Index: SQLite + sqlite-vec (Day 0) → LanceDB + Rust/Go TurboQuant Sidecar (SOTA)  
> * Graph: NetworkX → Graphiti on Neo4j / FalkorDB

**Execution Safety & Language Tooling**

> * Docker / gVisor (runsc) sandboxes per agent  
> * Git worktrees for parallel branch exploration  
> * LSP Integration: `pygls` / LSP daemon sidecar for real-time type checking and diagnostics

**Observability & Governance**

> * OpenTelemetry + custom Trajectory Store  
> * Cost, latency, token, success-rate dashboards  
> * Circuit breakers, budgets, autonomy policies (configurable per domain risk)

**Evaluation**

> * Internal benchmark suite (SWE-bench subsets + custom project generation tasks)  
> * Public/private score split  
> * Multi-judge + process reward models

## **7\. Safety, Autonomy & Control**

> * Autonomy levels: Interactive → Hybrid → Fully Autonomous → Scheduled  
> * Human-in-the-loop gates by risk class  
> * Immutable audit log of every decision and harness mutation  
> * Hard iteration / token / wall-time limits  
> * Sandboxed code execution with network and filesystem policies  
> * Self-improvement only accepted after multi-metric held-out validation

## **8\. Phased Adapter Migration Matrix (Day 0 → Day N Evolution)**

| Component | Day 0 (Simple Baseline) | Day 1 (Production Ready) | Day 2 (SOTA AGI Harness) |
| :---- | :---- | :---- | :---- |
| **Kernel Orchestrator** | Native Async ReAct Loop | Stateful State Machine + Checkpoints | Dual-Process MCTS + A2A Multi-Agent Fleet |
| **Short-Term Memory** | In-Memory Circular Buffer | Redis Persistence + Compaction | Trajectory-Compressed Context Ring |
| **Long-Term Memory** | SQLite + simple embeddings | LanceDB + SQLite-WAL Event Log | Graphiti Bi-Temporal Graph + LanceDB |
| **Indexing Engine** | Python Tree-sitter + BM25 | SQLite-FTS5 + AST Skeletonizer | Rust/Go gRPC Sidecar (tqdb + Tree-sitter) |
| **Diagnostic Layer** | Subprocess pytest + flake8 | Local Stdio LSP (`pygls`) Adapter | Multi-language LSP Daemon Sidecar |
| **Execution Sandbox** | Local Subprocess + Git Branch | Ephemeral Isolated Git Worktrees | Containerized Docker/gVisor Worktrees |
| **Protocol Integration** | Stdio MCP Tool Drivers | HTTP-SSE MCP Server/Client | Full MCP + A2A Protocol Infrastructure |
| **Self-Improvement** | Manual Prompt Iteration | Automated PRM Step Scoring | RHI Outer Loop under Held-Out Validation |

## **9\. Package Structure (Clean Architecture)**

sagiha2/  
├── kernel/                 # DI, lifecycle, event bus, observability, safety  
├── ports/                  # All Protocols (stable typing.Protocol interfaces)  
├── adapters/               # Concrete Python implementations (plugins)  
│   ├── memory/             # SQLite, Redis, LanceDB, Graphiti adapters  
│   ├── indexing/           # Local & Sidecar AST / Vector search adapters  
│   ├── lsp/                # Language Server Protocol adapters  
│   ├── tools/              # Local functions & MCP client drivers  
│   ├── research/           # Search & retrieval tools  
│   └── evaluation/         # Pytest & LLM PRM evaluators  
├── orchestration/          # Native microkernel, DMARTIC engine, MCTS tree search  
├── sidecars/               # High-performance native sidecars (Rust/Go)  
│   ├── ast_indexer_rust/   # Tree-sitter AST gRPC service  
│   └── tq_vector_go/       # tqdb vector quantization engine  
├── meta/                   # Outer-loop self-improvement  
├── mcp/                    # MCP server & client integrations  
├── a2a/                    # Agent-to-Agent protocol layer  
├── trajectories/           # OTel-instrumented trajectory store  
├── benchmarks/             # Held-out evaluation suites  
└── workspace/              # Git worktree & sandbox management

## **10\. Success Metrics (World-Class Definition)**

> * Task success rate on hard coding benchmarks  
> * Self-improvement delta on held-out suite per outer-loop iteration  
> * Cost and latency per successful project generation  
> * Regression rate after harness mutations  
> * Human intervention rate (target → near zero for well-scoped domains)  
> * Ability to generate and maintain its own subsequent versions

## **11\. Closing Statement**

SAGIHA2 is the synthesis of everything the original specification required (modular hexagonal packages, DMARTIC, replaceable indexing, LLM-centric intelligence) with the full set of 2026 SOTA necessities that were not originally requested: independent evaluation, recursive harness self-improvement under held-out validation, MCP \+ A2A protocols, rigorous observability, sandboxed parallel execution, and a clear evolutionary path toward a general software-creation Super-Agent.  
The harness remains deliberately “dumb.”  
All intelligence, creativity, and ambition live in the models.  
The Meta-Harness’s only job is to give those models the richest possible environment in which to think, act, verify, and improve — including the environment itself.  
This is the architecture of a system that does not merely use AI to write code.  
It is the architecture of a system that uses AI to become a better system for writing any code.

## **12\. Incremental Improvements from Grok Build (v1.1)**

The following enhancements are incorporated from the publicly available Apache 2.0 Grok Build harness. They strengthen parallelism, extensibility, and operational robustness without altering the core hexagonal architecture or the Outer Loop philosophy.

### **12.1 Parallel Execution with Isolated Git Worktrees**

SAGIHA2 now treats **git worktrees** as a first-class isolation primitive for parallel agents:

> * Each sub-agent (or specialized worker) can be spawned inside its own worktree.  
> * Changes remain completely isolated until explicitly merged or discarded.  
> * The Orchestrator maintains a worktree registry and lifecycle (create, list, apply, gc).  
> * This enables true concurrent coding on the same repository without file conflicts — a capability previously missing from the base design.

**Port addition:**  
class WorktreeManager(Protocol):  
    async def create(self, base\_ref: str \= "HEAD") \-\> WorktreeHandle: ...  
    async def apply(self, handle: WorktreeHandle) \-\> None: ...  
    async def discard(self, handle: WorktreeHandle) \-\> None: ...

### **12.2 Explicit Agent Loop**

The inner reasoning/execution cycle is now formalized as a clear, observable loop inspired by production harnesses:

> 1. **Context Assembly** — gather STM, relevant LTM, indexed code, graph facts, and current plan.  
> 2. **Model Invocation** — call the chosen LLM with structured tools and system instructions.  
> 3. **Response Parsing** — extract natural language, tool calls, or plan updates.  
> 4. **Tool Dispatch** — execute via the ToolRegistry (MCP or local) under permission scopes.  
> 5. **Observation & Update** — write results back to STM / Trajectory Store and decide next step.

This loop lives inside every Orchestrator node and is fully instrumented with OpenTelemetry spans.

### **12.3 Extension System (Skills, Plugins, Hooks)**

A lightweight but powerful extension layer is added:

> * **Skills** — reusable, versioned instruction \+ tool packages (loaded from skills/ or MCP).  
> * **Plugins** — full adapters that can register new Ports or replace existing ones at runtime.  
> * **Hooks** — lifecycle callbacks (pre-tool, post-tool, pre-plan, post-improve, etc.) that allow observation or interception without modifying core code.

Discovery is automatic via the Plugin Discovery component already present in the Kernel. This brings the modularity of Grok Build’s extension model into the hexagonal design.

### **12.4 Plan Mode with Human Review Gate**

Before any destructive or multi-file change set is applied, the system can enter **Plan Mode**:

> * The Orchestrator (or a dedicated Planner agent) produces a structured plan (files to touch, commands to run, expected outcomes).  
> * The plan is presented for human approval (or auto-approved under low-risk autonomy policies).  
> * Only after approval does the system proceed to execution (possibly spawning parallel worktree agents).

This directly implements the “plan-then-execute” pattern and strengthens the Control step of DMARTIC.

### **12.5 Workspace Abstraction & Headless Operation**

A dedicated **Workspace** port is introduced:  
class Workspace(Protocol):  
    async def read(self, path: str) \-\> str: ...  
    async def write(self, path: str, content: str) \-\> None: ...  
    async def run(self, command: str) \-\> CommandResult: ...  
    async def checkpoint(self) \-\> CheckpointId: ...  
    async def restore(self, checkpoint: CheckpointId) \-\> None: ...

> * Supports both interactive TUI-style sessions and fully **headless** execution (ideal for CI, scheduled runs, and Outer Loop experiments).  
> * Local-first configuration via a single config.toml (model endpoints, autonomy level, worktree root, MCP servers, etc.).

### **12.6 Updated Package Structure (additions)**

sagiha2/  
├── ...  
├── workspace/              \# New: Workspace port \+ git worktree implementation  
├── extensions/             \# New: skills, plugins, hooks loader  
│   ├── skills/  
│   ├── plugins/  
│   └── hooks/  
└── ...

## **13\. Impact on Existing Components**

| Component | Change |
| :---- | :---- |
| Orchestration | Now supports worktree-spawned parallel agents and explicit Plan Mode |
| Tools | Tool dispatch becomes step 4 of the formalized Agent Loop |
| Meta-Improvement | Outer Loop can evolve skills, hooks, and worktree policies |
| Safety & Autonomy | Plan Mode adds an additional human/policy gate |
| Observability | Every step of the Agent Loop emits structured traces |

These additions raise the maturity of the parallel execution and extensibility layers to the level of the best open-source coding harnesses available in mid-2026, while preserving the original Meta-Harness vision and all previously defined contracts.

## **14\. Auxiliary Optimization Intelligence (AOI)**

### **14.1 Purpose and Scope**

The Auxiliary Optimization Intelligence (AOI) is a set of lightweight, locally trainable models that operate alongside the Super-Orchestrator LLM.  
Its sole responsibility is to learn from execution trajectories and continuously improve the selection of configurations, routing decisions, early-stopping policies, and Outer-Loop proposals.  
AOI never replaces the deliberative reasoning of the frontier LLMs. It acts as a statistical co-pilot that makes the Meta-Harness more sample-efficient, cost-aware, and adaptive.

### **14.2 Core Responsibilities**

| Responsibility | Description | Output |
| :---- | :---- | :---- |
| Configuration Selection | Choose the best combination of models, adapters, and policies for a task | Ranked list of configs |
| Reward / Preference Prediction | Estimate the expected quality of a proposed harness change | Scalar or multi-objective score |
| Failure Prediction | Detect trajectories that are likely to fail early | Risk score \+ recommended action |
| Cost-Performance Estimation | Predict cost, latency, and quality trade-offs | Pareto estimates |
| Context Compaction Policy | Decide what information should be retained or summarized | Compaction strategy |

### **14.3 Architectural Integration**

AOI is fully integrated into the hexagonal architecture through dedicated Ports:  
class RewardPredictor(Protocol):  
    async def predict(self, trajectory\_features: dict) \-\> float: ...

class ConfigurationSelector(Protocol):  
    async def select(self, task\_context: dict, candidates: list\[Config\]) \-\> list\[RankedConfig\]: ...

class FailurePredictor(Protocol):  
    async def predict\_risk(self, partial\_trajectory: dict) \-\> FailureRisk: ...

class CostPerformanceEstimator(Protocol):  
    async def estimate(self, config: Config, task\_features: dict) \-\> CostQualityEstimate: ...

These Ports are injected via the Kernel’s Dependency Injection container.  
Concrete adapters may be implemented with:

> * Gradient Boosting (XGBoost, LightGBM, CatBoost)  
> * Small neural networks (PyTorch / MLX)  
> * Linear / logistic models with strong regularization  
> * Embedding-based rankers (sentence-transformers)

All adapters must support both inference and incremental/online updates.

### **14.4 Data Sources**

AOI is trained exclusively on data generated by SAGIHA2 itself:

> * Complete and partial trajectories (from Trajectory Store)  
> * Configuration snapshots used in each run  
> * Observed metrics: success/failure, test pass rate, cost, latency, token usage  
> * Human preference signals (when available)  
> * Outer-Loop proposal outcomes (accepted / rejected \+ reason)

Every experience is stored in a structured, versioned format that can be replayed for offline training or used for online updates.

### **14.5 Training and Update Strategies**

> * **Offline batch training**: periodic retraining on the accumulated dataset (nightly or after N new trajectories).  
> * **Online / continual learning**: lightweight updates after each significant run (especially useful for FailurePredictor and RewardPredictor).  
> * **Experience replay \+ prioritization**: more weight is given to rare failures and high-impact configuration changes.  
> * **Held-out protection**: a portion of the data is never used for training the AOI models that influence the Outer Loop, preserving evaluation integrity.

Training is designed to run on consumer hardware (CPU or single consumer GPU).

### **14.6 Interaction with the Outer Loop (Meta-Improvement)**

> 1. The MetaImprover generates candidate changes to the harness.  
> 2. AOI ranks or filters these candidates using the RewardPredictor and CostPerformanceEstimator.  
> 3. Only the most promising candidates are submitted to the expensive held-out evaluation.  
> 4. Results of the evaluation are fed back into the AOI training set.  
> 5. Over time, the AOI becomes increasingly accurate at predicting which classes of changes are worth evaluating.

This creates a tight, data-driven co-evolution loop between the symbolic Outer Loop and the statistical AOI.

### **14.7 Configuration Search**

Because the entire system is configuration-driven (YAML \+ Pydantic), AOI can treat the configuration space as a searchable domain:

> * It can propose new YAML configurations.  
> * It can perform Bayesian optimization, evolutionary search, or simple multi-armed bandit strategies over the discrete/continuous parameter space.  
> * Different optimization targets (cost, quality, speed, balanced) are first-class citizens and can be selected per project or per task type.

### **14.8 Package Structure Additions**

sagiha2/  
├── ...  
├── aoi/                          \# Auxiliary Optimization Intelligence  
│   ├── ports.py                  \# RewardPredictor, ConfigurationSelector, etc.  
│   ├── adapters/                 \# Concrete model implementations  
│   ├── features/                 \# Feature extraction from trajectories  
│   ├── training/                 \# Offline and online training pipelines  
│   └── registry.py               \# Model versioning and loading  
└── ...

### **14.9 Design Principles Specific to AOI**

> * **Local-first**: all training and inference must be feasible on ordinary developer machines.  
> * **Statistically humble**: AOI models are intentionally narrow and well-calibrated; they express uncertainty.  
> * **Non-blocking**: if an AOI model is unavailable or low-confidence, the system falls back to safe default policies.  
> * **Fully observable**: every prediction and update is logged in the Trajectory Store.  
> * **Decoupled from deliberative intelligence**: AOI never generates natural language plans or code; it only scores, ranks, and selects.

### **14.10 Expected Impact**

The introduction of AOI transforms SAGIHA2 from a system that improves itself through expensive trial-and-error into a system that improves itself through statistically guided, sample-efficient search.  
It directly addresses the core economic problem of Meta-Harness evolution: how to explore a large configuration and design space without prohibitive cost.  
**End of Technical Specification**