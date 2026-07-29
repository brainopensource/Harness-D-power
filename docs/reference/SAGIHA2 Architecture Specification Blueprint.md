# **Engineering Specification and Research Brief: SOTA Meta-Harness and Infrastructure for Autonomous LLM Coding Agents (SAGIHA2)**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a proposed architecture and architectural blueprint for the Meta Harness CoderAGI, not an imperative or immutable final solution. Further iterative prototyping, benchmarks, and practical evaluations will be conducted to refine and finalize the ultimate harness structure.

## **Ecosystem Benchmarking and Theoretical Infrastructure Analysis**

Autonomous Large Language Model (LLM) coding agents have advanced beyond basic prompt-wrapping execution loops to multi-tiered, stateful software engineering runtimes. Designing a production-grade, hexagonal Meta-Harness requires evaluating modern open-source agent frameworks, dynamic graph memory architectures, mathematical vector quantization techniques, and emerging inter-agent communication standards.

### **Agent Control Planes and Harness Paradigm Evaluation**

Current software agent control planes exhibit fundamental differences in state representation, execution loops, tool dispatch pipelines, and code isolation mechanisms. Evaluating these paradigms reveals critical trade-offs between architectural flexibility, state isolation, and token efficiency.

| Framework / Paradigm | Control Loop Paradigm | State Management Architecture | Tool Dispatch Pipeline | Sandbox & Isolation Strategy | Worktree & Parallel Branching |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **OpenHands** | Event-Stream Orchestration | Stateful Event Log with step replay and state checkpointing | Non-blocking asynchronous event bus with streaming terminal standard IO | Containerized Docker execution runtime with gVisor sandbox | Ephemeral git branches with manual workspace state synchronization |
| **SWE-agent** | Agent-Computer Interface (ACI) Loop | Linear trajectory storage with action-observation step history | Synchronous bash tool execution with custom file view/edit utilities | Isolated Docker container execution instance per trajectory | Single repository clone per evaluation run |
| **Agentrail** | Local Control Plane & Scaffolding | Repository-centric state anchored to filesystem context1 | Asynchronous IPC and TUI event streaming2 | Host process or local virtual environment execution2 | Git workspace management via local control plane1 |
| **OpenHarness** | Minimalist Deterministic Loop | Ephemeral in-memory context window with explicit context compaction | Direct synchronous function calling with streaming tool output | Local process sandbox or light container isolation | Direct filesystem manipulation on active working branch |
| **Grok Build Paradigms** | High-Throughput ReAct Engine | Multi-turn Key-Value (KV) cache optimized state retention | Low-latency non-blocking tool dispatch pipelines | Containerized execution runtimes | In-memory code delta tracking with git commit staging |
| **Aider** | Git-Centric Interactive Edit Loop | In-memory Abstract Syntax Tree (AST) symbol graph and active commit index | Synchronous block-edit tool dispatch with git auto-commit hooks | Direct host working directory execution | Direct git integration with automatic commit-per-change policy |

In frameworks like SWE-agent and Aider, a primary bottleneck stems from the tight coupling between the reasoning loop and the active file system directory. Synchronous, block-based file modifications hinder parallel hypothesis testing and multi-branch exploration. In contrast, OpenHands demonstrates that event-stream architectures decouple agent decision-making from execution runtimes. However, state synchronization overhead during long-horizon tasks can cause context degradation if event logs grow unboundedly.  
The SAGIHA2 operational model synthesizes these paradigms into a decoupled Control-Agency-Runtime (CAR) architecture. It leverages event-stream orchestration from OpenHands, repository-level symbol mapping from Aider, trajectory tracking from SWE-agent, and multi-branch isolation through native Git worktrees.

### **Graph-Backed Memory Architectures and Knowledge Topologies**

Flat vector retrieval mechanisms frequently fail to capture structural code dependencies, temporal evolutionary changes, and cross-file ownership boundaries across complex enterprise repositories. Mapping modern software codebases requires combining Abstract Syntax Trees (ASTs), Architectural Decision Records (ADRs), git blame topologies, and bi-temporal knowledge graphs.  
Graphiti—the engine powering Zep's temporal context graph architecture—introduces a bi-temporal data model that explicitly records both valid time (when a fact was true in the real-world software system) and transaction time (when the agent ingested the fact)4. In dynamic software development, where continuous refactoring invalidates prior design decisions, temporal edge invalidation prevents the system from retrieving obsolete API signatures or outdated class structures4.  
Formally, an edge `e = (u, r, v)` asserting relationship `r` between entities `u` and `v` carries two independent intervals: a **validity interval** `[valid_from, invalid_at)` recording when the fact held in the modelled system, and an **ingestion interval** `[ingested_at, retracted_at)` recording when the system believed it. When a mutation event `m` is observed at time `t`, any pre-existing edge `e'` inconsistent with `m` is invalidated by setting `e'.invalid_at = t`, and a successor edge `e''` is created with `e''.valid_from = t`. Retrieval as-of time `τ` selects edges satisfying `valid_from ≤ τ < invalid_at`, which is what prevents obsolete API signatures and superseded design decisions from re-entering context.

Note the scope limit established in the memory module: this machinery applies to **learned, contestable facts**. Code structure is not modelled this way, because git already records both time axes — valid time is commit time, transaction time is index time — and structure re-derives exactly at any ref.
Graphiti avoids expensive LLM-in-the-loop reranking during retrieval by executing vector similarity, keyword full-text search, and temporal graph traversals within a single compiled query execution step5. Empirical evaluations on the LongMemEval benchmark demonstrate that temporal context graphs achieve up to 18.5% higher retrieval accuracy with a 90% reduction in query latency compared to traditional vector-only or sliding-window agent memory systems6.  
To comprehensively index a codebase, SAGIHA2 unifies four distinct structural topologies into a single property graph deployed on Neo4j or FalkorDB4:

> * **AST Dependency Graph**: Tracks module imports, class inheritance hierarchies, function call graphs, variable definitions, and interface implementations generated via Tree-sitter parsers.  
> * **Architectural Decision Map**: Formulates a directed acyclic graph connecting high-level system requirements, ADR markdown files, pull request rationales, and architectural module boundaries.  
> * **Code Ownership Topology**: Maps git blame metadata to contributor nodes, calculates module volatility metrics, and tracks historical co-change coupling scores across files.  
> * **Temporal Context Graph**: Captures agent execution trajectories, conversational turns, tool outputs, dynamic edge invalidations, and active workspace mutations in real time4.

### **Vector Search and Online Quantization Mechanics**

Repository indexing for multi-million-line codebases with high-dimensional vector embeddings (such as 1536-dimensional or 3072-dimensional embeddings) incurs substantial memory footprints and high search latencies. Standard Scalar Quantization (SQ8) achieves 4x memory compression with minimal recall drop, but cannot compress below 8 bits per dimension without loss of precision8. Traditional Product Quantization (PQ) achieves higher compression ratios but requires offline codebook training over static data, making it ill-suited for rapidly evolving repositories undergoing continuous commits8.  
TurboQuant (Zandieh et al., ICLR 2026\) addresses this challenge via a data-oblivious, online vector quantization algorithm that achieves optimal theoretical distortion rates without offline codebook pre-training9.  
The TurboQuant algorithm operates via a two-stage vector transformation pipeline10:  
First, an input vector `x ∈ ℝᵈ` undergoes a random orthogonal transformation `x̃ = Rx`, where `R` is generated efficiently via a Randomized Walsh-Hadamard Transform. This rotation spreads variance evenly across coordinates, driving the marginal distribution of each coordinate toward a concentrated Beta form and removing the axis-alignment that scalar quantizers otherwise suffer from.

Stage 1 then applies coordinate-wise Lloyd-Max scalar quantization `q(x̃)` using centroids precomputed for the unit sphere, yielding the compressed representation. Because MSE-optimal quantizers introduce **bias** in inner-product estimation, Stage 2 applies a Quantized Johnson-Lindenstrauss transform to the residual `r = x̃ − q(x̃)` using a 1-bit sign projection `S`, capturing the residual's contribution without storing it.

The resulting unbiased estimator for the inner product of two vectors `x`, `y` is:

```
⟨x, y⟩ ≈ ⟨q(x̃), q(ỹ)⟩ + c · ⟨sign(Sr_x), sign(Sr_y)⟩
```

where `c` is a scalar derived from the expected residual norm. The first term supplies the bulk estimate from quantized coordinates; the second corrects the bias that quantization introduced.

> [!NOTE]
> **Adoption status**: deferred. At this system's corpus size (~10⁵–10⁶ vectors) an exhaustive SIMD scan completes in single-digit milliseconds, so quantization addresses a cost not yet incurred. Retained here for the day a measured latency or memory ceiling triggers it — at which point it is an adoption decision (LanceDB in-process, or Qdrant's existing TurboQuant engine) rather than an implementation project.  
Fast-TurboQuant optimizes this process further by replacing dense orthogonal rotations with a Rademacher phase inversion followed by a Fast Walsh-Hadamard Transform (FWHT), eliminating floating-point multiplications during preprocessing and yielding a 19.7x speedup under sequential execution15.

| Quantization Framework | Bit-Width per Dimension | Compression Factor | Codebook Pre-Training | Search Execution Speed | Inner Product Bias Mitigation | Target Runtime Environment |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Float32 Baseline** | 32-bit | 1x | None | Baseline | Exact Unbiased | Uncompressed In-Memory Search |
| **Scalar Quantization (SQ8)** | 8-bit | 4x | Min/Max Calibration | Fast | Minimal Bias | Low-latency Vector Databases8 |
| **Product Quantization (PQ)** | 2-bit to 4-bit | 8x to 16x | Required (K-Means Clustering) | Moderate | High Distortion at Low Bit-Widths | Static Enterprise Indexes8 |
| **TurboQuant (ICLR 2026\)** | 2.5-bit to 3.5-bit | 9.1x to 12.8x | **Data-Oblivious (Zero Training)** \[cite: 9, 10\] | Fast SIMD Kernels | **Unbiased via 1-bit QJL Residual** \[cite: 10, 11\] | Dynamic KV Caches & Real-time DBs8 |
| **Fast-TurboQuant** | 2-bit to 4-bit | 8x to 16x | **Data-Oblivious (Zero Training)** \[cite: 15\] | Multiplier-Free (FWHT)15 | Unbiased via Residual FWHT15 | Low-power Local Search Engines15 |
| **tqdb (Pure Go)** | 4-bit | 8x | Zero Training (mmap Native)16 | Zero-Copy Memory Mapped | Embedded Scalar Approximation16 | Pure Go Local Codebase Search16 |
| **Qdrant 1.18 (TurboQuant Engine)** | 1-bit to 4-bit | 8x to 32x | Precomputed Standard Centroids8 | AVX-512 / NEON SIMD8 | Anisotropy Compensation & Renormalization8 | Production Scale Vector Deployment8 |

SAGIHA2 implements a hybrid retrieval engine combining lexical BM25 sparse indexes with dense TurboQuant-compressed vectors managed by LanceDB and sqlite-vec8. For local embedded search scenarios, the harness utilizes tqdb memory-mapped quantization storage, enabling search execution directly over mapped files without decompressing vectors into floating-point arrays16.

### **Tri-Tier Persistence Layer Architecture**

SAGIHA2 organizes state persistence across three unified adapters to maintain structural consistency and support rollback capabilities:

> * **Short-Term Memory (STM)**: In-memory sliding ring buffer over the active session, durably backed by the same SQLite-WAL store as the trajectory. **Redis is not adopted.** STM is per-session and small, it needs durability co-located with the trajectory rather than a network hop, and SQLite-WAL already supplies persistence, crash recovery, and queryability. Introducing a second daemon buys nothing at single-node scale, and the multi-node case that would justify it is not on the roadmap.
> * **Transaction Store**: SQLite with write-ahead logging and append-only event sourcing for step trajectories, tool payloads, diff deltas, and checkpoints. Scores arrive as separate `StepScored` events rather than mutations of stored steps, which is what makes "append-only" true rather than aspirational.
> * **Long-Term Memory (LTM)**: Split deliberately into two stores with different epistemics — see below.

#### **The Code Graph and the Episodic Graph Are Not the Same System**

Earlier revisions routed both structural code facts and learned experience through a single temporal graph engine. That conflation is expensive and unsound, because the two have entirely different sources of truth:

> * **Deterministic code graph** — imports, call edges, definitions, inheritance, ownership, co-change coupling. These are *exactly derivable* from Tree-sitter and git. Passing them through LLM-based entity extraction pays tokens and latency for facts a parser already knows with certainty, and admits hallucinated edges into the dependency graph that downstream impact analysis then trusts. This tier is built directly by the indexer into SQLite tables, or an embedded property store such as Kùzu when recursive traversal outgrows SQL — embedded either way, which preserves the local-first principle that a Neo4j daemon would break. It is cheap, exact, and fully rebuildable from HEAD.
> * **Episodic and decision memory** — ADRs, pull-request rationale, "we tried X and it failed because Y", operator preferences. Here the facts are genuinely unstructured, genuinely contested, and genuinely change validity over time. This is where bi-temporal modelling and LLM extraction earn their cost, and where an engine such as Graphiti applies.

**A note on bi-temporality for code**: git is already a bi-temporal store. Valid time is commit time, transaction time is index time, and structure can simply be re-derived at any ref. Rebuilding that inside a graph database duplicates version control. Temporal invalidation is reserved for learned facts, which git does not track.

### **Protocol Standardization: Model Context Protocol (MCP) vs. Agent-to-Agent (A2A)**

Standardizing agent communication protocols requires distinguishing between vertical tool integration and horizontal inter-agent collaboration17.

| Architectural Feature | Model Context Protocol (MCP) | Agent-to-Agent Protocol (A2A) |
| :---- | :---- | :---- |
| **Primary Integration Axis** | **Vertical Integration**: Single Agent to Local Tools and Resources17 | **Horizontal Collaboration**: Agent-to-Agent Peer Orchestration17 |
| **Governing Entity & Origin** | Anthropic (November 2024\)18 | Google / Linux Foundation (April 2025\)17 |
| **Capability Discovery** | JSON-RPC 2.0 handshake over standard IO / HTTP-SSE | Standardized JSON metadata published at /.well-known/agent-card.json \[cite: 17, 18\] |
| **Core Abstraction Primitives** | Tools, Prompts, Resources, Resource Templates | Skills, Tasks, Messages, Parts (TextPart, FilePart, DataPart)17 |
| **Transport Layer Mechanisms** | Stdio pipes, HTTP with Server-Sent Events (SSE) | HTTPS with JSON-RPC 2.0, SSE streaming, gRPC bindings (v0.3+)17 |
| **Task Lifecycle Management** | Synchronous tool execution calls | Asynchronous state machine (submitted, working, input-required, completed, failed)17 |
| **Security & Authentication** | Local process boundaries, environment variable tokens | Enterprise OAuth2, Bearer tokens, API keys, mutual TLS (mTLS)17 |

MCP defines a standard interface for agents to discover and invoke local host tools, inspect language server diagnostics, and read filesystem structures17. A2A provides an enterprise framework for asynchronous, cross-system agent collaboration17.  
In SAGIHA2, an Orchestrator Super-Agent uses A2A to dispatch sub-tasks—such as writing an integration test or optimizing a database query—to remote specialized sub-agents18. The sub-agent receives the task via an A2A task lifecycle, executes local tools via MCP servers, streams real-time updates over SSE, and submits completed artifacts back to the orchestrator17.

### **Outer-Loop Self-Evolution and Process Reward Models**

Autonomous agents often struggle with prompt drift, over-fitting, and policy collapse when evaluating performance purely on final outcomes. Traditional Outcome Reward Models (ORMs) provide sparse feedback by checking only binary test suite outputs. This can lead to reward hacking, where an agent generates hardcoded returns to pass specific test cases.  
Process Reward Models (PRMs) mitigate this by scoring each step of a trajectory rather than only its outcome. For a trajectory `τ = (s₁ … s_n)`, the aggregate score is the weighted mean of per-step scores `PRM(τ) = Σ wᵢ · r(sᵢ) / Σ wᵢ`, where `r(sᵢ)` combines diagnostic deltas, tool execution efficiency, and incremental coverage gain.

**The reward signal must stay vector-valued, and its components are not interchangeable.** Diagnostic counts, lint cleanliness, and coverage are *proxies*, and every one of them is trivially gamed: delete the failing code, add a suppression comment, widen a type to `Any`, or wrap the call in a bare except. Collapsing them into a single scalar that admits candidates is how a system optimizes its way into a broken state while its dashboard improves. The architecture therefore separates two distinct roles:

> * **Hard gates (admission)**: binary, non-negotiable, and never traded off against each other — tests pass against a pristine injected suite, no new suppressions, test files unmodified, coverage not decreased, diff size within bounds. A candidate failing any gate is discarded regardless of its score.
> * **Soft score (ranking)**: the PRM value, used only to order candidates that have *already cleared every gate*.

Recursive Harness Self-Improvement (RHI) integrates step scoring into a dual-loop framework:

> * **Inner Loop**: The agent produces code changes under its current scaffolding, retrieval parameters, and tool configuration.
> * **Outer Loop**: A Meta-Improver reviews execution logs and score distributions across held-out splits, proposing mutations to prompts, compaction policy, and dispatch parameters — never to the trusted computing base.

Candidate mutations must clear four gates, detailed later in this document: an A/A noise-floor calibration, a screening split, a commit-replay private split, and a paired regression gate with multiple-comparison correction.

## **Technical Deliverables and System Architecture Specifications**

### **Decoupled Control-Agency-Runtime (CAR) Model**

The CAR architectural model isolates execution responsibilities into three conceptual layers, preventing unvalidated LLM outputs from reaching host resources or bypassing governance boundaries:

> 1. **Control Layer**: Manages execution policy, safety guardrails, financial token budgets, context allocation, and verification gates. It authorizes every agent tool request against security policy before execution.
> 2. **Agency Layer**: Handles high-level deliberation, reasoning loops, context synthesis, sub-task decomposition, and A2A delegation. It holds no reference to Runtime objects and issues intent specifications only.
> 3. **Runtime Layer**: Executes sandboxed code, captures terminal IO streams, manages isolated Git worktrees, and runs local MCP tool drivers. It returns structured observation objects to Agency without touching agent memory or policy state.

**Native Performance Sidecars** are deliberately *not* a fourth layer. They are a deployment topology available to the Indexer and Runtime layers — an implementation detail of where a port's adapter happens to run, not a distinct architectural responsibility. Conflating logical layering with physical process placement obscures both.

#### **Making Control Structural Rather Than Advisory**

A Control layer described only in prose is a convention, and conventions are bypassed by the first contributor in a hurry. Earlier revisions of this document asserted that Control "evaluates every agent tool request" while the implied call graph let the Orchestrator invoke the tool registry directly, leaving no interception point anywhere in the type system.

Enforcement is therefore structural, by three mechanisms:

> * **Capability grants**: every side-effecting Runtime method requires a `Grant`, an unforgeable token minted exclusively by `PolicyEngine.authorize()`. Code without a Grant cannot act, so policy is non-bypassable by construction.
> * **Import-graph contracts**: CI enforces that the Agency package cannot import Runtime or adapter modules (via `import-linter` layer contracts). A violation fails the build rather than degrading silently.
> * **Single dispatch choke point**: Agency emits a `ToolCall`; the kernel resolves authorization, leases resources through the `ResourceGovernor`, dispatches, and records the outcome. There is exactly one path from intent to effect.

### **Architectural Blueprint and Meta-Harness Kernel**

SAGIHA2 is implemented in Python 3.12+ using Pydantic v2 for schema validation and strict hexagonal architecture protocols (`typing.Protocol`) to decouple domain logic from external adapters.

```python
"""
SAGIHA2 Core Protocols and Domain Models
Python 3.12+ Hexagonal Architecture Interface Definitions

CONTRACT RULES (enforced in CI, see 06-guides-and-patterns/port-conformance-testing.md):
  1. No `Dict[str, Any]` crosses a port boundary. Every payload is a Pydantic model.
  2. No infrastructure type crosses a port boundary. Ports speak domain language
     (`recall`), never storage language (`search_similar(query_vector)`).
  3. All timestamps are timezone-aware UTC. Naive datetimes are a schema violation.
  4. Ports are verified statically (mypy/pyright strict) plus a per-port conformance
     suite parametrized over every adapter. `@runtime_checkable` is NOT used as a
     correctness mechanism: isinstance() against a Protocol checks method *presence*
     only, never signatures, and yields false confidence.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Single source of time. Aware-UTC is a system-wide invariant: the bi-temporal
    memory layer compares valid-time against transaction-time across adapters, and a
    naive/aware mix raises at runtime or silently misorders across DST boundaries."""
    return datetime.now(timezone.utc)


# ============================================================================
# Core Domain Schema Definitions
# ============================================================================

class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    AUTH_REQUIRED = "auth-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class EffectClass(str, Enum):
    """Replay safety. A recorded trajectory may only re-execute PURE calls; all
    others are replayed from their recorded observation. Without this, time-travel
    debugging re-runs `git push` and `rm`."""
    PURE = "pure"                  # no side effects, safe to re-execute
    IDEMPOTENT = "idempotent"      # re-execution converges to the same state
    DESTRUCTIVE = "destructive"    # never re-executed during replay


class ToolCall(BaseModel):
    """`tool_name` is an OPEN namespace validated against the ToolRegistry at
    dispatch. It is deliberately not a closed enum: a fixed ActionType cannot
    represent tools discovered dynamically from an MCP server, which contradicts
    the premise that every capability is an MCP server."""
    model_config = ConfigDict(frozen=True)
    call_id: str
    tool_name: str
    arguments: dict[str, Any]      # validated against the registered JSON Schema
    effect: EffectClass = EffectClass.PURE


class ContentBlock(BaseModel):
    """Tool output is structured, not stringified. Mirrors MCP content blocks so
    images and resource references survive the boundary intact."""
    model_config = ConfigDict(frozen=True)
    kind: Literal["text", "image", "resource", "diagnostic"]
    text: str | None = None
    mime_type: str | None = None
    resource_uri: str | None = None


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    call_id: str
    success: bool
    content: list[ContentBlock]
    error_message: str | None = None
    execution_time_ms: float
    # Tool output overflowing the context window is a top-tier practical failure
    # mode. Truncation is explicit and the full payload stays addressable.
    truncated: bool = False
    full_output_uri: str | None = None


class DiagnosticItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    file_path: str
    line: int
    column: int
    severity: Literal["error", "warning", "information", "hint"]
    message: str
    code: str | None = None


class ReasoningBlock(BaseModel):
    """Provider-native reasoning, round-tripped verbatim.

    Extended-thinking blocks carry signatures that must be returned unmodified to
    continue a tool-use turn. Normalizing reasoning into a plain string breaks the
    signature and forfeits both reasoning continuity and prompt-cache hits, so the
    harness treats it as opaque payload it transports rather than text it owns."""
    model_config = ConfigDict(frozen=True)
    provider: str
    opaque: dict[str, Any]
    redacted: bool = False


class StepId(BaseModel):
    """Trajectory identity is a DAG, not a counter.

    A monotonic int cannot represent a branching search. System 2 explores parallel
    candidates, and per-step reward scoring requires ancestry, so identity carries
    run, branch, and parent."""
    model_config = ConfigDict(frozen=True)
    run_id: str
    branch_id: str
    seq: int
    parent: "StepId | None" = None


class TrajectoryStep(BaseModel):
    model_config = ConfigDict(frozen=True)
    step_id: StepId
    reasoning: list[ReasoningBlock] = Field(default_factory=list)
    summary: str = ""              # human-readable gloss, never the reasoning itself
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class StepScored(BaseModel):
    """Scores arrive after the fact. Emitting them as a separate event preserves the
    append-only guarantee of the trajectory log instead of mutating a stored step."""
    model_config = ConfigDict(frozen=True)
    step_id: StepId
    prm_score: float
    scorer_version: str
    scored_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# Memory & Retrieval Ports
# ============================================================================

class MemoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: str
    kind: Literal["episode", "decision", "preference", "artifact"]
    source_uri: str | None = None
    valid_from: datetime = Field(default_factory=utc_now)


class RecallQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str
    k: int = 10
    kinds: list[str] = Field(default_factory=list)
    as_of: datetime | None = None   # bi-temporal read: state of knowledge at a time


class Recall(BaseModel):
    model_config = ConfigDict(frozen=True)
    memory_id: str
    content: str
    score: float
    valid_from: datetime
    invalid_at: datetime | None = None


class Memory(Protocol):
    """Domain-level memory. Deliberately contains no vector, no embedding, and no
    storage vocabulary.

    The prior `store_vector(key, vector: List[float])` / `search_similar(query_vector)`
    form was a vector-database driver, not a port: it forced the core to own the
    embedding model and made the roadmap's own Day-2 target unreachable, since a
    temporal graph engine takes text episodes and has no vector to accept. Embedding
    is an adapter-internal concern behind EmbeddingProvider."""
    async def remember(self, record: MemoryRecord) -> str: ...
    async def recall(self, query: RecallQuery) -> list[Recall]: ...
    async def invalidate(self, memory_id: str, at: datetime) -> None: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimensions(self) -> int: ...


class Symbol(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    kind: str
    file_path: str
    line: int
    signature: str | None = None


class Indexer(Protocol):
    """Query-shaped, never parse-shaped.

    The boundary is drawn at the *query* so the index can later migrate out of
    process without touching a single consumer. A port that returned ASTs or bulk
    symbol tables would force serialization of the whole structure across the
    boundary and reintroduce exactly the cost a sidecar exists to avoid."""
    async def index_directory(self, root_path: str) -> None: ...
    async def update_file(self, file_path: str) -> None: ...
    async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]: ...
    async def get_skeleton(self, file_path: str) -> str: ...
    async def neighbors(self, symbol: Symbol, hops: int = 1) -> list[Symbol]: ...


class LSPAdapter(Protocol):
    async def get_diagnostics(self, file_path: str) -> list[DiagnosticItem]: ...
    async def get_definition(self, file_path: str, line: int, column: int) -> Symbol | None: ...
    async def get_references(self, file_path: str, line: int, column: int) -> list[Symbol]: ...


class CodeGraph(Protocol):
    """Deterministic structure: imports, calls, definitions, ownership, co-change.
    Derived exactly from Tree-sitter and git — never through probabilistic LLM
    extraction, which would admit hallucinated edges into the dependency graph and
    charge tokens for facts the parser already knows."""
    async def upsert_edges(self, edges: list["GraphEdge"]) -> None: ...
    async def query(self, cypher_or_sql: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
    async def impacted_by(self, file_path: str, hops: int = 2) -> list[str]: ...


class GraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True)
    src: str
    dst: str
    relation: str
    valid_from: datetime = Field(default_factory=utc_now)


# ============================================================================
# Model, Control & Execution Ports
# ============================================================================

class ModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    system: list[ContentBlock]
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    max_tokens: int = 8192
    cache_breakpoints: list[int] = Field(default_factory=list)


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True)
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0


class ModelProvider(Protocol):
    """The system's single most important dependency, and the port the earlier
    revision omitted entirely.

    Owns streaming, tool-schema translation, retries, token accounting, and cache
    breakpoint placement. A record/replay adapter implementing this same Protocol is
    what makes the orchestrator testable without API calls."""
    async def stream(self, request: ModelRequest) -> AsyncIterator[ContentBlock]: ...
    async def complete(self, request: ModelRequest) -> tuple[list[ContentBlock], TokenUsage]: ...


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)
    allowed: bool
    reason: str
    requires_human: bool = False
    grant: "Grant | None" = None


class Grant(BaseModel):
    """Unforgeable capability token minted only by the Control layer.

    Runtime methods require a Grant, which makes policy non-bypassable by
    construction rather than by developer discipline. Prose that says 'Control
    checks every request' is not an architecture until an interception point exists
    in the type system."""
    model_config = ConfigDict(frozen=True)
    grant_id: str
    tool_name: str
    scope_paths: list[str]
    expires_at: datetime


class PolicyEngine(Protocol):
    """The Control layer of the CAR model, which previously had no interface at all."""
    async def authorize(self, call: ToolCall, context: "RunContext") -> Decision: ...
    async def record_outcome(self, grant_id: str, result: ToolResult) -> None: ...


class RunContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    autonomy_level: Literal["interactive", "hybrid", "autonomous", "scheduled"]
    workspace_root: str
    budget_remaining_usd: float


class ResourceGovernor(Protocol):
    """Global admission control. Parallel branch exploration against a frontier API
    hits provider rate limits and burns wall-clock in retries unless concurrency,
    spend, and sandbox count are centrally bounded."""
    async def acquire(self, kind: str, estimated_tokens: int) -> "Lease": ...
    async def release(self, lease: "Lease", actual: TokenUsage) -> None: ...


class Lease(BaseModel):
    model_config = ConfigDict(frozen=True)
    lease_id: str
    kind: str


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    truncated: bool = False


class HunkResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    applied: bool
    file_path: str
    reason: str | None = None


class EditResult(BaseModel):
    """Applying an edit is the highest-frequency operation in the system; a bare
    bool discards why it failed and leaves the model unable to repair its own patch."""
    model_config = ConfigDict(frozen=True)
    hunks: list[HunkResult]
    syntax_valid: bool          # Tree-sitter parse check before the LSP ever sees it
    rejected_reason: str | None = None


class Workspace(Protocol):
    """No `get_path()`.

    Exposing a real filesystem path lets consumers call open() directly, which
    permanently blocks substituting a container or remote runtime. Every filesystem
    interaction is mediated so the sandbox adapter remains swappable."""
    async def read(self, path: str) -> str: ...
    async def write(self, path: str, content: str, grant: Grant) -> None: ...
    async def apply_edit(self, diff_text: str, grant: Grant) -> EditResult: ...
    async def run(self, command: list[str], grant: Grant) -> CommandResult: ...
    async def checkpoint(self, label: str) -> str: ...
    async def restore(self, checkpoint_id: str) -> None: ...


class WorktreeManager(Protocol):
    async def allocate(self, base_ref: str, branch: str) -> Workspace: ...
    async def materialize(self, workspace: Workspace) -> None: ...
    """Copies or links ignored-but-required artifacts (.env, node_modules, .venv)
    into a fresh worktree. Without this step every build fails immediately, because
    a worktree contains only tracked files."""
    async def release(self, branch: str) -> None: ...


class ToolRegistry(Protocol):
    def register(self, name: str, schema: dict[str, Any], effect: EffectClass) -> None: ...
    async def dispatch(self, call: ToolCall, grant: Grant) -> ToolResult: ...


class TrajectoryStore(Protocol):
    """Append-only. Source of truth for replay, audit, and outer-loop training data."""
    async def append(self, step: TrajectoryStep) -> None: ...
    async def append_score(self, score: StepScored) -> None: ...
    async def read_run(self, run_id: str) -> list[TrajectoryStep]: ...


# ============================================================================
# Orchestration, Evaluation & Improvement Ports
# ============================================================================

class GateReport(BaseModel):
    """Hard gates are separated from soft scores on purpose.

    Diagnostic-count deltas are trivially gamed by deleting failing code, adding
    suppressions, widening types, or swallowing exceptions, so they may rank
    candidates but may never admit one."""
    model_config = ConfigDict(frozen=True)
    tests_pass: bool
    no_new_suppressions: bool
    tests_unmodified: bool          # a candidate must never edit its own grader
    coverage_not_decreased: bool
    diff_within_bounds: bool

    @property
    def admitted(self) -> bool:
        return all([self.tests_pass, self.no_new_suppressions, self.tests_unmodified,
                    self.coverage_not_decreased, self.diff_within_bounds])


class Candidate(BaseModel):
    model_config = ConfigDict(frozen=True)
    branch_id: str
    gates: GateReport
    score: float


class CandidateSearch(Protocol):
    """Verifier-guided best-of-N with sequential repair.

    Deliberately not named MCTS: the operative algorithm has no persistent tree, no
    visit counts, and no backpropagation. Tree search is gated on a calibrated value
    model, because its asymptotics assume cheap rollouts while each expansion here
    costs a full agent run plus a test suite."""
    async def propose(self, task: "TaskSpec", n: int = 3) -> list[str]: ...
    async def evaluate(self, branch_id: str) -> Candidate: ...
    async def select(self, candidates: list[Candidate]) -> Candidate | None: ...


class Orchestrator(Protocol):
    async def execute(self, task: "TaskSpec", context: RunContext) -> AsyncIterator[TrajectoryStep]: ...


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str
    check: str                      # machine-checkable command or predicate
    required: bool = True


class TaskSpec(BaseModel):
    """Long-horizon autonomy requires a durable, resumable unit of work with
    machine-checkable success conditions. A bare task string leaves 'done'
    undefined and gives the Evaluator no target to evaluate against."""
    model_config = ConfigDict(frozen=True)
    task_id: str
    goal: str
    acceptance: list[AcceptanceCriterion]
    parent_task_id: str | None = None
    status: TaskStatus = TaskStatus.SUBMITTED


class Evaluator(Protocol):
    """Runs against a pristine, read-only injected copy of the test suite, never the
    candidate's own working tree."""
    async def evaluate(self, task: TaskSpec, branch_id: str) -> GateReport: ...


class MutationProposal(BaseModel):
    model_config = ConfigDict(frozen=True)
    proposal_id: str
    rationale: str
    diff: str
    targets: list[str]              # rejected if any path falls inside the TCB


class MetaImprover(Protocol):
    """Constrained by the trusted computing base: the policy engine, evaluator,
    benchmark definitions, and deployment gate are outside its writable surface.
    Otherwise the cheapest route to a higher score is editing the grader."""
    async def propose(self, run_ids: list[str]) -> list[MutationProposal]: ...


# ============================================================================
# Auxiliary Optimization Intelligence (advisory only)
# ============================================================================

class Prediction(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: float
    confidence: float
    calibrated: bool                # uncalibrated predictions may never gate
    shadow_mode: bool = True        # predict and log; do not act


class RewardPredictor(Protocol):
    async def score_step(self, run_id: str, step_id: StepId) -> Prediction: ...


class FailurePredictor(Protocol):
    """Ships in shadow mode until its reliability diagram justifies gating. Acting on
    predictions censors the training data — halted runs never produce success labels,
    making the predictor self-confirming — so an exploration fraction always runs to
    completion regardless of predicted risk."""
    async def predict_risk(self, run_id: str) -> Prediction: ...


class CostPerformanceEstimator(Protocol):
    async def estimate(self, task: TaskSpec) -> Prediction: ...
```

### **Operational Inner Loop: DMARTIC Dual-Process Execution Cycle**

The inner loop executes a structured operational sequence termed **DMARTIC** with Dual-Process reasoning:

> 1. **Design**: Parse task goals into a `TaskSpec` with machine-checkable acceptance criteria. Route via the deterministic escalation ladder (below) to System 1 or System 2.
> 2. **Measure**: Run language server diagnostics (`LSPAdapter`) and collect baseline test metrics prior to modifying code.
> 3. **Analyze**: Query the code index, the deterministic code graph, and episodic memory.
> 4. **Review (Plan Mode Gate)**: High-impact actions trigger an explicit review state verified by an Evaluator LLM or a durable human approval request.
> 5. **Test**: Apply edits speculatively inside isolated worktree branches; run tests from a pristine injected copy of the suite and query LSP diagnostics.
> 6. **Improve**: Admit candidates through hard gates, rank survivors by score, repair sequentially on failure.
> 7. **Control**: Validate policy and budget, land the winning candidate, and commit trajectory event logs.

**Routing.** System 1 / System 2 selection is a deterministic escalation ladder, not a learned judgment: attempt System 1; escalate on repeated failure, multi-file scope, or diff size above threshold. This resolves the cold-start problem — `select_model_route(task_complexity: float, …)` consumed a complexity score that nothing in the system produced — and the ladder's decisions double as the labelled training data the AOI router later learns from.

**Determinism.** State transitions and checkpointing are managed by a native Async Microkernel (with optional external orchestrator adapters). Note precisely what is deterministic: LLM calls are not reproducible even at temperature zero, and model versions drift underneath you. What the kernel guarantees is **record/replay determinism** — a recorded trajectory replays identically because effectful calls are served from recorded observations rather than re-executed, per `EffectClass`. This is what makes the orchestrator unit-testable without API calls, and it is a stronger practical property than the unattainable claim of deterministic generation.

## **Neural-Symbolic Memory, Graph, and Search Architecture**

SAGIHA2 integrates a hybrid retrieval architecture combining sparse lexical search, TurboQuant dense vector search, and temporal property graph traversals4.  
When an agent initiates context retrieval for a code refactoring task, the system executes a three-phase pipeline:

> 1. **Lexical Sparse Search**: BM25 keyword matching via SQLite-FTS5 extracts exact symbol names, class definitions, and error string matches. For code, exact-symbol lexical matching is the single strongest signal and is never demoted below dense retrieval.
> 2. **Dense Search**: The query is embedded and scored against the vector index. At Day 0 this is an exhaustive SIMD scan; see the sizing note below before adopting a quantizer.
> 3. **Graph Expansion**: The deterministic code graph expands the candidate set along import, call, and co-change edges, then episodic memory contributes decisions and rationale filtered to those still valid at read time.

**Chunking is the dominant variable, and earlier revisions omitted it entirely.** Retrieval quality for code is governed far more by how source is split into embeddable units than by how those units are compressed. The unit is the **AST-bounded span** — a function, method, or class body emitted by Tree-sitter — prefixed with its enclosing file path, module docstring, and symbol path so a retrieved fragment carries the context needed to interpret it. Oversized bodies split on statement boundaries with the signature repeated in each part. Retrieval is evaluated directly, as recall@k against a labelled query set drawn from the target repository, and that number is the metric to move.

**Quantization sizing.** A large repository chunks to roughly 10⁵–10⁶ vectors. At 10⁵, an exhaustive float32 scan completes in single-digit milliseconds, and compression addresses a cost the system does not yet incur. Aggressive quantization becomes relevant at 10⁷ and above. The dense tier therefore starts uncompressed and adopts quantization only against a measured latency or memory ceiling — noting that LanceDB embeds in-process and that Qdrant already ships a production TurboQuant engine, so this is an adoption decision rather than an implementation project.

### **Context Engineering: Cache-Stable Assembly**

Long-horizon sessions are constrained by two forces at once — attention density and prompt-cache economics — and the second dominates cost. Cache hits require a **byte-identical prefix**. Any scheme that repartitions the window each turn changes that prefix and forfeits the cache on every single call, which is why the previous "Dynamic Token Allocation" split (15% instructions / 25% graph / 40% snippets / 20% history) is withdrawn: applied literally, it would have made the system's stated token-reduction target unreachable by construction.

Context is assembled in strict order of decreasing stability:

> * **Stable prefix** — system instructions, tool schemas, and durable project conventions. Written once per session and never reordered. A cache breakpoint closes this region.
> * **Semi-stable region** — retrieved repository context for the current task, appended after the prefix. Changes only when retrieval genuinely changes, never merely because a percentage budget was recomputed.
> * **Append-only tail** — conversation, tool calls, and observations. Growth is strictly append-only so every prior token stays cached.

Compaction is a **deliberate, infrequent checkpoint**, not a per-turn background process. Compacting resets the cache exactly once, in exchange for reclaiming the window; performing it continuously pays that cost on every turn while saving nothing. Within this structure the three lossless strategies still apply:

> * **AST Context Skeletonization**: strip function bodies while preserving interfaces, attributes, signatures, and docstrings.
> * **Symbol Context Injection**: inject scope-local definitions, imports, and caller/callee signatures.
> * **Log Condensation**: collapse repeated whitespace, duplicate tracebacks, and progress spinners in captured output.

**Staged re-hydration** remains the safety valve: if an edit fails to compile or test under skeletonized context, the failing files are re-inserted in full before the next attempt.

## **Multi-Agent Delegation, Parallelism, and Isolation**

To enable multi-agent collaboration without file modification conflicts, SAGIHA2 isolates sub-agent execution contexts using Git worktrees and containerized sandboxes.

### **Git Worktree Concurrency and Lifecycle Management**

Instead of creating complete repository clones or allowing parallel sub-agents to operate within a shared working directory, SAGIHA2 assigns each sub-agent an isolated Git worktree attached to a separate branch.  
Worktree allocation follows a managed lifecycle:

> 1. **Allocate**: The `WorktreeManager` creates an ephemeral directory linked to a dedicated branch off the base commit.
> 2. **Materialize**: Ignored-but-required artifacts are linked or copied into the new tree. A worktree contains only *tracked* files, so `.env`, `node_modules`, `.venv`, and build caches are absent on creation and every build fails immediately without this step. Earlier revisions omitted it, which would have blocked the first parallel run.
> 3. **Isolate**: Edits, writes, and compilation execute exclusively within the directory.
> 4. **Commit & Verify**: Each step commits locally — commit-per-step is the checkpoint primitive, unifying rollback, replay, and audit at negligible cost. Verification runs against a pristine injected copy of the test suite.
> 5. **Select or Land**: See the merge policy below.
> 6. **Prune**: The directory is removed from disk and pruned from Git state.

#### **What Worktrees Do and Do Not Isolate**

Worktrees isolate *tracked file state*. Nothing else. Stating this precisely matters, because a Day-1 gate of "zero cross-branch contamination" is unreachable with worktrees alone, and believing otherwise produces failures that look like model errors:

| Resource | Isolated by worktree? | Consequence and mitigation |
| :---- | :---- | :---- |
| Tracked files | Yes | The intended guarantee. |
| Object database | No | `index.lock` contention and `git gc` races under concurrency. Serialize Git mutations through a single lock. |
| Network ports | No | Two agents both binding `:3000` collide. Allocate ports per worktree from a governor-held pool. |
| Dependency trees | No | Each tree needs its own install — minutes and gigabytes per branch. Link a shared read-only store where the toolchain permits. |
| Global caches | No | Concurrent writes to `~/.cargo`, pip, npm caches. Set per-run cache homes. |
| Databases & external services | No | Parallel migrations against one dev database corrupt it. Requires per-branch service instances. |
| Environment & credentials | No | Inherited from the parent process. Scrub and re-inject per grant. |

Full isolation of the bottom five rows requires **containers with per-branch volumes and a network namespace**. This is why containerization moves earlier in the roadmap rather than arriving as a Day-2 performance concern: it is the only mechanism that makes the isolation claim true.

#### **Merge Policy: Selection, Not Reconciliation**

Rebasing *k* sibling candidates that edited overlapping files makes conflict the expected case rather than the exception, and LLM conflict resolution is a high-variance operation to place on the critical path. The policy therefore distinguishes two situations that earlier revisions conflated:

> * **Competing candidates** (System 2 exploring alternative solutions to one task): exactly one winner is selected and the losers are **discarded**. Siblings are never merged with each other, so conflicts cannot arise by construction.
> * **Decomposed parallel work** (distinct sub-tasks advancing together): the code graph partitions the work into **disjoint file sets** before dispatch, using `impacted_by()` to compute the closure of each sub-task. Sub-tasks whose closures intersect are serialized rather than parallelized. Prevention at partition time is cheaper and far more reliable than reconciliation at merge time.

Landing remains optimistic: rebase onto the latest base, re-run the full suite in a clean sandbox, and land only on a green result.

### **Sandboxed Command Execution and Governance**

Sub-agent execution is confined to container or gVisor (`runsc`) sandboxes.

**Command sanitization is a usability guardrail, not a security control, and must never be relied upon as one.** Blocklisting shell strings such as `rm -rf` fails to `bash -c`, `python -c`, base64-encoded payloads, `$IFS` substitution, symlink indirection, and arbitrary interpreters already present in the image. The correct framing is unambiguous: **if the agent has a shell, it has every capability the sandbox grants that shell.** Security is therefore enforced at the boundary, not in string inspection:

> * **Sandbox-first**: the sandbox is the perimeter, which is why it is required from the first phase rather than deferred.
> * **No host credentials inside**: secrets are injected per-grant, scoped, short-lived, and redacted from captured output before it reaches memory or logs.
> * **Egress allowlist at the network layer**: enforced by the namespace, not by inspecting the command line.
> * **Filesystem scope**: writes outside the worktree require an explicit `Grant`, and grants covering credentials, CI configuration, or harness policy escalate to a human.

The harness supports interactive streaming and headless execution modes for CI and outer-loop evaluation runs.

## **Auxiliary Optimization Intelligence Engine**

To optimize execution latency and token costs, SAGIHA2 integrates non-LLM machine learning models that act as deterministic co-processors.

### **Local Machine Learning Pipeline Architecture**

The Auxiliary Optimization Intelligence (AOI) engine leverages lightweight local models to evaluate risk, score intermediate steps, and route requests dynamically:

> * **Trajectory Failure Predictor (CatBoost Classifier)**: Analyzes early tool call sequences, error codes, and step patterns to estimate the probability that a run fails or enters an unrecoverable loop.
> * **Step Process Reward Scorer (XGBoost / LightGBM Regressor)**: Evaluates diffs, diagnostic deltas, and test metrics to produce a step-wise score without an expensive LLM judge.
> * **Dynamic Context Budget Router**: Routes by task complexity and context length across local models, mid-tier cloud models, and high-capacity frontier models. Until it has training data, routing is the deterministic escalation ladder, which supplies the labels the router later learns from.

#### **Mandatory Statistical Discipline**

Every AOI model is advisory. Three constraints are binding, and the previous specification satisfied none of them:

> * **Shadow mode before gating.** A model that predicts, logs, and does not act, until its reliability diagram and Brier score justify promotion. A fixed 0.85 halt threshold on an uncalibrated model is an arbitrary number, and calibration cannot be assumed — it must be demonstrated on held-out runs.
> * **Exploration against self-confirmation.** Halting runs predicted to fail censors the training data: those runs never produce success labels, so the predictor's errors are never observed and it becomes self-fulfilling. A fixed exploration fraction always runs to completion regardless of predicted risk, and censored outcomes are never treated as negatives. Where halting does occur, training corrects for the selection with inverse-propensity weighting.
> * **Out-of-distribution fallback.** On unfamiliar repository layouts the model abstains and control reverts to deterministic policy. Non-blocking behavior is a hard requirement: an unavailable or low-confidence AOI model must degrade to safe defaults, never stall the run.

## **Outer-Loop Self-Improvement and Verification Framework**

SAGIHA2 employs Recursive Harness Self-Improvement (RHI) to systematically evolve its system prompts, context compaction parameters, and tool execution scaffolding over time.

### **Harness Evolution Cycle and Multi-Tier Verification**

The outer-loop self-evolution framework operates continuously across four operational steps:

> 1. **Trajectory Ingestion**: Traces, tool logs, and step scores are written to an append-only Trajectory Store instrumented with OpenTelemetry, following the OTel **GenAI semantic conventions** so ecosystem tooling works without bespoke adapters. The span log and the trajectory store are one source of truth with one derived from the other, never two stores of the same facts drifting apart.
> 2. **Mutation Proposal**: A Meta-Improver agent reviews failure patterns and proposes targeted mutations, restricted to the writable surface defined below.
> 3. **Multi-Tier Verification**: see gates below.
> 4. **Deployment**: Validated mutations are staged for **human sign-off**. They do not self-deploy.

#### **The Trusted Computing Base (Non-Negotiable)**

A self-improving system that can edit its own evaluator has a trivial optimum: edit the evaluator. The previous revision explicitly listed policies and adapter code as mutable artifacts and had validated mutations "automatically commit to the production scaffolding baseline" — which, combined with shell access, made rewriting the grader the cheapest available path to a higher score.

The following are **outside the Meta-Improver's writable surface**, enforced by path allowlist in `MutationProposal.targets`, by residing on a branch the agent cannot push, and by CI rejection of any diff touching them:

> * The policy engine and autonomy configuration.
> * The Evaluator, the gate definitions, and the benchmark task definitions.
> * The deployment gate itself, and this list.
> * Secret handling and the sandbox boundary.

The mutable surface is what remains: prompts, retrieval and compaction parameters, tool descriptions, routing heuristics, and non-Control adapter code.

#### **Verification Gates and the Noise Floor**

> * **Tier 0 — A/A calibration.** Before any mutation is evaluated, the *unmodified* harness is run twice against the suite to measure the score-delta distribution under pure stochasticity. This establishes the noise floor. Any candidate that does not beat it is not an improvement, regardless of how much its score moved. Without this step, "accept if the score improves" ratchets permanently on noise — a real and likely failure mode given that most harness mutations produce effects smaller than run-to-run variance.
> * **Tier 1 — Screening.** Candidates run against a held-out task split. **SWE-bench Lite is unsuitable as the primary screen**: it is contaminated across frontier models, Python-only, and shaped as single-repo issue resolution, which does not match the long-horizon multi-file target. Prefer SWE-bench Verified and Multi-SWE-bench, and treat public suites as a smoke test rather than the objective.
> * **Tier 2 — Commit-replay split.** The private split is harvested rather than hand-authored: real commits are mined from target repository history, reverted, and posed as tasks. This yields an unbounded, uncontaminated, in-distribution benchmark that stays current as the repository evolves, and it removes the need to invent synthetic bugs whose distribution nobody can defend.
> * **Tier 3 — Regression and statistics.** Paired evaluation on identical task sets with fixed seeds, k ≥ 3 runs per task, reporting variance rather than a point estimate. Because many candidates are screened, the acceptance threshold is corrected for multiple comparisons; uncorrected repeated testing manufactures winners from noise. The mutation must not increase token consumption or latency.

**Budget realism.** A few hundred benchmark tasks at several dollars each, times k repetitions, times many candidates, puts a single outer-loop iteration in the thousands of dollars. The AOI pre-filter exists precisely to keep this tractable, and the outer loop is scheduled deliberately rather than run continuously.

## **Epistemic Critique and Adversarial Failure Analysis**

Deploying autonomous meta-harnesses in software development introduces structural failure modes that require explicit architectural mitigations.

### **Context Compaction Degradation vs. Information Loss**

> * *Structural Failure Mode*: Aggressive context compaction strategies—such as stripping docstrings, removing comments, or generating AST skeletons—risk omitting subtle business constraints, edge-case warnings, or implicit type requirements embedded in source comments.  
> * *Mitigation Strategy*: SAGIHA2 implements a staged fallback protocol. If an edit action fails compilation or unit testing within a compacted context window, the harness automatically re-hydrates the context window with raw source files before attempting subsequent edit steps.

### **Serialization Latency in Multi-Agent Networks**

> * *Structural Failure Mode*: Relying on JSON-RPC 2.0 over HTTP-SSE across deep sub-agent hierarchies introduces message serialization overhead, high latency, and transport bloat during rapid tool dispatch loops17.  
> * *Mitigation Strategy*: For co-located sub-agents running on the same host machine, SAGIHA2 utilizes high-performance gRPC over Unix domain sockets with shared memory buffers, falling back to HTTP/A2A transports only for remote cross-network calls17.

### **Indirect Prompt Injection via Repository and Web Content**

> * *Structural Failure Mode*: **The primary security threat to this class of system, and one absent from every prior revision of this specification.** An agent that reads repositories, issues, dependencies, and web pages while holding shell access and credentials is the canonical injection target. A malicious README, issue body, code comment, test fixture, or transitive dependency can carry instructions that the model reads as directives — exfiltrate `.env`, weaken a check, add a backdoor, alter CI configuration. Autonomy multiplies the blast radius, since no human reviews the intermediate steps.
> * *Mitigation Strategy*: Repository and web content is **untrusted data, never instruction**. Retrieved content is delimited and labelled as data in the prompt, and the system prompt establishes that content encountered in tool output carries no authority. Defense does not rest on the model's judgment: credentials never enter the sandbox, egress is allowlisted at the network namespace, tool output is scanned for secrets before entering memory, and any action writing outside the worktree or touching credentials, CI configuration, or harness policy requires a human grant regardless of autonomy level.

### **Evaluation Capture: The Candidate Editing Its Own Grader**

> * *Structural Failure Mode*: A candidate branch has full filesystem access to its worktree, including `tests/`. Any selection procedure that scores a branch using tests the branch could have modified is measuring a number the candidate controls. The same applies at the outer loop, where a Meta-Improver with write access to the evaluator can raise its score without improving anything.
> * *Mitigation Strategy*: Evaluation runs against a **pristine, read-only injected copy** of the test suite taken from the base commit, never the candidate's copy. Modification of test files is a hard gate failure rather than a scored penalty. At the outer loop, the trusted computing base is excluded from the writable surface and enforced in CI.

### **Git Worktree Drift and Parallel Merge Collisions**

> * *Structural Failure Mode*: Concurrent sub-agents modifying overlapping files across worktrees produce branch drift and conflicts that an LLM must then resolve under pressure — a high-variance operation on the critical path.
> * *Mitigation Strategy*: Conflicts are prevented rather than resolved. Competing candidates are selected among and discarded, never merged with one another. Decomposed parallel work is partitioned into disjoint file sets using the code graph's impact closure, and overlapping sub-tasks are serialized. Landing remains optimistic: rebase, full suite in a clean sandbox, land only on green.

### **AOI Model Overfitting and Self-Confirming Predictions**

> * *Structural Failure Mode*: Local models trained on one codebase overfit to formatting and directory conventions, producing false-positive halts on valid solution paths. Worse, acting on those predictions censors the training data — halted runs never produce success labels, so the predictor's false positives are never observed and the model confirms itself indefinitely.
> * *Mitigation Strategy*: Shadow mode until calibration is demonstrated; a fixed exploration fraction always runs to completion; censored outcomes are never trained as negatives and selection is corrected by inverse-propensity weighting; out-of-distribution detection reverts control to deterministic policy on unfamiliar layouts.

## **Package Topology and Maturity Implementation Roadmap**

### **Codebase Package Mapping**

```
sagiha2/
├── pyproject.toml
├── src/
│   └── sagiha2/
│       ├── __init__.py
│       ├── composition.py         # THE composition root: build_kernel(config) -> Kernel
│       ├── ports/                 # All Protocol definitions. Imports nothing internal.
│       │   ├── memory.py
│       │   ├── model.py           # ModelProvider — the port previously missing entirely
│       │   ├── control.py         # PolicyEngine, Grant, ResourceGovernor
│       │   ├── workspace.py
│       │   ├── indexing.py
│       │   └── evaluation.py
│       ├── domain/                # Pydantic models. Pure; no I/O, no adapter imports.
│       │   ├── trajectory.py      # StepId DAG, TrajectoryStep, StepScored
│       │   ├── task.py            # TaskSpec, AcceptanceCriterion
│       │   └── tools.py           # ToolCall, ToolResult, ContentBlock, EffectClass
│       ├── kernel/
│       │   ├── dispatch.py        # The single intent -> effect choke point
│       │   ├── policy.py          # TCB — outside the outer loop's writable surface
│       │   ├── governor.py        # Global admission control: concurrency, spend, leases
│       │   └── bus.py
│       ├── agency/                # Deliberation. CI forbids importing runtime/ or adapters/
│       │   ├── loop.py            # System 1 ReAct
│       │   ├── candidates.py      # System 2 best-of-N + sequential repair
│       │   └── context.py         # Cache-stable context assembly
│       ├── runtime/
│       │   ├── worktree.py        # Allocate, materialize, release
│       │   ├── sandbox.py         # Container / gVisor — the actual security perimeter
│       │   └── edit.py            # Structured patch application + Tree-sitter validation
│       ├── adapters/
│       │   ├── model/             # Provider clients + the record/replay cassette adapter
│       │   ├── memory/            # SQLite baseline; episodic graph adapter
│       │   ├── indexing/          # Tree-sitter chunker, FTS5, vector tier
│       │   ├── lsp/               # Warm server supervisor + pooling
│       │   └── tools/             # MCP client drivers
│       ├── aoi/                   # Advisory only. Ships in shadow mode.
│       ├── outer_loop/            # Meta-Improver. Path-restricted away from the TCB.
│       └── observability/         # OTel GenAI semantic conventions; trajectory store
└── tests/
    ├── contracts/                 # Per-port conformance suites, parametrized over
    │                              # every adapter. The mechanism that makes the
    │                              # migration matrix safe rather than aspirational.
    ├── unit/
    ├── integration/
    └── benchmarks/                # Commit-replay harvester + public suite runners
```

**Deferred by design.** `sidecars/` does not exist yet, and neither does a DI container. Sidecars are introduced only when a measured Python baseline justifies them, against the query-shaped `Indexer` port that already permits the swap. Wiring is a single explicit composition root rather than a container with runtime plugin discovery: dynamic wiring defeats static analysis, and since this codebase's principal maintainer is an LLM navigating it through an LSP, "go to definition" resolving correctly is a first-class architectural requirement rather than a developer nicety.

### **Multi-Stage Production Deployment Roadmap**

The roadmap is sequenced as **vertical slices**, each thin through every layer and each independently useful. A component-wise plan that upgrades one row at a time optimizes the wrong axis: the risk in this system lives in integration, not in any individual component. The component migration matrix is retained as an appendix to the slice plan, not as the plan itself.

| Slice | Capability Delivered End-to-End | Primary Components | Quality Gate (measurable) |
| :---- | :---- | :---- | :---- |
| **S0: Verified Single-File Edit** | Agent resolves a failing test in one file, verified, logged, and replayable | `ModelProvider` + cassette replay, Pydantic domain models, dispatch choke point, `PolicyEngine`, SQLite-WAL trajectory store, Tree-sitter chunker + FTS5, structured edit application, pytest runner, commit-per-step | ≥ 70% resolved on a pinned 30-task internal suite at ≤ $X and ≤ Y min per task; 100% of runs replay deterministically from cassettes; port conformance suite green |
| **S1: Isolated & Sandboxed Execution** | Agent works in a materialized worktree inside a container with grants enforced | Worktree allocate/materialize/release, container sandbox, egress allowlist, secret redaction, resource governor, LSP supervisor with warm pooling | No run can write outside its worktree without a grant; no credential reachable from inside the sandbox; parallel runs show no port, cache, or database interference |
| **S2: Retrieval & Memory That Earn Their Keep** | Retrieval measurably improves task success over a no-retrieval baseline | AST-bounded chunking, hybrid lexical + dense fusion, deterministic code graph, episodic memory with temporal reads | recall@10 ≥ target on a labelled query set from the target repo; ablation shows retrieval beats the no-retrieval control on the task suite |
| **S3: Candidate Search** | Verifier-guided best-of-N with sequential repair on multi-file tasks | Candidate proposal, hard gates, pristine injected test suite, graph-partitioned decomposition, escalation ladder | Best-of-N beats single-shot on the suite by more than the measured A/A noise floor; zero instances of a candidate modifying its own grader |
| **S4: Measured Self-Improvement** | Outer loop proposes mutations that survive statistical scrutiny | Commit-replay benchmark harvester, PRM scorer, calibrated AOI in shadow mode, Meta-Improver with TCB path restrictions, human sign-off gate | A/A noise floor established and published; every accepted mutation beats it under paired evaluation with multiple-comparison correction; TCB diffs rejected by CI in 100% of attempts |

**Deferred until a measurement demands them:** compiled sidecars, gRPC transport, vector quantization, external graph daemons, Redis, A2A, and tree search with backpropagation. Each has a named trigger condition in the migration matrix rather than a calendar slot.

## **Strategic Conclusions**

The **SAGIHA2** specification defines a Meta-Harness for autonomous software engineering agents built on hexagonal boundaries, isolated worktrees inside real sandboxes, split deterministic and episodic memory, standardized protocols, and advisory local models — addressing the failure modes that dominate agent runtimes in practice: context degradation, execution locking, API cost, and fragile scaffolding.

**What this revision deliberately changed.** The prior specification's ambition outran its foundations in four ways, each now corrected in the text above. Its ports were storage drivers rather than domain contracts, and would have broken at the first adapter migration the roadmap itself called for. Its Control layer existed only in prose, with no interception point anywhere in the type system. Its self-improvement loop could edit its own evaluator and deploy without human sign-off. And its complexity was front-loaded onto exotic components — quantization, tree search, compiled sidecars, temporal graphs for facts a parser already knows — while the components that actually determine whether a coding agent works were unspecified: the model port, context and cache layout, chunking strategy, edit application, and error recovery.

The corrected sequencing is deliberately unglamorous. Boring components first, measured before replaced, each exotic addition gated on a number rather than a date. The hexagonal discipline is what makes that sequencing safe: a query-shaped `Indexer` port admits a compiled sidecar later without touching a consumer, and a domain-shaped `Memory` port admits a temporal graph without a caller knowing. Deferral costs nothing when the seams are drawn correctly, which is the entire return on drawing them correctly at Day Zero.

#### **Referências citadas**

> 1. Maybe the problem with non-coding agents is that they have no repo : r/ClaudeAI \- Reddit, [https://www.reddit.com/r/ClaudeAI/comments/1tni1tf/maybe\_the\_problem\_with\_noncoding\_agents\_is\_that/](https://www.reddit.com/r/ClaudeAI/comments/1tni1tf/maybe_the_problem_with_noncoding_agents_is_that/)  
> 2. Best AI Assistants Tools \- Visalytica, [https://www.visalytica.com/category/ai-assistants](https://www.visalytica.com/category/ai-assistants)  
> 3. Vercel Day | Product Hunt, [https://www.producthunt.com/contests/vercel-day-may-26](https://www.producthunt.com/contests/vercel-day-may-26)  
> 4. GitHub \- getzep/graphiti: Build Real-Time Knowledge Graphs for AI Agents, [https://github.com/getzep/graphiti](https://github.com/getzep/graphiti)  
> 5. Graphiti — Zep, [https://www.getzep.com/platform/graphiti/](https://www.getzep.com/platform/graphiti/)  
> 6. Zep: A Temporal Knowledge Graph Architecture for Agent Memory \- GraphRAG, [https://graphrag.com/appendices/research/2501.13956/](https://graphrag.com/appendices/research/2501.13956/)  
> 7. graphiti/mcp\_server/README.md at main \- GitHub, [https://github.com/getzep/graphiti/blob/main/mcp\_server/README.md](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md)  
> 8. TurboQuant in Qdrant, [https://qdrant.tech/articles/turboquant-quantization/](https://qdrant.tech/articles/turboquant-quantization/)  
> 9. TurboQuant quantization (ICLR 2026\) · Issue \#8524 \- GitHub, [https://github.com/qdrant/qdrant/issues/8524](https://github.com/qdrant/qdrant/issues/8524)  
> 10. TURBOQUANT: ONLINE VECTOR QUANTIZATION WITH NEAR-OPTIMAL DISTORTION RATE \- OpenReview, [https://openreview.net/pdf?id=tO3ASKZlok](https://openreview.net/pdf?id=tO3ASKZlok)  
> 11. TurboQuant: Redefining AI efficiency with extreme compression \- Google Research, [https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/)  
> 12. TurboQuant-H: Hadamard Rotation for 2-Bit Embedding Quantization \- Cactus Docs, [https://docs.cactuscompute.com/v1.14/blog/turboquant-h/](https://docs.cactuscompute.com/v1.14/blog/turboquant-h/)  
> 13. TurboQuant : Near-Optimal Vector Quantization Without Codebooks \- Medium, [https://medium.com/@danushidk507/turboquant-near-optimal-vector-quantization-without-codebooks-3c0ccc8a41db](https://medium.com/@danushidk507/turboquant-near-optimal-vector-quantization-without-codebooks-3c0ccc8a41db)  
> 14. TurboQuant: Online Vector Quantization with Near-optimal Distortion Rate \- ICLR 2026, [https://iclr.cc/virtual/2026/poster/10006985](https://iclr.cc/virtual/2026/poster/10006985)  
> 15. \[2606.21448\] Fast-TurboQuant: A Multiplier-Free Online Vector Quantization Approach, [https://arxiv.org/abs/2606.21448](https://arxiv.org/abs/2606.21448)  
> 16. Building a Vector Database That Never Decompresses Your Vectors \- Embedded Thought, [https://scotteveritt.github.io/blog/quantization-native-vector-database/](https://scotteveritt.github.io/blog/quantization-native-vector-database/)  
> 17. What Is the Agent-to-Agent (A2A) Protocol? A Guide for API Teams \- Zuplo, [https://zuplo.com/learning-center/agent-to-agent-a2a-protocol-guide](https://zuplo.com/learning-center/agent-to-agent-a2a-protocol-guide)  
> 18. Google A2A Protocol: How Agent-to-Agent Coordination Works \- Atlan, [https://atlan.com/know/google-a2a-protocol/](https://atlan.com/know/google-a2a-protocol/)  
> 19. Agent-to-Agent (A2A) Protocol: Implementation and Trade-offs \- n8n Blog, [https://blog.n8n.io/agent-to-agent-protocol/](https://blog.n8n.io/agent-to-agent-protocol/)  
> 20. Understanding A2A (Agent-to-Agent Protocol) | by praveenreddy\_c \- Medium, [https://medium.com/@mailpraveenreddy.c/understanding-a2a-agent-to-agent-protocol-249f03777ff8](https://medium.com/@mailpraveenreddy.c/understanding-a2a-agent-to-agent-protocol-249f03777ff8)  
> 21. Agent Trajectory Annotation: The Guide | Innovatiana, [https://www.innovatiana.com/en/post/agent-trajectory-annotation](https://www.innovatiana.com/en/post/agent-trajectory-annotation)  
> 22. A2A protocol \- Koog, [https://docs.koog.ai/a2a/](https://docs.koog.ai/a2a/)


