---
status: rationale
updated: 2026-08-01
title: SOTA Harness Infrastructure & Autonomous AGI Coding Agent Architectural Briefing
source: docs/rationale/reference/harness_research_2026.md
---

# SOTA Harness Infrastructure & Autonomous AGI Coding Agent Architectural Briefing

## Executive Summary

This document provides a comprehensive, highly detailed, yet concise architectural briefing for constructing a **State-of-the-Art (SOTA) Meta-Harness Infrastructure** and a **World-Class Autonomous AGI Coding Agent** capable of operating for long sessions (days to weeks) on complex multi-tasking software engineering goals.

It condenses the PhD-level specifications, mathematical formulations, protocol designs, execution engines, and technology stacks from [`harness_research_2026.md`](file:///home/rock_dev/Code/Harness/docs/rationale/reference/harness_research_2026.md) into 11 structured chapters totaling under 1,500 lines for rapid reference and implementation.

---

## Chapter 1: Vision, Design Philosophy & Foundational Invariants

### 1.1 Core Thesis: Model-Centric Intelligence vs. Harness Scaffolding
- **LLMs Own All Intelligence**: Planning, reasoning, creativity, code synthesis, hypothesis formulation, and strategic decision-making reside exclusively within frontier LLMs.
- **The Harness Owns Scaffolding & Boundary Control**: The harness is a pure, modular, evolvable environment providing context assembly, memory persistence, tool contracts, execution sandboxes, verification gates, safety boundaries, and deterministic state orchestration.
- **The Meta-Harness Concept**: The harness source code itself is an edit-target artifact. It continuously optimizes its own scaffolding (prompts, routing graphs, validation rules) under strict held-out evaluation until it can autonomously generate, refactor, and evolve non-trivial software projects.

### 1.2 Foundational Architectural Invariants
1. **Hexagonal Architecture (Ports & Adapters)**: Absolute separation between domain reasoning logic and infrastructure adapters.
2. **SOLID + Clean Code + Dependency Injection (DI)**: Interfaces (`typing.Protocol`) define contracts; concrete adapters are injected at composition runtime.
3. **Dual-Loop Execution Model**:
   - **Inner Loop (Task Execution)**: Solves specific software tasks using cyclic state machines (DMARTIC).
   - **Outer Loop (Recursive Harness Improvement - RHI)**: Mutates the harness scaffolding and evaluates candidates against private held-out benchmark suites.
4. **Generator-Evaluator Separation (Anthropic 2026 Pattern)**: Task execution agents (Generators) are strictly decoupled from independent Evaluator agents.
5. **Bounded Self-Improvement**: Harness mutations are accepted only if they pass private, held-out evaluation suites without regressing safety or token cost boundaries, preventing reward hacking and collapse.

---

## Chapter 2: Clean Architecture & Hexagonal Ports System

### 2.1 Core Package Layout
```text
sagiha/
├── kernel/            # DI Container, Lifecycle, Event Bus, Safety, Observability
├── ports/             # Pure Python Protocols (Stable contracts, 100% remoteable/async)
├── domain/            # Pure Pydantic models (Zero I/O dependencies)
├── adapters/          # Concrete implementations (Plugins: memory, index, tools, etc.)
│   ├── workspace/     # Local workspace & Git Worktree manager
│   ├── sandbox/       # Container sandboxes & egress proxy firewalls
│   ├── memory/        # Short-term (Redis/In-Memory) & Long-term (SQLite/LanceDB)
│   ├── indexing/      # Dense/sparse vector indexers (sqlite-vec, LlamaIndex)
│   ├── graphs/        # NetworkX / Neo4j Knowledge Graph adapters
│   ├── tools/         # MCP tool drivers & cassette recorder/replay
│   ├── iao/           # NullIAO, XGBoost, and ONNX statistical control adapters
│   └── evaluation/    # Inspect AI & SWE-bench test runners
├── orchestration/     # LangGraph DMARTIC cycle & Temporal.io durable workflows
├── meta/              # Outer Loop RHI MetaImprover engine
├── mcp/               # Model Context Protocol servers & clients
├── a2a/               # Agent-to-Agent protocol layer (Agent & Task Cards)
├── extensions/        # Dynamic loading for Skills, Plugins, and Hooks
├── trajectories/      # Persistent execution traces and telemetry logs
└── benchmarks/        # Held-out evaluation suites and ablation fixtures
```

### 2.2 Functional Ports & Adapter Contracts

| Port Name | Target Protocol | Primary Adapters | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| `Workspace` | `Workspace` | Local, Git Worktree | Isolated file reads/writes, bash command execution, state checkpointing. |
| `WorktreeManager` | `WorktreeManager` | Git Worktree Adapter | Zero-copy concurrent workspace branching (`create`, `apply`, `discard`). |
| `ShortTermMemory` | `ShortTermMemory` | In-memory, Redis | Active session context, sliding-window token compaction. |
| `LongTermMemory` | `LongTermMemory` | SQLite + Vector, LanceDB | Persistent knowledge store: Episodic, Semantic, and Procedural. |
| `Indexer` | `Indexer` | sqlite-vec, LlamaIndex | Dense/sparse code chunking, vector indexing, Reciprocal Rank Fusion (RRF). |
| `KnowledgeGraph` | `KnowledgeGraph` | NetworkX, Neo4j | Code dependency mapping, AST call graphs, entity-relationship traversal. |
| `ToolRegistry` | `ToolRegistry` | MCP Client Drivers | Universal tool exposure and execution via JSON-RPC 2.0 schemas. |
| `Orchestrator` | `Orchestrator` | LangGraph, Temporal | State machine transitions, DMARTIC loop control, checkpoint time-travel. |
| `Evaluator` | `Evaluator` | Inspect AI, SWE-bench | Independent code quality scoring, rubric evaluation, held-out testing. |
| `MetaImprover` | `MetaImprover` | Propose-Evaluate-Accept | Outer-loop harness prompt and workflow mutation proposals. |
| `IAOCircuitBreaker` | `IAOCircuitBreaker` | NullIAO, ONNX / XGBoost | Real-time inner-loop risk evaluation and early stopping. |
| `IAOSurrogateEvaluator`| `IAOSurrogateEvaluator`| NullIAO, GBDT Ranker | Outer-loop mutation candidate filtering prior to benchmark runs. |

---

## Chapter 3: Inner Loop & Execution Mechanics (DMARTIC & Agent Loop)

### 3.1 The Formalized Agent Loop
Each step within an orchestrator node follows an explicit 5-stage loop:
1. **Context Assembly**: Gather short-term history, relevant long-term memory, indexed code snippets, knowledge graph facts, and current plan instructions.
2. **Model Invocation**: Call the designated LLM with structured tools and system instructions.
3. **Response Parsing**: Parse natural language, structured JSON tool calls, or state updates.
4. **Tool Dispatch**: Route calls through `PolicyEngine.authorize()` and dispatch to `ToolRegistry` (MCP/local).
5. **Observation & State Update**: Log raw outputs to trajectory store, update short-term memory, and evaluate step transition.

### 3.2 The 9-Stage DMARTIC Cycle
```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DMARTIC INNER LOOP CYCLE                          │
│                                                                             │
│  [1. Concept] ──► [2. Design] ──► [3. Measure] ──► [4. Analyze]             │
│        ▲                                                   │                │
│        │                                                   ▼                │
│  [9. Self-Reflect] ◄── [8. Control] ◄── [7. Improve] ◄── [6. Test] ◄── [5. Review]│
└─────────────────────────────────────────────────────────────────────────────┘
```
1. **Concept**: High-level goal formulation and goal decomposition.
2. **Design**: Architectural design, sub-agent assignment, falsifiable hypothesis generation.
3. **Measure**: Collecting baseline metrics (test pass counts, AST complexity, code churn).
4. **Analyze**: Root-cause analysis using scientific abduction.
5. **Review (Plan Mode)**: Structured plan generated (files to edit, shell commands to run) and presented for Socratic human/policy approval before destructive edits.
6. **Test**: Execution within isolated Git Worktree sandboxes.
7. **Improve**: Patch generation, syntax verification (`ast.parse`), and refactoring.
8. **Control**: Evaluating circuit breaker rules (AST oscillation, test stagnation, AOI risk).
9. **Self-Reflect**: Summarizing execution traces into Long-Term Memory axioms.

### 3.3 Extensibility & Memory Compaction
- **Skills**: Reusable, versioned instruction + tool packages loaded from `skills/` or MCP.
- **Plugins & Hooks**: Lifecycle hooks (`pre_tool`, `post_tool`, `pre_plan`, `post_improve`) allowing interception without core code modification.
- **Dual-Strata Context Compaction**:
  - **Deterministic Execution Log**: Raw tool inputs, stack traces, and exit codes kept intact in SQLite/JSONL.
  - **Semantic Summary Stream**: Sliding-window LLM summarization stripping long stdout successes while preserving errors and stack traces.

---

## Chapter 4: Outer Loop & Recursive Harness Improvement (RHI)

### 4.1 Concept & Workflow
The Outer Loop operates asynchronously to evolve the harness infrastructure itself.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             OUTER LOOP (RHI)                                │
│                                                                             │
│   ┌──────────────┐     Mutation Diff     ┌──────────────┐                   │
│   │ MetaImprover │──────────────────────>│ Candidate    │                   │
│   │   (Agent)    │                       │ Harness Config│                  │
│   └──────┬───────┘                       └──────┬───────┘                   │
│          ▲                                      │                           │
│          │ Feedback                             │ Candidate Pruning         │
│          │ Scores                               ▼ via AOI (f_θ & UCB)       │
│   ┌──────┴───────┐                       ┌──────────────┐                   │
│   │ Hot-Swap     │<── Aceita/Rejeita ────│ Ray Cluster  │                   │
│   │ Deployment   │                       │ (Inspect AI) │                   │
│   └──────────────┘                       └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **Mutation Proposal**: `MetaImprover` proposes modifications $\mu(H) \rightarrow H'$ across system prompts, workflow graph definitions, policy rules, and tool descriptions.
2. **Candidate Ranking & Pruning**: The AOI Surrogate Reward Model ($f_\theta$) and UCB Exploration Ranker evaluate candidates, selecting only top $K$ promising variations.
3. **Parallel Held-Out Evaluation**: Selected candidates run in parallel across a Ray cluster against private benchmark suites (SWE-bench / Inspect AI) hidden from the improver agent.
4. **Safety & Regression Audit**: `Promptfoo` scans candidate configs for red-teaming vulnerabilities (OWASP LLM Top 10) and prompt regressions.
5. **Hot-Swap Promotion**: If $\mathbb{E}[\text{Score}(H')] > \mathbb{E}[\text{Score}(H)]$ with zero safety regressions, the kernel promotes the new configuration via zero-downtime hot-swap.

---

## Chapter 5: Statistical Control Plane: Auxiliary Optimization Intelligence (AOI)

### 5.1 Symbolic Reasoning Plane vs. Statistical Control Plane
- **Symbolic Reasoning Plane (Frontier LLMs)**: High latency, high cost, highly creative, deep reasoning.
- **Statistical Control Plane (AOI)**: Sub-millisecond latency, zero API token cost, local CPU GBDT/ONNX execution.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SYMBOLIC REASONING PLANE                              │
│              Super-Orchestrator LLM & Specialized Agents                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Telemetry & Action Props
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    STATISTICAL CONTROL PLANE (AOI)                          │
│  ┌──────────────────────┐ ┌──────────────────────┐ ┌─────────────────────┐  │
│  │ Surrogate Reward f_θ │ │ Failure Risk g_φ     │ │ UCB Candidate Rank  │  │
│  └──────────┬───────────┘ └──────────┬───────────┘ └──────────┬──────────┘  │
│             └────────────────────────┼────────────────────────┘             │
│                                      ▼                                      │
│                      Local Feature Store (DuckDB / SQLite)                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Control Signals (Prune, Halt, Approve)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                       META-HARNESS KERNEL ENFORCEMENT                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Mathematical Specifications

#### 1. Surrogate Reward Predictor ($f_\theta$)
Approximates the held-out benchmark score $R(\tau) \in [0, 1]$ from proposed harness diff features $x_\tau$:
$$f_\theta(x_\tau) \approx \mathbb{E}[R(\tau) \mid x_\tau]$$
Proposals with $f_\theta(x_\tau) < \theta_{\min}$ are rejected prior to expensive benchmark runs.

#### 2. Early-Stopping Failure Predictor ($g_\phi$)
Evaluates trajectory failure risk at inner-loop step $t$:
$$g_\phi(x_{\tau \le t}) = P(\text{Trajectory Failure} \mid \text{State at step } t)$$
Triggers `CircuitBreakerException` when $g_\phi > \gamma_{\text{risk}}$, halting doomed execution loops.

#### 3. UCB Exploration Candidate Ranker
Ranks harness configurations $c \in \mathcal{C}$ balancing reward estimation, exploration variance, and token cost:
$$\text{Score}(c) = \hat{\mu}(c) + \alpha \sqrt{\frac{\ln N}{N_c + 1}} - \lambda \cdot \mathbb{E}[\text{Cost}(c)]$$
- $\hat{\mu}(c)$: Estimated reward from $f_\theta$.
- $N$: Total outer-loop evaluations.
- $N_c$: Evaluations completed for configuration $c$.
- $\lambda$: Lagrangian multiplier for token/latency cost penalty.

### 5.3 Feature Vector Engineering ($x_\tau \in \mathbb{R}^d$)
- **Code Churn**: Lines added/deleted, AST node delta, file edit entropy.
- **Execution State**: Consecutive tool errors, test pass ratio delta ($\Delta \text{Pass}$), stack trace depth.
- **Token Dynamics**: Token consumption velocity (tokens/step), context fill ratio (%).
- **Dependency Graph**: Graph centrality of modified files, coupling coefficient.
- **Tool Usage**: Shell exit code frequencies, MCP response latency.

### 5.4 Pragmatic Rollout & Deterministic Alternatives
When operating without ML models initially:
- **NullIAOAdapter**: Implements `IAOCircuitBreaker` and `IAOSurrogateEvaluator` returning default safe passes while logging telemetry to DuckDB/SQLite.
- **AST Hash Ring**: Hash SHA-256 of ASTs across steps. If $H(\text{AST}_t) \in \{H(\text{AST}_{t-1}), \dots, H(\text{AST}_{t-k})\}$, halt immediately due to code oscillation.
- **Test Stagnation Rule**: If unit test pass percentage fails to increase over $K$ iterations, trigger circuit breaker.
- **Consecutive Error Limit**: Halt if tool exit code $\ne 0$ for 3 consecutive steps without code changes.

---

## Chapter 6: Protocols, Workspace Isolation & Scaled Orchestration

### 6.1 Model Context Protocol (MCP) & Agent-to-Agent Protocol (A2A)
- **MCP (Model Context Protocol)**: Client-server JSON-RPC 2.0 application-layer protocol. Standardizes access to:
  - **Tools**: Executable functions with JSON Schema validation.
  - **Resources**: Readable file/database URI data sources.
  - **Prompts**: Parameterized prompt templates.
- **A2A (Agent-to-Agent Protocol)**: Peer-to-peer inter-agent coordination standard. Defines:
  - **Agent Cards**: Standardized JSON descriptors of agent capabilities, roles, and endpoints.
  - **Task Cards**: Stateful contracts tracking task assignment, progress state, and artifact handoffs.

### 6.2 Workspace Isolation via Git Worktrees
```python
class WorktreeManager(Protocol):
    async def create(self, base_ref: str = "HEAD") -> WorktreeHandle: ...
    async def apply(self, handle: WorktreeHandle) -> None: ...
    async def discard(self, handle: WorktreeHandle) -> None: ...
```
- Each parallel sub-agent runs inside its own isolated Git Worktree sharing the root `.git` object store.
- Zero-copy cloning with instant context switching; zero file edit collisions.
- Sequential merge/rebase driven by a dedicated Integration Agent with regression testing.

---

## Chapter 7: Scientific Epistemology & Metacognitive Reasoning

### 7.1 Popperian & Peircian Scientific Cycle
The agent applies formal scientific inquiry (Abduction $\rightarrow$ Deduction $\rightarrow$ Experimentation $\rightarrow$ Induction):

```text
    ┌──────────────┐      Abdução      ┌──────────────┐
    │ Observação de│──────────────────>│ Hipótese de  │
    │ Falha / Erro │                   │ Causa Raiz   │
    └──────────────┘                   └──────┬───────┘
           ▲                                  │
           │ Indução                          │ Dedução
           │                                  ▼
    ┌──────────────┐     Execução      ┌──────────────┐
    │ Atualização  │<──────────────────│ Experimento/ │
    │ do Conhecim. │                   │ Teste Mínimo │
    └──────────────┘                   └──────────────┘
```

1. **Abduction (Epistemic LLM)**: Formulates root-cause hypothesis $H$ from observed build/test failure logs.
2. **Deduction (Design LLM)**: Designs minimal unit test case $T$ capable of falsifying hypothesis $H$.
3. **Experimentation (Harness Core)**: Executes test $T$ within an isolated Git Worktree sandbox via MCP.
4. **Induction (Metacognitive LLM)**: Extracts general rule (**Learned Axiom**) and saves to Long-Term Memory (LTM).

### 7.2 Multi-LLM Role Specialization
- **Worker LLM**: Code generation, patch application, MCP tool execution.
- **Epistemic LLM**: Root-cause analysis, hypothesis generation, test design.
- **Metacognitive LLM (Process Architect)**: Dynamic DAG compilation, system prompt refinement, workflow optimization.
- **Evaluator Judge LLM**: Applies rubrics, calculates Process Reward Model (PRM) scores per step.

---

## Chapter 8: Technology Stack & Tooling Ecosystem

### 8.1 Technology Stack Layering

| Layer | Primary Technology | Key Capabilities & Rationale |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.12+ / Pydantic v2 | Async-first (`anyio`/`asyncio`), strict `typing.Protocol` contracts. |
| **Inner Loop Engine** | LangGraph | StateGraph cyclic execution, PostgresSaver checkpoints, Time-Travel. |
| **Durable Infrastructure**| Temporal.io / Cadence | Event Sourcing durable execution; survives server crashes across weeks. |
| **Cluster Scaling** | Ray | `@ray.remote` actor model for mass parallel outer-loop benchmark runs. |
| **Tool Protocol** | Model Context Protocol (MCP) | Open JSON-RPC 2.0 standard for tool exposure. |
| **Agent Protocol** | A2A Protocol | P2P agent discovery, Agent Cards, Task Card state contracts. |
| **Workspace Isolation** | Git Worktrees | Zero-copy concurrent branch isolation without Docker spin-up overhead. |
| **Memory & Database** | SQLite (`sqlite-vec`) + LanceDB | Relational transactional persistence + high-speed vector embeddings. |
| **Telemetry Analytics** | DuckDB | In-process columnar OLAP for sub-millisecond AOI telemetry feature extraction. |
| **Knowledge Graph** | NetworkX / Neo4j | Code structure, AST call-graphs, entity-relation mappings. |
| **Indexing Engine** | LlamaIndex / GraphRAG | Hierarchical AST chunking and graph-guided code retrieval. |
| **Evaluation Frameworks** | UK AISI Inspect AI + SWE-bench | Dynamic sandboxed evaluation of complex agents on real GitHub issues. |
| **Security & Prompt CI** | Promptfoo | Declarative YAML red-teaming and OWASP LLM Top 10 vulnerability scanning. |
| **Local ML Inference** | XGBoost / LightGBM / ONNX | Microsecond GBDT inference on CPU for AOI surrogate risk and reward models. |

---

## Chapter 9: Multi-Week Autonomous Execution Blueprint (Case Study)

### Scenario: Refactoring a 500,000 LOC Python Monolith to AWS CDK Microservices (3-Week Run)

```text
SEMANA 1: Durable Init & Knowledge Mapping
┌─────────────────────────────────────────────────────────────────────────────┐
│ • Temporal.io registers durable workflow execution.                         │
│ • GraphRAG & LlamaIndex construct Neo4j Knowledge Graph & sqlite-vec LTM.   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
SEMANA 2: Parallel Worktrees & Inner-Loop DMARTIC Cycles
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ • Super-Orchestrator spawns 4 sub-agents via A2A protocol.                  │
│ • Sub-agents work in parallel branches via Git Worktrees.                   │
│ • LangGraph drives DMARTIC cycles; MCP executes build tools.                │
│ • AST Hash Ring & AOI g_phi detect loops -> trigger Time-Travel rollback.   │
│ • Context Assembly Engine compacts STM windows, retaining stack traces.     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
SEMANA 3: Outer-Loop Meta-Improvement & Final Reintegration
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ • MetaImprover proposes 20 harness prompt/graph mutations.                  │
│ • AOI f_theta & UCB ranker select top 2 candidates.                         │
│ • Ray cluster runs Inspect AI / SWE-bench on held-out validation suite.     │
│ • Winner promoted via hot-swap; Promptfoo verifies zero security regression.│
│ • Integration Agent rebases branches, runs E2E tests, submits clean PR.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Chapter 10: Definitive Technical Quick-Reference Matrix

| Category | Technology / Concept | Classification | Primary Strengths | Weaknesses & Alternatives | PhD-Level Technical Summary | Tool Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Orchestration** | **LangGraph** | Cyclic State Graph | Native state persistence, Time-Travel, step checkpointing. | Single-process bound; Alt: Temporal, AutoGen. | Directed StateGraph $G=(V,E)$ over typed schemas with deterministic transition function $\delta: S \times V \rightarrow S \times V$. | SAGIHA, LangChain |
| **Orchestration** | **Temporal.io** | Durable Execution | Rebuilds exact execution stack after hardware failure. | Verbose setup; Alt: AWS Step Functions, Airflow. | Event Sourcing engine reconstructing process memory from immutable event logs in DB. | SAGIHA, Uber |
| **Orchestration** | **Ray** | Distributed Computing | Massively parallel actor execution across clusters. | Complex state management; Alt: Celery, Dask. | Actor-model distributed runtime with dynamic task graphs (`@ray.remote`). | SAGIHA, OpenAI |
| **Protocols** | **MCP** | Tool Protocol Standard | Open client-server standard for tools/resources. | JSON-RPC payload overhead; Alt: Native function calling. | Application-layer JSON-RPC 2.0 protocol defining JSON Schema tool contracts. | SAGIHA, Anthropic |
| **Protocols** | **A2A** | Agent Protocol Standard | Structured peer negotiation via Agent Cards. | Requires strict schema maintenance; Alt: Free text. | Peer-to-peer task lifecycle protocol with cryptographic state validation. | SAGIHA, Industry |
| **Workspace** | **Git Worktrees** | Isolation Primitive | Zero-copy parallel working directories. | Directory GC required; Alt: Docker, Podman. | Multiple working trees attached to a single shared `.git` object database. | SAGIHA, Grok Build |
| **Control** | **AOI Core** | Statistical Control Plane | Sub-millisecond inference, zero token cost. | Requires initial telemetry data; Alt: Rule-based. | Non-symbolic control system over feature vector $x_\tau \in \mathbb{R}^d$ using GBDTs in ONNX runtime. | SAGIHA |
| **Control** | **AST Hash Ring** | Deterministic Circuit Breaker | Zero latency, 100% deterministic loop detection. | Misses semantic loops; Alt: Embedding distance. | SHA-256 ring buffer of AST structures checking $H(\text{AST}_t) \in \{H(\text{AST}_{t-k})\}$. | SAGIHA |
| **Evaluation** | **Inspect AI** | Agent Evaluation Harness | Async agent evaluation in sandboxed environments. | High learning curve; Alt: DeepEval, Ragas. | Async evaluation framework structuring tests into Datasets, Solvers, and Scorers. | UK AISI, SAGIHA |
| **Evaluation** | **SWE-bench** | Coding Benchmark | Real GitHub issues evaluated via test patches. | Heavy execution cost; Alt: HumanEval, MBPP. | Closed test dataset measuring functional patch output against hidden regression suites. | Cognition, SAGIHA |
| **Evaluation** | **DeepEval / Ragas** | RAG / G-Eval Judge | Calibrated faithfulness, hallucination metrics. | High API cost; Alt: Promptfoo, TruLens. | G-Eval metrics decomposing text into atomic claims evaluated by instruction LLMs. | SAGIHA, RAG CI |
| **Evaluation** | **Promptfoo** | Red-Teaming & Fuzzing | Ultra-fast YAML declarativity; OWASP security scanning. | Poor multi-agent state tracking; Alt: Lakera. | Static and dynamic fuzzing scanner evaluating responses against regex and semantic assertions. | DevOps CI, SAGIHA |
| **Evaluation** | **lm-eval-harness** | Base LLM Benchmark | Industry gold-standard for MMLU/GSM8K leaderboards. | Static Q&A only, no tool execution; Alt: Lighteval. | Low-level log-likelihood calculation framework over multiple inference backends. | Hugging Face |
| **Memory** | **DuckDB** | Telemetry OLAP | Ultra-fast in-process columnar queries over logs. | Single-node limit; Alt: ClickHouse, PostgreSQL. | Vectorized columnar OLAP execution engine operating directly on Parquet/JSONL. | SAGIHA, Databricks |
| **Memory** | **SQLite (sqlite-vec)**| Local Relational OLTP | In-process transactional state + vector search. | Scaling requires multi-node layers; Alt: Qdrant. | In-process B-Tree transactional relational engine extended with vector distance indexes. | SAGIHA, Local-First |

---

## Chapter 11: Master Curriculum & Phased Implementation Roadmap

### 11.1 Master's-Level Syllabus Overview
- **Module 1: Infrastructure & Durable Isolation**: Temporal.io event sourcing, Git Worktrees, MCP server setup, Pydantic/Protocol clean interfaces.
- **Module 2: Inner Loop Governance & Epistemology**: LangGraph StateGraph, DMARTIC 9-stage cycle, Popperian hypothesis generation, AST Hash Ring, Process Reward Models.
- **Module 3: Statistical Control & Telemetry**: DuckDB feature store, XGBoost failure prediction ($g_\phi$), ONNX model compilation, NullIAO fallback adapters.
- **Module 4: Outer Loop & Recursive Self-Improvement**: MetaImprover proposal generation, Surrogate Reward Model ($f_\theta$), Ray cluster scaling, Inspect AI private held-out benchmark evaluation, zero-downtime hot-swapping.

### 11.2 Phased Evolutionary Implementation Plan

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASED IMPLEMENTATION ROADMAP                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ FASE 1: Core Clean Hexagonal Harness ]                                   │
│  • Define stable Python Protocols (`ports/`) for Workspace, Memory, Tools.  │
│  • Build DMARTIC engine on LangGraph + MCP + Git Worktrees.                 │
│  • Passive telemetry logging to SQLite/DuckDB + NullIAOAdapter.             │
│                                                                             │
│  [ FASE 2: Multi-Agent Collaboration & Resilience ]                         │
│  • A2A Protocol for inter-agent task delegation.                            │
│  • Independent Evaluator (Anthropic 3-agent pattern) & PRM quality gates.   │
│  • Deterministic circuit breakers (AST Hash Ring, Test Delta ΔPass).        │
│                                                                             │
│  [ FASE 3: Statistical Control & Outer-Loop Self-Evolution ]                │
│  • Train XGBoost/CatBoost models on accumulated telemetry logs.             │
│  • Swap NullIAOAdapter with ONNX GBDT adapters (f_θ and g_φ).               │
│  • Activate Outer-Loop RHI under held-out Inspect AI / SWE-bench validation.│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.3 Concluding Statement
The transformation of a standard LLM into an **Autonomous General Systems Agent (AGI)** is achieved not by scaling parameters alone, but by enclosing the LLM inside a **dual-loop hexagonal harness**. The Inner Loop provides runtime control, deterministic safety boundaries, and scientific self-correction. The Outer Loop provides continuous, empirical self-evolution of the harness infrastructure under held-out validation. This architecture enables AI agents to operate autonomously for weeks on end, delivering verified, production-grade software engineering.
