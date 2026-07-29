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
Mathematically, given a knowledge edge ![][image1] representing a relationship ![][image2] between code entities ![][image3] and ![][image4], Graphiti decorates ![][image5] with a temporal validity interval ![][image6] and an ingestion interval ![][image7]4. When a code mutation event ![][image8] occurs at timestamp ![][image9], any pre-existing edge ![][image10] inconsistent with ![][image8] undergoes temporal invalidation where ![][image11] is set to ![][image9]4. A new edge ![][image12] is then created with ![][image13]4.  
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
First, an input vector ![][image14] undergoes a random orthogonal transformation ![][image15], where ![][image16] is a random orthogonal matrix generated efficiently via a Randomized Walsh-Hadamard Transform10. This rotation spreads coordinate variance evenly across dimensions, forcing coordinate values to follow a concentrated Beta distribution ![][image17]10.  
Second, Stage 1 applies coordinate-wise Lloyd-Max scalar quantization ![][image18] using precomputed centroids optimized for the unit sphere, yielding a compressed coordinate representation ![][image19]8. Because MSE-optimal quantizers introduce bias during inner product estimation, Stage 2 applies Quantized Johnson-Lindenstrauss (QJL) transform ![][image20] to the quantization residual vector ![][image21] using a 1-bit sign projection matrix ![][image22]10.  
The unbiased inner product estimator between two vectors ![][image23] and ![][image24] is formulated as:  
![][image25]  
where ![][image26] is a scalar scaling factor derived from the residual norm expectation10.  
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

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHoAAAAaCAYAAAB4rUi+AAAEGUlEQVR4Xu2ae6hNeRTH13gnMoi8UlOaGcojeUSiqBlmqBlqGjPlLSQpovCHRF7jzTTNjEemqeEfmmLylkhIIY+8JSWvkBmSwfh+rd92f3e19zl773Pn3JyzP/Xtnt9a++z7u/v3WGv99hXJyMjIyMgoGqugL62xxNkKdbfGUmYGtNEay4A20FmopXWUIu2hO1BD6ygTJkB7rDEpn0GXoGfQf9Bd174IXYVuQ6+db4z7TrHh9rXcGsuI+tBDqLd1pIEzhoP5qXWAdtADaIB1FIHm0EvRVV3OrIO2WWNS6oqu6GvW4fEX9JE1FoFxopOs3PkWegLVtI4k9BddzWs9Ww2pnPwcgGp57WLxK7TTGssQLjKOUUEZ+CLRmwx0bQ4ys9yf3l2RfyZ9Dp1OoJNQo7ffzM0JaKU1gjrQeugotAOq7ewzoftSWJbKe/8OnRHdMoeITvQjovePS1X38V9olDUmgQ/9FXQBOg/9LTrwQ/2Lqomb0FxrFK2p+0Bfifa1g7PPdu1Brp2GKdB30HjRe22BmkC3oHPedfmo6j4yhE23xrg0FR3k/Z6tAfQI+tCz5VvR/xePoanGxh3nD/d5E3RPKlbLB9AN6GPXJtuh0V47H8zymbf8KJq7NHbtzdAw77pcJO0jmQWtNjYfVkELrTEu34jOrjmejbH4kNf+XnSWVweccHagAzghufusMPZjps0cJE6YsHCH22WNCYnbR9JFtMKJggO92BrjwmSHA21rtHruJ2ffcam8usNgPc4QEFf8Q+M8fFYCYVs3YSbKvvfybHxYflKZllai9069VTqqso/curnqU8EY+FQqthULV/LP1lhEopIxsgx6IZXDyi/QJ+4zM9Q10J8V7nf0gL6wRo8RogPU2To8uBhGQi2swyNfHwn7skA0fOY6/WMyNtYa48DkgH/MXusQ3XKYefPmHY2vmDC+RZVXk0VP7XioQgaLVhABjGd8oEyifLhLsSa1K82Hv5enhLw2Cq523mO3dXjk6yMz8x/cZ55IdvN8PkF51dU6ctFP9KCciQ6/zJ9B2cOS4oroaRR9+9x3qguuGJYiYfAhMfScEk2g5osmQQFMouaJrioLD4A42FHxn4PnD0gYjP3MIXhMHEW+PnJXaCaa1T937TAYAv4RvV9J0loKOwK9DnUSrS4sfOU5yRpTELXjJIG1eliCFsB6nmVeScPDizQvNRj7uHPxVV9YbFsi6SdQAJPU36wxBcymbWYeELzU6GsdpQYHg/EyV6ISRlvosOgksckmT6XCkrSkcIC4hRcK+/m1NTr4mrLQMu+9YSK0wRoLgImUPbBICsvDpdaYAsZdHswwVlu4G10WnbRlA7e2UvpXIh6zMlkcDh00vgDG5Z7WmPF+MU20quFgMunMyMjIiOANtgThY9QCBowAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAAAdElEQVR4XmNgGAWDG9QB8WEgPgDEZkC8BYj3APFaIGaEKdIF4llArArE/4H4OhCLAfFGKF8EprACiC2AOBQq4QEVB9kCwhhgGhB/BmJWdAl0cAuIN6MLogM5Boi1+egS6CCeAaJQC10CHVQB8TF0wVFAfQAAbyMTqfrG10IAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAaCAYAAAC+aNwHAAAA3klEQVR4XmNgGAWjYDABFyDeAsR3gdgbKiYC5XfAFOECMkC8DoiZgPgCEK+CigsB8QsgPgnl4wR5QGwNxApA/A+IC5DkEoF4GRLfDIhvI/FRQAMQ/2KAOB0GkoA4DYkvDMR2SHwUcAOId6KJrQFiCTQxrIAHiP8DcS2SmBIQz4eyGYG4Hoh3MeBxwSsgngplczFAAlYayndngGhcDsTJUDEM4ATE5xgg0bkCiA2R5ASAmBeI3zFAYocsEM8AcRU/ELOgyREFtgFxMBBXAjEbmhxRAJQiFzAgUuoooBYAAKHuIGWcNRBeAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAaCAYAAAC6nQw6AAAA+klEQVR4XmNgGAWjYDgDFyDeAsR3gdgbKiYC5XfAFBECMkC8DoiZgPgCEK+CigsB8QsgPgnlEwR5QGwNxApA/A+IC5DkEoF4GRIfBnYAcRC6IAw0APEvBoiXYCAJiNOQ+DDgDsS86IIwcAOId6KJrQFiCTQxvIAHiP8DcS2SmBIQz0fig0AUELcD8SI0cRTwCoinQtlcDJAIkEZIM2gCcToQSwLxFyRxDOAExOcYIMlgBRAbokqDvcgKxIFAfAhNjizQy0BC2sIHTgCxH7ogqYATiH8AsTC6BKnADoivoAuSAvqB2BeIZwJxPZocSWA1AyRxTmGAxNwQAADXWiSnfHSLVAAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAbCAYAAAB1NA+iAAABBklEQVR4XmNgGAWDD7gB8U0g/gbE/4H4JZR/A4jvAPEzIP4HlUuC6sEKdjFAFGmgSwCBChC/AWJndAkYYGeAuOAuugQS2AbEiuiCMODEALF9MpIYExDPQ+LvA2IWJD4KaGeAGOAB5YM0lwLxdLgKBgZmJDYGOAPEf4H4GhBfBeLPDBADg5AV4QLCDBDNe5HEeID4PRALIInhdAHFBoQxQJxbjSQGCqyDSPxoIM5F4qOA2QwQA6zQxDmgNCMQn2RAdQ0KeAjEX4GYFV0CCkA2z0QXhAEtBojtu9ElGCDhAIrK30CsiybHYA/El4H4AwPEABB9AYovAvFtIP4DldsD1TMKRgEKAAAW4DetLfV9gAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKYAAAAaCAYAAAA9gCd5AAAE/UlEQVR4Xu2aV6hkRRCGy7RmXTGDyoorJhQDxhcDi6IIBsxgQMxZwYjgVRdzxCwGUNecBRVjiyALpgdFfVPMOYEiBvT/rD57ztbOMHNm7+7c0B/8TJ/qE+bUra6u7rlmhUKhUCgUJgiPS7OlWbGjUBgA4oh4eiR2tCVFQ6EwCqRoaEuKhkJhFEjR0JYUDZllpZOkKbGj0BeT3X8pGtqSoiFzhvSvtGbsKPTFZPdfioa2pGjIvCh9FI2Fvpns/kvR0JYUDebTz+/SDbGj0BfFf53jqhWp0d7ZfJR/aT4NfZyPD2icU+hO8V9Nioa2pGgQF0l/SyvGjpasIG0qbRA7OrC6tKVNjJpsIvtvcWkjaevYEUjR0JYUDeIN6c1oHIBtzO91Xz5e2jyLzJhzRs3+0mfSUbGjBbtGQ0t2kJaLxgEYr/7rh5XNN9E/jx2BFA1tSeF4eekv6fJgH5QTrXbsotKItN6c3rnhhQd17GrSLdHYkpulNaKxJePVf21Y34YQmHua10e7BfsiPT67cZzVju0F5w3i2CXMg/LW2NGCjaVfbP4Dczz6ry3TbQiBebX0p/kGMVwpbSGdK/0ovWVeO5FdvpMOk5aRnjcfzfxGegwXZpqOPVr6UDokH0+V7jbPLhdLb1tvx06RrpHOlK41v3Zv6R3ze98hbZXP5V1YGd8u3WheH8GT5qtm7vGBtIv5dQQUWefCfF4n1jJ/ZwZDJ8a6/4CS5V7pUvP35l147z+kk6WzzX/v3r26QOwjPSBdIF1vQwhMviAvDztJt9VdNtP8RYAV6L65jaP5ZxA+cXIz88QR/4TVzuNZZzX6Xm30dYNMdH9uE6Qjuc1nzJg3Sdvl9ivmdRgsJv1j7vgjzKcmIDB7ZcxnzM8j0Dox1v23kvmAoPQBBm01EH61+no+GcDAbPKF1fX3jjaEwCTbsMWBoy4z/yNWsDr8WVoq9xEYFZtLV5mPXF5ws2yPjn3I/KWpl8ha2zb6cEQvx+LQr80XAXdZvQodsXkDk5UqI5zM8J50SqOPVXMMwn4Ck4DEB/inE2Pdf8wu3H8k607zn07hJ2mT3CYrv5Db50nP5TbwXRd6YPaC1eah0iUNGyPoU2mdfMzoYutiSZvXsQ+aO48+pjymlYp+HEvgrCsdLj0rvZTtBGAVmDif1SPfo6r1yC6nmmckIDDJHk2qwCST8v26QeYgQAZh2P7byzxjduJ7acPcPsj81ytg+6sKUhiTgUnW4QWaDqEmeyy3yQa/mY84xKqSoKioRjyQVarRCq9LxzaOO7GfdFpuk3Goq4B6kQzK8883nyp/yH3wsvl1M/MxU/nUuvt/+N4Ex4jV9WgnCNzjo7FPhu0/dg2+kbbPxwzE6n5kzCowD7Z60FMjsxVVZfgZ0le53Y0UDW1J0dCDVaV3g40/JvUN9c7p5gsOshkF82zpE/MscaR5ZnjNvG5ZxbwIJ2DOkd43n6KrLNcJ6rKHzUcxC4s9sn2aeTZidb62eUFPsX6ddIL5dMRzCap7zLPjo+ajv4IAecrmnvIjTM1Pm3/3QRi2/4BszNTMAowyh4XaFebbXPiEnQWe8a3VvuD5nM9AYSGJ//BvN1I0tCVFwyjCH5HtEEQGIlhoUx+hbkyzugaK6lUDLmhYwR8YjQuIhek/7g08k3Z1f547CCka2sJ0wBYGtUuhML8QR8QT216FQqFQKBQmF/8Bk+hWDVqe4boAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAaCAYAAACzdqxAAAABPklEQVR4Xu2TPyhGURjGHyLZPkoZZZHhYxCjzWAxCIPhkzIiOyYGi2xKKRPKJlnNCCnZiJLRICWLeF7POd1z7ndvd9f91W8473Pue8+fe4GSkiIG6D19pz/0KY7rmITmfdMHehjH9ezTW+iBllTm6aSbUOO9VJbLHV2GHupJZZ5FugLNmUplmfTSIyTbHI3jP8ZoNz2DdtUex9nYSuag87bG83GMDjpNW+kXvYjjfE5oF61AjbeiVC9qpCNQvhbH2TTTm2D8Ro+DsTXzZ74BNR5O4nxs0nYwvoQ+P8N2UAuyK/oBLaaQdToejA/oJ22gC7TJ1dugSzt140LOoZV57Pxsu7O0P6jby62+FNRy6aOP0MV4ZqAGq0HN2HH1aqoeMUSfoa3ZZLuwCZcN0mskf98ufXXzzBfomy8p+Zf8AnQVQMXFAyHjAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADkAAAAaCAYAAAANIPQdAAACX0lEQVR4Xu2XS4iOURjH/65TTGFlakoWZNKQlGIyycICZcGKlEu5JYpiMg1maizcWbgmSlm434uFlFgIJQu5ZCnMCmEhMv9/z3P6zpw0w/d9LN7Or37Nec853zvvc85znu/9gEwmk8n8e8bQRWln0bhGX6adRWIw/UKPpgNFYjr9RRekA0Wghb6gH+lPb8vR0ZzCcI8+TjuLxFD6ne5OB/6SBnqKPkJ5ad9Ea9POajEbdh71txIe0Il0HZ2VjP0Jh2ld2lkt9sB2stJVfIfyH3I8/YTyP98nT2C7IPrRm3QQvUK/0U30OZ3pc1bSY/QQ3eB9HbC55+h8upCepbvoJfR8eKWy5u2kd2CLewKWTWdg9xJ6llafp6O00fvn0df0Kmz+De/vlbf0iLd10yXeHgCruErjpXQsnUGf+bhQJR7n7fewtyaxyhXbYAsiGmkXHUaH0/t0pI8pyHgxlPbHo2sFtNjb7fQhradrw4TeWEZfwVY3BBj4gZ7/+AAsyHb3Iuw7VsRB6uViDd1Lr8N2U2ynd72dkgapar88ut5Mb3u7DVV8cVGQI6Lr/fR8dB3zAaUg9TA7vL2CXqZDaCcsRX9HCFKZUwNbzNXR+BbYzgsFeTAaqwilq9IqMA2W3iHwOXSyt0OQA2GLM8H7t8LOtwLU3M8o7VgzneLtr3QULEN0Dx2dkz4mtLghNXVPZVXFnIat7gU6KerXL5VbdB9KhUcFRhVaxWYqrFjpcypS2o2nKD2gipJSVkHr3AVUcFRM1vt1f1g2qMjp60W7p2I0F1YI38DS/7+hapzJZDJ90g3a1HkeYbrYIgAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAaCAYAAAA9rOU8AAAB1klEQVR4Xu2VSShGURTHj1lRlJStogwpFhQWCslOLJRko6xkacNCKdlYmIfIggzFmjKVpbIgQ4SFTClFiZTxfzr30/nu9963kLd7v/r17rnnDefd4T0iHx8fb6iCp/AVfsN7E5/Ac3gLv0yu2VzjOWskD8yyEyADPsAKO+EFcSQjc2EnFCsw3e70gnKSURlSfZFwWsVbMFrFntFLUky1ibmQdjj2ewZRlGp7yi78hMfwCD6TFFenTwpDDMyGhXaCZDTdciGkkBSyqfoS4SNMVn3hRiYVzsNrO0Fy/zlyzoVQTzIKnaqP32ZbxY2wTcVO5JL7AzPJPRfEJEkxJVZ/vDlGwB0KHiUn+JPg9kD+NLjlgriELyTz7gSPyISKa+AI7Ib9MMH028XUwgXYBQesnCM5JKOybidI1g3vqHeYZ/ry4SHJbmNa4JRp62L4vjck92DKVC4ETh7AJ5Ji+Lhn3Idn8MPkNsw1TB+cUXERyceSF7cupgOuBk4ieQnXYv7KIFxUcTFJ0by+dDE8hfx7CeBJMaUkP1DebUwrXDJt3k08NUwBvIKxJq6Ed6b9rzTAWZLFOw6TYBpchm+wx5zXBEdJCh4mmXJe0J7DCzrwUXTblT4+/8IPYEVhYThBHcsAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEUAAAAaCAYAAADhVZELAAAC1klEQVR4Xu2XWchNURiGX/OsuDHdICLDjWSeUi6IUi4MKckUIkqZkj/kwhyZconIlCEyFqIUbpSxUKaQkMxDvK9vLXuf5fxn/+d3/uPi7Kee9tpr7XP2Wd/+1rf2AVJSUlJSUv437ei4sLPUOUrvhp2lTG36nm4LB0qZfvQnHRUOlCLz6R36lv5wbdk6dk3JcpFeCzsrQTPajbYIB7LQlvak9cKBAtOIdqUdwoFcNKBf6epwoBKMpk/oZHeuST+mTf5cEbGEfoftelVJd3qJ7goHcjEUVk90LAT7EQWlOV1J60TDGTxF1QdFTEGeQVkDy5SGQX+1hGN57EUUlCSUVcUIin5PXkG5Ti+7tiZ8nNaCTU4ZtMON3aK3YTWjCz1Ny+gx2tddI+JB2Uof0jbuvBMsk5bR5fQ1KhaUqXQ73Uznur7d9DOdBdswriDKds1jKewzWqZHkGdQlML68WIRnRAb01oc79r6chVS0Ytuce0B9KZrizBT3sAmriV0n/Zw/fXpBzeWi4H0Ruxcu6Mvmu8Q3UvHw66t5XLCtYUClFdQJtJ7dB8yAyKm0VOuvS4+QEbQ9XQT7Il7wqC8gE28D/0U6xd6FUgKygZYUMqcB2HvVUIB7+za+oui7BU6Kns8c5BnUHLRlH6kI2E7i2chPQt72u1hP64urY6/g/IcNvHB9Asya1JFgqLAa8ll4xXt6Npj6BnX1iuGst5T0KCIQ/QBMt8nLsDWsugPm9x02hI2AaWvx2eKls8zWD0SjWEBT3p/6A1b4n5bHwara0IPwwdlLOxBidn0gGuLFXRP7Pyf0TLxNcczhJ6jM2DBOE830kn0Eaxwq+6sgu1sKor6f6V3hp10Jl0MC8pV2gq50dI4CVvCvtDqu7/BJj8c9qBewgKibFwLqyU612dVf+b9/mSRqemOWkY1YLtYvL88BiGqGXEX2HBW/Hf7++ieIuleKSkpKUXjF5Ikj4hP20GzAAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAaCAYAAAAqjnX1AAACBklEQVR4Xu2WXyhfYRjHn/k3MUVKuFMuluZGStysTUlRJLlxpyVlaynLheRPspXdyGz+u8CdcqEof1auWO3CWttoqJWUEE0of8b38TxHr9PPr1a/3znF+dSn87zvc07nPc953/ccIg8Pj/tBHlyBR/ACbml7Ga7CTfhPcxV6jWtMkwzksT0BUuEOzLUnnOQhSSXX7AmDSZhi73SS5yRV7DT6QuCg0f4Mw4y247wlGWS+tnmAb+Cn6zOIQo3YFb7Cc/gT/oAHJIMuMU9yk3iSAc4ZfY/gHow1+lytZBlJ1eqNPp5780a7HL4y2o7TRzLIHFt/pB4fwC90s6r/A89vht+Er9g6+uUPPITh9oTCFezRuAbuwvewDk7ARs0x/KDDJAuxH0bAEZIi1MIPGr+GpfAYtl9d6Yc0kotm7AmSeckr/BSmG/08ML4xw5v8vsZxcBsmaLsXVmrMX65nJFXjRfmE5A11aN4nT+F3khvwIPm4pH6Dv+GZ5mb1GotxWK1xMjzRuBj+hU3qAHypuXewi+S+C7AZZpFUMyiMwSqNE0kqzRSRVNIXmST/AK0wA/6CLTDKPCmQcCWtQSaRVJyJIfk5ydY2P8ALjZl12K0x/7wMGbmAwn9BG3ARFsJRkilhLSyu0hT8SLJ4orWfaYMFGjeQbH1Bwfp286Tn3cDa4G/bGTw87gyXUjNmE0Gx1AgAAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKEAAAAaCAYAAADfXDwAAAAFSElEQVR4Xu2Zd4hkRRCHf4YzY87xzBERc3YVFcRTRMGMOaCiYM66ZjGnOyNiwJxzwLAmxHwi5ohZ/zBhRtH6qG6np3dnZ/bd3szg9Ac/5r3qN2/eq66uru6RCoVCoVAoFAqFQqFQKNSzhGnH3FhoO7uaFs6NvcK9pndzY6GtrGz6x7RD3tALTGP62XRZ3lBoK8fKg3C+vKEXWFf+8tvkDYW28pjpjdz4f+dI0zumH0x/h2M0NrmmMJi7TBNHoMP8a0Mys+lN0wfyRPCNvA/OSS/qBZ42vZwbKzCPvK5pZTpZzLSGafq8oUfZSB6E4/KGXmBG05+ms/OGCmxn+ty0VzgnyD4zzfbfFTWON/0lX5VXYX7TCrlxhGyaGzrI6XJ/kBmrMpPpcvki8/ysrVU64pPN5COQz9HgNtWCcF65c6etNdfxhaoH4bam7XPjCLkzN3SQF4ImhdNMB5k2NB2ctbXC3KZLc2M7oPYgEzKKUqZo8tmIm1ULwmaQNasEIZn1JU1aEO5kejs3tsjt8vKlVR3iX2vILPIseEbeMEJuUnWfjJEHYEd2SF4xPReOCbAH5A9EMJEhrwxtb8k7jZqPafBRU7/pPtM64RpIg5CX+ti0aDhfTp4pTzadYvpOzYOQ2pGp5XDTraat5Quqr0xPmK6SD6AZTA/Ln4nf2EcO93/e9KLpLNNHprXk78mCjO93epN+C7mvN0nOyWhbmt433WO6wXR/aKfmvtZ0qukW+eY27/Ch6RnT0WrsD5jVdI3pAvm9dzZtZXpV3sf4ZJVw7TLyKZ7+usK0eLDfbfpV3i/EBtm3MkyJMQUfI9+xjzwrf0CghmPhAWuaJoTj9eWru0ieCb+XBwJTMk5aPdhx0i+hbTjIDvuGY4J9XDgeUP2oJ5swvfLJvX+UlwPQJ8/2OP8403TBxiq0G9hbHoT4l1qXYKNWh375NL2A6YBge1K17TSC78ZwnPp+OH+QMU8Ix0zb9Dv0qz4T8gyfmBYM50vK+5p95ankOyqUcbuFtsrsbnpPnmXSAAQ6/5FwfF7aIB+tZKiL5RktkgchWw4E2tqm3xI7kImaBeHGpt9Nr8kzKA6AAQ2eelaSlxeM2p9MKwY7+6B5wPUNYesUlBdPyfcJyXBzJW0MmjQwGEgE7EXyoDlXnrkg9/1Q/sB/f5g2SK6L9Kv+txjwnybnQPZjJgFKiBjYk43Z5T9KqmblGyHd4zBGGCOAbEd2mVKDHfG1PNDYguDl05qylSBcKuhA+SikU4BsQBAyXeNcnIrD4v+uZHhKBzIwQfh6sEe4PgYh79et8L4XJucxCJdPbBGm5uj7Rv5g9U3wrBfsKSeqFoT4hNKH/kuhD0kMwH2G2vkYdUjp1FHpfh6jlqAAXoZg2k8+lVB/ML1EYiYkGL5UbVsFZxDgS4fzRlwiH9FAIMcOoabbRV5H4fCTTHeENgYEUz1TFeIZJ4a2yGry9wJWld0KZRC1W8qD8kQADGr+7oM0CIfzB/UcGTRyaPikvrtafj3Bz1T+rWmR0E7gs+VGOzAdMygmO0y7+bKdjn/ctL88+Abk08Oe8tHHQoe6kYUAtRhFNdPAqqbr5bUNjiMIWeVS7zTiTPnvU8OMl2c+2Fz+OziTDMyIJzseIa9zKBPoLLIgz8p/4zg4DqapTQ/JF16jtT012vCOFP3U0mSpyJzygLtOvr+7rGkPeYDgE+r4Rv6gvptDvsLn+9yX78NYeX/g74WCjexJ/zEQuJ7FJXBMRuY+MUl0BXQsEBQUrmMyeyP65PVIrqO8udACzXxcKBQKhUKhUCh0Jf8CdXsor40OkRMAAAAASUVORK5CYII=>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAaCAYAAAAEy1RnAAACs0lEQVR4Xu2XS6hNURjH/95CUZ55XO9QihTKABNSMpDkEQNFMSIGmFDyVh4hBsLAK5IIiTzDiAEyYyZ5FonJzeP/7/s266yzz77n7E65rv2rX3ufb619299ea31rXaCg4F9mOn1BT8YNLZ2LdEUcbMm0pp/oqLihOdKVnqfvYSN1jn6mV+g9j5+ms5IHAvTsAbqZnqFvSpubPzvoQNqdHg7iC2FTdhXdFcTFXTrX7/W8Ev9rtKFt3VZRWyW202G0N90XxPX8cb/fRMf6/Uz60duFZslyv0+lPezFYpIXFfpj6lcNGp2t9IF7m96g1+nsoF8W22BJ96F7o7YTftUU18iLLfSC3+td9QG0nrt5rAytgZ+R+oLzo9jl5IEMJtKnsGfbRW21oCQqJX3Urxrp8X6/ju7x+xn0LR1BF3usjF50NL0ES+4D7QlbUyocWhtqb0geqIBe8AntFzfkQAMRJ62KrPWsWaSPctbjoof/1lpeTe/Q/bRT0CcVTctXsMRVQa/S57RL2CkDrcM5cTAnSnooLOmXsI/5GFbJVbCWwj5CXZhKv8MS/0JHlrRmcxPptSEPYdIa6QWwUZ5C1wb96sZBWNLa3AeVNmXyjN5vwnm/e2ejKRwmLbRn6/du2HKrG9oiXtNGWOIP8aeCN4UKXec4mBNV7yEoTXo4PQZbbtqSqt1NMlFyWi+P6DjY9FbiKg7VsISuiYM5UX0YjPLqvQH2z4SmeVKtc9EXNl10CPhGx3h8JSzpH3SR98las/poOi5OixtysJMOgO0iOlomaHQ1ozrS9XRZ0FYTR1C6H+uIlxaX2hqy0Pn3FD1EJ8CmYi1VVocJbZHvYGtY25C2TV37e5/JsAOP+n2lGz1eE/p6yfFNI5l2qFB7B79WwyRYwblGb8H2TVmvLa2goKCgoOB/4BddlYpt+PWrLQAAAABJRU5ErkJggg==>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFoAAAAZCAYAAACxZDnAAAADIklEQVR4Xu2YWciNURSGXzMZMpM5UWRMkkL+QoobypRwI9f+lCTDlYiSkHKBJEr6ReYh/MpQuOBCISmRIULmIcP7Wnv37fN15n4dp/ZTb+ecvdb+znfWXt/aax8gEolEIpHKMZn6ndIv6if1nfpAPaD2UePdnEgZtKPGUouRBPqMGxtHzaD2B7aNNi1SLgqsD6YCm+Y6EntNpilSCoUCfQCJfW3K1iA0p5qkB0lTJ9EI5lfNFAr0cST2hcG4YtAs+OxRTFoEn8P3WVmH5Au8RlLzUmMn/IQqJVegFbBp1FdnO4LMxMu2mdZS3VNjH/2EXHSlhlLHYBNeU12ovtQr6qCz9/ET/jGrqNslSPdXDGGgv1AvqJfUZzf2iVoAC3xIa9jvXwPzU8cyCZbl16j7sMQc7CcUohP1FHaxw9Qp6i7VJnSqYsJA18EyshcsuN/ceLaS4tECnIb5PaQ2wBZnWOhULDWw/lIXU385KMNaHj1gGVFpcpUOsTuwqVTkQk//cyS+WqSy2QG7yDuqX6apLObA6n2lyRfo5YFtU8qWZjYS35kpW9F0o55RP2AXUg3ynUc5dKBuorRAr6RulSC1ZcWQL9BLA9uhlC2kMXUeSXzeUL0zPIpAAb0Mu/lRsNKhi4UnpQGwxv4GbOUfUZ1hp69tsA5mJzXF+a+APWoXqV2obL3PF+glgU0brGcuMu95PfUWtvndgflfQZHJ6GvoVtgOPMKN+1XWLqtaJB+1PTWw/wjaU6uplrDNc/7fWeZzjxroPtejtIxuaHzXoPvzwVTPrDGfjT2p986m3zuVGgPbr4Y4X/XWsmlRxGgkmb3F+SjhcqJM8zcg1eYYl5S9+uNFgfS0hd1A/2BMHYtKgKhHZQOdrQ/2qgv8hsNaxSewLkSBXwZLsnDOUeefHpdmOVtWdOLzvaOyMd8pSK8KtB4bT0fYl4QdyllYGRGXYIHWQujHVBsqC/4Aoxqd6wQov6JKSLFMQGYdE+eoRe69FuoxkhJ00tlUtye6sUgBtBlegB0391Ct3LgOO+pFt1N7YX89eqZTV6nNsIyIRCKRSOS/4g+RCvUq20b99QAAAABJRU5ErkJggg==>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFUAAAAaCAYAAADG+xDjAAADiElEQVR4Xu2YWahNYRTHF67MU8aMLzJEFDI/3GTKkHlIPCDhwUwJyQMyhEIZ4kXmWSgR9yqSN8MDSR54IZkzluH/v9/67O98nbP3PqfTvYe7f/Xr7POtc849Z+2117f2FUlISCgshsKn8IgfyIIl8AOc4wcqMxfgfH8xC6rCt7CzH/AZDH97/oI/4Q/4CT6Bh+BAfc+/CBPyXoKEtIdtgvBfiv0Fh57wpb+YjvqwL5wtQVKv6NoAOBYedmKbzdvKjX7wInwNT8Or8JWYqrsPn8H9sKt9g0MDuBuuh8clNSE14B7Y0lmbB0c5z0kXuA9ugSViPic2TKJNHJPoc0eCeHFqqFw4oY8T4FRnnYnhyefjJGed3HTWWAx+QurAA7AZnAWnpIbL1p/Ddvr8rpjExyYqqWzwNr7Wi2VLNVikVvFimWCVEv7wcc56L7hAj/ma6no8Er6R4PNZ2ekSwiuV1b/QD4Ct8Kwes328g52CcDRRSeUlaOMzvFgUjeFGeFvlZXRNzI9xExTGKX1klbIlWVhFvLzJNgku5w3wnB4zsUww+2lDXbNMhsvEtJB6XozfdZEedxfTPmqqsciUVH6hEfCbxvhFWWlx6QMfiEmGraJcsJe/n9RucLEeX5agMlfCHXo8XEwf7iipBTFazJhEmsK9sFYQLttbxujxJnhSzDhl20EkblK/ijkr/CJfdO0znC7xL1fSQsxm0soP5IDth25SWTGcSpgo/mBbVaSJrrGXLoWlcBesrXFubMv12MIqX+c8Z0HwZG4X89k34BonHombVPYmJqS1mER+1/V0bSEMnl1uLPngmD4yqdwwHok5YTzZbA2DNF5QZLr8yUEnxrk2Ltclu1YRhptUVipHJV76q2F/+6JCIyypK5wY57W4PIS3IvTHmEz4PbURPC9m3mSl2su6oAhLKvuJjbFPxeWSmFkwH9i/6/ZU9tK5sAfcqWsFRVhSuePZ2D1nnVVW13nuM1PMuJIP/Eq1nIHNxbSB8c56hcJK4k44TYLEcSblmr035u79UWP8v8Aw2FvM/wfa6mvSUSRmzBniB3LA9lTeIU101juI6fkczpl4Vm2Fw43HJtPX3sUQbgoca16ImQaYZI4qUfD++6iY20ieCFY2ExAX3vvzroYjHv9+CXwsZli3rBJTsTyB/F68m6oUcIfmvMeBmvNeqZqvkSshISEhISEhIeH/4Q9sjNsWnuAozAAAAABJRU5ErkJggg==>

[image17]: <data:image/png;base64,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>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAaCAYAAAAqjnX1AAACLElEQVR4Xu2WOWgVURSGf6MGhQSNUVALA+62prHQRgiCC0FsLLTRQongBpoi4pqISNxRTJHGBTQEFUNABAtR3BC0sDAgQUHBRhELFzTq/3vO8GYOGkIgE9D54OPduf/lzXn33pn7gIKCgv+LibSJ3qY36R36mO6lY0rDho8G+g5WUGWqfwbtoU/p+FR/roygZ+lXuiRkCXX0Jz0Rg7xohhWwPQYpymFjXsUgD2ppH31JR2ejDJrtb/RTDPLgMmyGtsQgMBc27kUMhhrNzgfYzeeFLLIeNu5MDIaasbAbq1AV3B936Rc6KwZ58JG+jZ2BRbAfszkGeXEe9uBMiIEzjvbSfaF/G+yd2kobaTfsLbGB7qL36Gwfu9SznfQR7F56Wxylh+lFutjH/pGpsCf7CJ1O22kH7Avm0Bt0VTI40EUveHsm/UEX+PVxesDb92HfJVRoFd1DT3mfanjj7b9SDSvyAX1IL8H24GmUjsJJtMbbCVfpJm/rRlqRhIOwHypU0GfYUbvW+3R6XYedbvIWrfBswGj/pU8XXcct0Uk3ensy/Z7KtLzHvK1lX0h30/fefoLSDxw0W2GnyzS6jJ7Lxr/RTCZFTkG2yBbYkgvNkvag2E9XwpZdWyl5q+xIjRkwq2FPtNRJMz8bYx19Ddsiy2GbX2Pb6Ar6jD6HFXQFtip6oE7Ciimjh+g1/6zHINC/He0bFbImZGKUf2omdJyO9Gu1lalfJuMKCv4JfgFkVWsU5MwlgQAAAABJRU5ErkJggg==>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAZCAYAAABZ5IzrAAABlklEQVR4Xu2UPShGYRTHj68QibJIiQnZLAZikE0oi4/VYGFBwsAgipQMltdC+SqJBclHhGQyKlks8pWSQQz8/53zeh9vlLy67+D+69dz7v853Xvuc8+5Ir58+fLl61sVgUVwDV7AFZgHWW6SVyoFT6KFtII8cAjewJyT55nORB++7Hgb5s04nicqEH0wGXD8NFAFUhzPE5VLqKDOsL2oqFBCBQ2F7UVN56IFHYf5uWDB4lnwDNpANzgBzRaPgE2QaLld5veDdfM4rdNgUHSac8z/UhWiU8aiAqDY4KSNO3mPoMVirrcg1a5PQSVIBhcgyfxhW3dBvcVN8oPpzRedqEvRk+Cp9YJYJ+dB9H9F8aY7zt4RqLGY/j1YBSUgXfRlJ0QHZwxMWW5EuhOdSqoBbDl7B6AWxIvmMJ4ULSxbtKDgy/yZeELBghrlc0H8vHUgE6w4/j7IAGugx7wY0PeR8UuxcV/BEqgGe+AGtIMO0ZPYBmWiRTCfTc0Gp1gom5ltMSo63REpwdY4i4O9xU9EKHrc9/V/9A4ocFUAyYpRVwAAAABJRU5ErkJggg==>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAaCAYAAAA5WTUBAAACDElEQVR4Xu2WTUhUURiGX1NDBSksN4kKWqS7/qCVu8JFG8GNigupTQRWupOKMtyo/diicCOCudBoq4igoLUokGgbhCgVJBKESvhD1PvNd+7Mud/M2EzNLIJ54IF77nu495vzdwfIkSNHehylt+gCnaWv6BK9R4ti3bLHNfoN+sJS734t/UDf08Pe/YySR4fpDm00WcBF+os+sUGm6IO+oNsGHgehfVZtkAnO0p90hRaGoxAyWnv0hw0ywST0F96wgaEO2u+jDVKghp6nxTYQ5Nd9hz683mSWK9B+z2yQBNlRHe76LnS0j0dTD6lMHiyFSEH78Zpu0xM2SEIXPee115GkCGGDfrU3DQ3QYq/bIA3kHUmLeA4dqjIbOA7RZdprA9IKPcwGoWfMS3f/Kl2jQ64t7FvEMejOeAhdQCP0BX1ET9IZ2hx09jhNt2ila7fRT7E4sg5SLkI4Ai3iDX1LJ6Br4CliR3U5rXbXgpwt815bXvDZa99BmkUkQubfPx2l7U/ZfTrntRMV8dhr/1URN6GnYxW9RMfCcWQ6NqGjKDQhXMRt6JQGyO5IdWdFaYHuCFFOyjPhOMJlOk176ADiR+KBu5ZsF7rW5CudMvK1lK+mPLjdZIk4hfgi+t118DkowJ/Po39CpucLXaQXoIu6M9Qjy1TQKehfgXd0lI7TEr9TtpEhPuCu8/3gv+A3udFlpia5u+QAAAAASUVORK5CYII=>

[image21]: <data:image/png;base64,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>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAaCAYAAAAtzKvgAAADqUlEQVR4Xu2YaahNURTHl3ks8/zBTKaMyRRPIUWSDPmADwgfSCizyJwk85B5yJgxc3imZEjKlCkpyVhEJIX/v7X3u/tu7513nuvVcTu/+vX23fvc+/ZdZ++117kiMTEx6UsP+BTu8gdiUucIHON3BlEFboCv4Hf4GK6ALeAt2CZxaVpQFHb0O0FbWMLvNBSEH2EjfyAnysIn8A3sDxvD3vA8/GXsnHV1/jICXhadzwF4Gz6ER+FzeAMughXtGwyc9x44GU6Bc+BFmAEXiH7WWHuxYarouKU9nOG8JmXgKjhP9PNfJw8HM100eBO8/gLwmBnr4o3lJ1wxW0x7Jaxq2iXhQdgSHoINTT9ZDAfBl7Cy6bsHl5h2Brxu2i4MGAPaGs73xghvzgDT5v9gcENzUjR4E/0B0FxSX7GFYGFjGIrDnaa9FpZzxibBZqK7bLvTXwEuhzPN62LwGyxvXo+Hm03bZx3cKLqQXHrBD04/8+voxHDunBIN3ic4SpK/CNkN63p9QTCVcMVdhVdEU8pZeEbCfQ6DYgPLL80gWobBbqbtr547ktja3GFcsRamlz6wktNHmC95Q7iym3hjXMHcGYTBZZB5vTufQGwqsP4UndQa2Mq5Lgwj4TXYwR/IA0Uk58COEz1Q2ccbbuHrr6KrncyCq02bC+Wz6Oqda/pIHdHvyJ3Eg2mZJN945mr2kZ6iZxDTz5CsK3KhNHwkycF15YEQhu7wtGhgUoFfNLvAMtdy5fcV3Q3tTD9hm1vVskM0GIQ5m9dzVVYzfawKmL/518J5L5XEzeEBuU80t/L8yRR9D3N9aLhFOJkf8mdgadfEpTlySRITTwUGlnMhDCxTyV3RSuGd6QuTUiIFVy9X3mzRUscG1s9nPqXgcb/zL/EDy5vO6oT/gyvZPwMiC+u87IplJuz9ooF94I35VIdvRQ+rIBvYNwTA7ekGlqmgE1wIa8P1ZizysOjOroYjrOEYWAYlCAaDp/6/gFWBLaXcHMt2U9FCnzVr5OEj63tYzx8QPRkZWFsfBrFVtNBOFR4e20zbDSxr1cOidTEPFZ7qkYaBZfC+iJYoA0XrQK4M1rasGPholxs1RE/fmv5AHuGpu8m0OR/38XWoaEnH3zZOSMTz7Tk4WPT3AR5AL0SrA+ZM5jP7iBgGPhxcgNNgfdFSx3+iCWK4aFnD3wd4YN4XLe755GTZa8ZuwmewljOW1vBU7yf69MW6k4HONP53ZVJMTExMTExMTEzk+A0FZcE2XcAj/QAAAABJRU5ErkJggg==>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAaCAYAAACD+r1hAAAA1UlEQVR4XmNgGAWDBbABMTO6IBCwQDEIMDJA1IFBCxD/R8MGQByBJrYFpkEMiHWAeBNU4g0QiwKxPBC/BuIVUHk5mAYYEAbiJwwQTWuBeBsQXwViHmRF6MABiP8yQDR9BmINFFkswIGBRA0gMJUBouEDECugSmECcSB+BsS/GSCajjEgghYDgCQOAvEZIDZigDgJpKkTWREISDFAgm0iEH8DYn2oeD4DRMM/II6BqgFH8ByoBAwXQDWgi4OwCEgCFOWgqAcBkAmsUDYyAMmzQ+lRQBAAAJ1wMQ2FyCQvAAAAAElFTkSuQmCC>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAZCAYAAADqrKTxAAAA4ElEQVR4XmNgGAVDBbABMTO6IBSA5JiQ2HDQAsT/0bAHVK4HSewHVAwMxIDYDCoIklwIxDxQOQkgvgHEfUCsBRVDAQsYIJpeMCCcYgjEv4BYEsrHAMYMCKfEQMVmA/FKuAoc4AQDRNNJIBYC4m9AbIuiAguIZkDYtgaIL6FKYwcgv7xkQGhMQ5XGDVoZIBreAzEXmhxOIA/Ef4G4F10CGYBSgysQC0L5akD8B4iV4SqwgEIGiHP2QfmTgXgjQho7KGeABDEo9uOB+B0QK6KowAJAztrPAElGx4BYB1V6yAEAwVQuUX15RBAAAAAASUVORK5CYII=>

[image25]: <data:image/png;base64,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>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAbCAYAAACnZAX6AAAAxElEQVR4XmNgGAUjBngD8X4oPgvEjUDMhCTPiMQGgxogfgrEmlC+CBC/AuJaKL8MiD2hbDAIBeL/DBCbkMFsIH4NxMxAvBeI2WASIIEHQPwQJoAEQLaADIsA4snIEmRpMoNKzEQWhIICBojcVSAWQ5YIh0okIwtCQQ4DRC4PXcIKKhGALgEEdQwQOZBrUAAoHs4D8SwkMXEGiB9WMyAMDAFiBSQ1DLJAvAGIjwDxDiBeDsTWULlJQHwLiBcxYIncUTB4AQBczSfTPPQZ5QAAAABJRU5ErkJggg==>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE4AAAAaCAYAAAAZtWr8AAADvklEQVR4Xu2YaYhNYRjHH2v2iIQwJCmEQrJOZE1SvogGV5YQStmzFUKRSJI9xBf7WvYPFCI+WIpi8oHIzgdk+/897ztz5nHuuWdmLjNd91f/Zs7/ee+55zznvM/7vFckS5YsWf45NaEzUGMbSEFd6DxUzwb+F05CY60Zk6HQWaiSDWQ6E0TfmtJwAFpozTj0gO5D76Gf0AvoAfQQegZdhMZBFfwHyglVoafQMBsoJt2h11AtG4jLMdHEtQp4FaGpzl8b8MsDI6DnotdYWu5CM60ZB375G+ieDYC2ool7aQNlzD7ooDVLyBbolDXj0FU0OattAMwXjZ2wgTLmETTHmqJTeAf0VfS6vX5A30VLkWW8aKkq9iLB4siTs955qonWtk/QLahRIFbWsB4xEcNtAGyHrkPLoKWi9WsJtMhpZMHIQnqK3n8L46fkEvQZOi5a666645tQAqpcMLJ80FL0RnONz0K/UwoXst6iPV4q2ouer7MNRFED+gIdMf5GKB/KCXj9RKcsv+QCtFe0zrAX6uLG9IWOujH094jWj21QQzeGrIceQ99EE2G5JnpdbBdsvJPo+Tsa38LSs8aaITQVPd9AG4hiiOiHZhl/gPNXGr+B8/k0PawRH6D67jhszFbojhRta7hS8wEsDnikHXRY9MGFwYTFSRy/b7Q1Q/CJG2wDUfDJh72mC5y/3Pg+Kb0CHmsjvUHuOGzMdOf55BImjl0/e8Ygs6FJkjxxzUTPlWsDAZqIjuFDSIWfqpzqsWELwrfFrijnRE82zfhhSWGS86WwibRjqkCHRKd2ECautuiK1s15bI3mitbWfOdZWF54/rDFwTNRtE7Hqc9+cQj2sJE0F/1AWAH1tWyyO94temKflP2iNWSz6FsbXHX9GBZqvrHcmXCc3X0wcbwx1r9Nzusv+vYnJHniyBMJb0c8nOq3rZkE347Y6/sDTi1uq96J3uBH0e6ZF+1pA10WHcfizidIfFKCYy32jWst+vTtVPCJ4xN/JfpmznOxhEQnbpdEN8DcKrIHjQMbYC5kf5WSJI5wX7kqcEx84gjrHAu5Lw0JiU4c+zHupdO15ZpizXTjk8JVNxl+TJ+Ax4s77f7v4P6uE+30CZtTbutY1ElCohPHhHO6pmOT/xaqYwPpJFe0yDMpV6C8ouHfcAynEMfwJx/fqXNTzrdqBTQK2iBaV9hsc8vHesvmm8yAbohOb07JHOdbWD64iJUG9olxp3RGwRsfY82Y8IdMPrg4K2/GUV20BJT0p3OWlSxZsmQOvwDia9fzj8R8jAAAAABJRU5ErkJggg==>

[image28]: <data:image/png;base64,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>

[image29]: <data:image/png;base64,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>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAAAaCAYAAAA+G+sUAAAERElEQVR4Xu2ZaahVVRTHl81zRio0UFQ0Ql+CBsLUCpo+VBRZ5BgREQUJ2mwDRGkDRQPNBdFApZnNERVSkEhiUWQRlYj1IcgKmz6I1f/H2vvd/Zbn3uu99xn31P3Bn3fO2ueec/bae6+1zn5mAwYMGPC/5lDplWjsU56XjozGOrK79IV0SGzoU/aWPpP2iA114ylpbjT2ORdLb0djnThM+kMaGxv6nB2kn6RjY0NduNc8ZtaR+6VF0VgXvpMui8aacJ60TtoyNvQ7e0l/W30rhP2sw/e/QfpAWiIdJb0mvSO9KI1qXLbZOc38xXeNDQUTpTekF6R3pWnDm3viHPMEyb2flO6UHht2RXvWSzOjsYrDpUekA807TRk3Tno5nY9pXLrZuUDaYM0Hm9r+Z2nPdM6EWd1o7olbpTXWuDdhg/7PG7pi0/hRmh2NVVwtHWM+2jzolGSnU6gVJ0VDj8wyd2wz5ki/SeOlraRLbOPZNVXaNtjacbp53/lt5uhky/7I7C8dH2wlX5sP4ibzgPSrtHVsaMFIZ/DLrbXjT5T+MncI73qP+QBkWJ2/W+eOX24+oJSEmavMw8ZOhQ2oulpNSBw/Pxpb8ZX0ajS2YIp5WBpJiNetQg2cIN0lrTQfgJlF21nmcb8TRpsP5pvBTo77MNjgU+m4aCwg1FwTjc3Yx7wTzLgqrjCfATeavyCx9nXpF/Pkc366bhtzp9wuPWPupDOkb6X3zZfgo+YrZZf0m5JWyXWh+X0yzGpm6YXpnPuukpal4xI+6adb9WrG8TyzDA87Sn+az1yO6eOp5nkP+9PpvApWSX6ntswwfzhfjZHtpW+k7dJ5TjaTpC/TcYaBuS8dk6S+T8c3m1dIGQbl8eI8kydAVTnGV+FtxTlxmcRaDtLH5u8VYSVz32YzcYX0cDqmv7wr1+MXEv5FqY1JtCQdV5HLySNiQzOutepllXlPWms+4iQdmGQbO/4T8x3Fm5JY9sTI66WHhq4ymyz9UJyXMGurPqDONu80q4VV96y0b9HOCmI2lnE6g8NZnc1yEgmT0PKSeR/57GcCfWS+b5TzyB3SLem4CiohViErv2d4KLuEjDYJmAHAmROt4fgz019m3KXpuIQNr9LxVA/cp4oHrbstA5b+0nTMh1iEd+7mviWEsZPNQxYld4Qtg+eisVuoFBYX58Tq3czDQY65eRZcKb1ljeRIbmD0cXwZahaYD2IVB5lXJp1ukvEM8svO5iEvwsBQfnYLfSJ+s7K4zwHDm4c2ySYEe9ewN46zSZh0CGcCK4ElTyLLiWYL84TEQPGXVQI4hdlCGcbMf8I8ljaD5HVdNLaBEMgXLXkgJmf2TgiBvX4MEnbuNg97EbaFmXR9RQw17cBxJLyDY0OXUF2dG40jCFUT5TjFQV/BSunE8UDIqcu//ojruejoG/jk/ty8WuGja8C/BHE/J9va7VMP+I/xD2mq0RzzIciRAAAAAElFTkSuQmCC>

[image31]: <data:image/png;base64,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>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADoAAAAZCAYAAABggz2wAAAC3klEQVR4Xu2WWehNURjFlzHzUMhU5rHkwQsiQ+RBokgk9X8wFVFEMnXNpcgjpUhJSCJDplxjyUzmKSVKHiQ8SFirb5/732e707k3XpxVv7p7nX323d8+e3/7A1KlSvW/qh7JkDvkKjlJevsdiqg12UuewN7fTdrFegDzyHjShjQlQ8kRMsTv9C+0ldwlzVxbE3tP2uZ65FddcolMce06ZDG5B1u8SJfJr4ATpKHX56+rM/lOpnueJqxAN3pePo0lZ0KTekrGee0s7Iu/JVfIXNgiFdVIcowMD/xKNR+2wgMCP0seBV6o2eQNbDv6uk4me+3zpKvXLltdyC7Yao4IniWVxlGgGtPXUfKTNA58X2Ng7yqwXs7rRz6QVlEn6hwqDDRSD7KHnEXlAeusaLIdAv+Q87sHvi9tv2uwfl/IanKfjPI7wea3iJwiN2DJrm+sR5nSairzaeWSBnwBNtH2gX/A+QMDP5S+nJJPlGQUeDjWabINtedyA3lHOuZ6JFQfsg8WcLlnOIvqAl0PC24p+QZ75wXsKonUH/Hk0w3Wb7vnVSQNrO2hM9woeBaq0NY96Pyege+rhrxCbTLS+dQ1VSoIXT3q8yx8kETaShlyGzaRUtoJ+1Otsi8lI/nFkpHO48LA08LeIg9dW4XCZzI118OkRKdznVgtyRpYdTKL1I8/LigVBwpoUOCrQtLdV0zKrhNDEzbmY/c7Axt/Ze4p0MR5zz2vpFqQVbAto4u4QfxxSSkh/CAzPE9jfCSbPE8LNw3xs6z7cYvXjrSW7HC/J8F2h18pDYYFutnzCkrl2grYF9QKVlNOqQTUONHdtxxWGamOjbQANrnDnqea9SuZCaumhAJ7STq5PkpCqoYmuLb+4yKsGGnuvLzSGVhCbsK+YDUBRtJqryMPYPfccfx5ZkeTT2RZ4Cu7Z2HXxWvYQoR3r4r8/bBsrDJQRYqflfNqGJmD5Fs0VapUqVKlyqPfbwqXfVxjZ6cAAAAASUVORK5CYII=>