---
status: advisory
date: 2026-07-30
title: "SOTA Harness Infrastructure: Architecture, Decision Matrix & Path to Shipping"
---

# **SAGIHA — SOTA Harness Infrastructure Improvement Plan**

> **Purpose**: Describes the path from SAGIHA's architectural specification to a shipped, measurable SOTA (State-of-the-Art) AI Coding Harness that pairs a frontier LLM with a deterministic, capability-gated, sandboxed execution environment. This document synthesizes competitive analysis, internal audits, and concrete engineering recommendations—organized by criticality, not by complexity.
>
> **SOTA Definition**: Not a prompt wrapper or script loop. A fully autonomous software engineering **control plane** with (1) the **macro workflow** ("dbt for agent logic": PRD → stories → DMARTIC inner loop → gate → merge); (2) **dual-process execution** (System 1 ReAct for single-file edits, System 2 best-of-N for multi-file refactoring); (3) **structural capability security** (unforgeable Grant tokens at a single dispatch choke point); (4) **deterministic replay** (100% byte-identical cassette record/replay in CI with zero network I/O); and (5) **measurement-first evaluation** (A/A noise floor, pristine injected tests, `tests_unmodified` as a hard gate).

---

## 1. 🎯 **Intentional Minimalism: Why SAGIHA Rejects High-Complexity Features**

SAGIHA's thesis is that **SOTA is achieved through depth in a few critical dimensions, not breadth across many**. Based on analysis of four shipping harnesses, SAGIHA explicitly rejects six tempting features that damage SOTA properties:

### A. Universal Model Abstraction Wrappers (LiteLLM) — ❌ Rejects
* **Cost to SOTA**: Breaks prompt-cache prefix-locking (the single largest cost lever). Heavy wrapper overhead prevents deterministic replay.
* **Found in**: OpenHands, Hermes Agent.
* **Why they chose it**: Marketing—support any LLM vendor.
* **SAGIHA instead**: Native SDKs (Anthropic, OpenAI) + one `base_url` adapter for Ollama/vLLM. **Result**: Zero wrapper overhead, locked cache prefixes, 100% replay determinism.
* **ADR**: [ADR-0008: Native SDKs, No LiteLLM](../08-decisions/0008-native-sdks-no-litellm.md).

### B. Monte-Carlo Tree Search (MCTS) for Code Hypotheses — ❌ Rejects
* **Cost to SOTA**: Requires a value model before the agent can even run tasks. Cold-start bootstrap problem. At $0.10/token, one expansion = full agent run + test suite; tree search at that cost profile is irrational.
* **Found in**: Academic frameworks.
* **Why they chose it**: Theoretical guarantees.
* **SAGIHA instead**: **System-2 Best-of-N at depth one**: spawn 3 parallel worktrees, test all three, rank by the PRM score (when it exists), repair sequentially on failure. Far cheaper and empirically sufficient.
* **ADR**: [ADR-0005: Best-of-N, Not MCTS](../08-decisions/0005-best-of-n-not-mcts.md).

### C. External Graph & Vector Daemons (Neo4j / Qdrant / Milvus) — ❌ Rejects
* **Cost to SOTA**: Adds operational surface (sidecar management), adds token cost (LLM entity extraction), adds latency (network round trips), adds hallucination risk (extracted edges are unverified). **Breaks determinism** — two runs with different entity extraction produce different code graphs.
* **Found in**: Enterprise agent stacks.
* **SAGIHA instead**: Tree-sitter AST for **deterministic** symbol graphs (imports, definitions, call chains) + SQLite FTS5 for **lexical** search (grep on steroids). No daemon, no token cost, 90%+ recall.
* **ADR**: [ADR-0014: Defer Dense Retrieval](../08-decisions/0014-defer-dense-retrieval.md), [ADR-0011: Split Code & Episodic Graphs](../08-decisions/0011-split-code-and-episodic-graphs.md).

### D. Monolithic Query Engines & God Classes — ❌ Rejects
* **Cost to SOTA**: Impossible to test, painful to maintain, becomes a magnet for merge conflicts. Hermes's `cli.py` is 816KB of proof.
* **Found in**: Hermes Agent (`cli.py` ~20K LOC), Claude Code (`QueryEngine.ts` ~1.7K LOC).
* **SAGIHA instead**: **CAR three-layer architecture** (Control / Agency / Runtime) with hexagonal ports. Strict ~300–500 LOC per file enforced by layer contracts and `import-linter`.
* **Consequence**: DMARTIC loop is testable at day one. Ports are wireable over JSON-RPC or gRPC. No single choke point is more than 100 lines.

### E. Unbounded Tool Outputs — ❌ Rejects
* **Cost to SOTA**: Raw shell dumps blow context windows, spike token costs, destroy long-horizon planning.
* **SAGIHA instead**: **Paginated reads** (`read_file_max_lines=2000`), **structured truncation** with `truncated: true`, **output handle offloading**. The model always sees the structure; large payloads stream to a sidecar.
* **Result**: Context is predictable, token spend is bounded, long-horizon runs work.

### F. Premature Peripheral Machinery (MCP, OTel, AOI, RHI) — ⏸️ Defers
* **Cost to SOTA**: Machinery that seems required is often not. Telemetry, background coprocessors, and plugin servers absorb engineering effort *before the core loop works*. Classic over-engineering.
* **SAGIHA decision**: **Close the core DMARTIC loop first** (Sprint 3). Only then add sidecars, observability, and outer loops as measurement justifies them.
* **Block Sequencing**: S0 (runnable loop) → E0 (evaluation harness) → S1 (gates shipping) → S2 (RHI outer loop for harness tuning) → S3+ (periphery).

---

### 📊 **Summary Matrix: Competitors vs. SAGIHA**

| Feature | Competitor Approach | SAGIHA Approach | Complexity Saved |
| :--- | :--- | :--- | :--- |
| **Model Provider** | Universal wrappers (LiteLLM) | Native SDKs + `base_url` adapter | 🚫 No heavy wrapper dependencies |
| **Code Indexing** | External Vector / Graph DBs | Tree-sitter AST + FTS5 SQLite | 🚫 No sidecar daemons (Neo4j/Qdrant) |
| **Parallel Search** | MCTS / Graph Search | Git Worktrees + Gate Verification | 🚫 No complex value-network estimation |
| **Code Base Size** | Monolithic files (800KB) | Decoupled Ports (<500 LOC/file) | 🚫 High testability, zero merge hell |
| **Tool Outputs** | Raw shell dumps | Paginated, handle-offloaded buffers | 🚫 No blown context windows |

---

## 2. 🔍 **Critical Audit of SAGIHA: Overengineering vs. Core Verification**

The [2026-07-29 Foundation Review](./2026-07-29-foundation-review.md) revealed that SAGIHA’s main initial flaw was **over-specifying the periphery before proving the core**:

1. **Architecture & Extensibility**: SAGIHA defined 21 typed ports and 74 docs before having a single working tool-call loop.
   * *Fix*: Freeze port expansion until an adapter exists. Keep only the 5 mandatory ports for Block 1 ([Sprint 3](../sprints/sprint-3.md)): `ModelProvider`, `Workspace`, `PolicyEngine`, `ResourceGovernor`, `TrajectoryStore`.
2. **Memory & History**: The codebase had 3 separate memory concepts (`ShortTermMemoryAdapter`, `TrajectoryStore`, and `InMemoryMemory`), yet steps were executed memoryless.
   * *Fix*: Use `TrajectoryStore` as the single authoritative source of step history; defer complex graph memory to Block 4.
3. **Security**: Early code minted capability `Grant` objects and tracked concurrent leases, but `dispatch.py` never verified grant expiration and key-name guessed file paths.
   * *Fix*: Write explicit fail-closed security behavioral tests (Sprint 3 §C) and enforce explicit schema-declared path scoping.
4. **Evaluation Rigidity**: `Evaluator` assumed machine-checkable `check` commands (`pytest`, `mypy`).
   * *Fix*: Explicitly classify non-code or conversational tasks as unverified in telemetry, keeping benchmark numbers honest.
5. **Execution Flow & Event Bloat**: 32 event subclasses led to schema overhead.
   * *Fix*: Focus events on core milestones (`ModelCallStarted`, `ToolCallRequested`, `ToolCallCompleted`, `GateEvaluated`) and pass details in structured payloads.

---

## 3. 🌐 **Universality & Protocol Support Matrix**

SAGIHA is explicitly designed to be universal across wire protocols, guaranteed by its [Remoteable Ports Architecture](../02-architecture/remoteable-ports.md):

* **100% Async Methods**: Every method on every port is `async def`.
* **Pure Pydantic Payloads**: No raw file handles, `Path` objects, callbacks, or un-serializable objects cross port boundaries.
* **JSON-Serializable Data**: All arguments and return values can be serialized to JSON natively.

| Protocol | Support Status | How SAGIHA Handles It |
| :--- | :--- | :--- |
| **OpenAI API** | **Native** | The `ModelProvider` port connects to Anthropic, OpenAI, Ollama, vLLM, and OpenRouter via OpenAI-compatible `base_url` endpoints. |
| **MCP (Model Context Protocol)** | **Native** | Tools register via JSON Schemas; SAGIHA can both **consume** external MCP tool servers and **expose** its internal tools as an MCP server ([protocols-mcp-a2a.md](../03-contracts-and-models/protocols-mcp-a2a.md)). |
| **JSON / REST / A2A** | **Native** | Agent-to-Agent (A2A) protocol and HTTP REST triggers wrap `RunLoop` inputs/outputs directly using Pydantic JSON serialization. |
| **gRPC / Protobuf** | **Seamless Adapter** | Because port signatures are strictly typed Pydantic models, a gRPC service wrapper can be generated with minimal boilerplate. |

---

## 4. 🧩 **Senior-Engineering Workflow Orchestration ("dbt for Agent Logic")**

To treat every task as a deterministic, composable engineering pipeline (*Prompt → PRD Specs → Epic / Story Board → Pick Story → Implement → Verify → Progress Log → Repeat*), SAGIHA defines a native, decoupled orchestration framework:

### Reusable Workflow Protocol Abstraction
Rather than importing third-party frameworks like LangChain or LangGraph (which introduce control-flow hijacking, breaking API changes, and prompt cache invalidation), SAGIHA uses native Python 3.13 abstractions (`typing.Protocol` + Pydantic + `anyio`):

```python
# Reusable base abstraction for any workflow box
class WorkflowStep[In: BaseModel, Out: BaseModel](Protocol):
    name: str
    async def execute(self, ctx: RunContext, input_data: In) -> Out: ...

# Reusable pipeline runner (the "dbt for agent logic")
class PipelineRunner:
    def __init__(self, steps: list[WorkflowStep]): ...
    async def run(self, ctx: RunContext, initial_input: BaseModel) -> PipelineResult: ...
```

### Decoupled Execution Stages
* `PRDGeneratorStep`: Takes prompt → outputs `PRDSpec`.
* `StoryDecomposerStep`: Takes `PRDSpec` → outputs `StoryBoard` with user stories.
* `CodingStep`: Takes `StorySpec` → executes inner `DMARTIC` loop.
* `VerificationStep`: Takes code diff → runs `Evaluator` pristine tests.

### Obsidian-Style Knowledge Net (Bi-Temporal Memory)
Long-term episodic memory is modeled as an **Obsidian-style Knowledge Net** ([neural-symbolic-memory.md](../02-architecture/neural-symbolic-memory.md)):
* `MemoryRecord` carries `links: tuple[str, ...]` connecting decisions, episodes, and rules into a graph.
* Supports **Neighborhood queries** (*"what decisions/episodes connect to this module?"*) and **Backlinks** (*"what beliefs depend on this decision?"*).
* **Code facts** (imports, call graph) are derived deterministically via Tree-sitter AST, while **learned facts** live in the linked Knowledge Net.

---

## 5. 🟢 **Audit of Staged Doc Changes & Immediate Action Plan**

### What is GOOD in Current Staged Changes (`git diff --cached`)
1. **Grounded Getting-Started Guide** ([getting-started.md](../06-guides-and-patterns/getting-started.md), [v0.1-user-guide.md](../01-executive/v0.1-user-guide.md)): Splits today's working verification (`pyright`, `lint-imports`, `pytest tests/contracts/`, `sagiha version`) from Sprint 3 deliverables (`sagiha run`, `sagiha replay --verify`).
2. **Added `docs/STATUS.md`**: Provides a single source of truth mapping implementation defects D1–D18 directly to [Sprint 3](../sprints/sprint-3.md).
3. **Roadmap Realignment** ([phased-migration-matrix.md](../07-roadmap/phased-migration-matrix.md)): Correctly sequences Block 1 (Sprint 3: Runnable Loop) → Block 2 (E0-lite Measurement) → Blocks 3–5 (Authority, Retrieval, Sandbox/MCP/OTel).

### Actionable Doc Improvements Before Finalizing
1. **Stage Reference Files**: Stage all untracked/modified reference analysis files (`git add docs/reference/`).
2. **Add Workflow Orchestration Spec**: Add `docs/04-workflows-and-loops/workflow-orchestration-and-dags.md` defining `WorkflowStep` & `PipelineRunner` protocols to make "dbt for logic" explicit.
3. **Expand Story Lifecycle**: Update [task-and-acceptance.md](../03-contracts-and-models/task-and-acceptance.md) with `PRDSpec` and `StoryBoard` lifecycle schemas.
