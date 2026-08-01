---
status: rationale
updated: 2026-07-30
retrieval: excluded
---
# **Engineering Specification and Research Brief: SOTA Meta-Harness and Infrastructure for Autonomous LLM Coding Agents (SAGIHA)**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a proposed architecture and architectural blueprint for SAGIHA, not an imperative or immutable final solution. Further iterative prototyping, benchmarks, and practical evaluations will be conducted to refine and finalize the ultimate harness structure.

> [!IMPORTANT]
> **Rationale / research brief — not normative.** Binding decisions live in [`08-decisions/`](../../08-decisions/)
> and modular docs `01`–`07`. Superseded narratives (e.g. quantization product names, earlier
> trace-ownership wording) may appear under warning banners for historical context.
> Agent-facing retrieval must **exclude** `docs/reference/` and `docs/reviews/`.
> Implementation truth: [STATUS.md](../../STATUS.md).

## **Ecosystem Benchmarking and Theoretical Infrastructure Analysis**

Autonomous Large Language Model (LLM) coding agents have advanced beyond basic prompt-wrapping execution loops to multi-tiered, stateful software engineering runtimes. Designing a production-grade, hexagonal Meta-Harness requires evaluating modern open-source agent frameworks, dynamic graph memory architectures, mathematical vector quantization techniques, and emerging inter-agent communication standards.

### **Agent Control Planes and Harness Paradigm Evaluation**

Current software agent control planes exhibit fundamental differences in state representation, execution loops, tool dispatch pipelines, and code isolation mechanisms. Evaluating these paradigms reveals critical trade-offs between architectural flexibility, state isolation, and token efficiency.

| Framework / Paradigm | Control Loop Paradigm | State Management Architecture | Tool Dispatch Pipeline | Sandbox & Isolation Strategy | Worktree & Parallel Branching |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **OpenHands** | Event-Stream Orchestration | Stateful Event Log with step replay and state checkpointing | Non-blocking asynchronous event bus with streaming terminal standard IO | Containerized Docker execution runtime with gVisor sandbox | Ephemeral git branches with manual workspace state synchronization |
| **SWE-agent** | Agent-Computer Interface (ACI) Loop | Linear trajectory storage with action-observation step history | Synchronous bash tool execution with custom file view/edit utilities | Isolated Docker container execution instance per trajectory | Single repository clone per evaluation run |
| **Agentrail** | Local Control Plane & Scaffolding | Repository-centric state anchored to filesystem context | Asynchronous IPC and TUI event streaming | Host process or local virtual environment execution | Git workspace management via local control plane |
| **OpenHarness** | Minimalist Deterministic Loop | Ephemeral in-memory context window with explicit context compaction | Direct synchronous function calling with streaming tool output | Local process sandbox or light container isolation | Direct filesystem manipulation on active working branch |
| **Grok Build Paradigms** | High-Throughput ReAct Engine | Multi-turn Key-Value (KV) cache optimized state retention | Low-latency non-blocking tool dispatch pipelines | Containerized execution runtimes | In-memory code delta tracking with git commit staging |
| **Aider** | Git-Centric Interactive Edit Loop | In-memory Abstract Syntax Tree (AST) symbol graph and active commit index | Synchronous block-edit tool dispatch with git auto-commit hooks | Direct host working directory execution | Direct git integration with automatic commit-per-change policy |

In frameworks like SWE-agent and Aider, a primary bottleneck stems from the tight coupling between the reasoning loop and the active file system directory. Synchronous, block-based file modifications hinder parallel hypothesis testing and multi-branch exploration. In contrast, OpenHands demonstrates that event-stream architectures decouple agent decision-making from execution runtimes. However, state synchronization overhead during long-horizon tasks can cause context degradation if event logs grow unboundedly.  
The SAGIHA operational model synthesizes these paradigms into a decoupled Control-Agency-Runtime (CAR) architecture. It leverages event-stream orchestration from OpenHands, repository-level symbol mapping from Aider, trajectory tracking from SWE-agent, and multi-branch isolation through native Git worktrees.

### **Graph-Backed Memory Architectures and Knowledge Topologies**

Flat vector retrieval mechanisms frequently fail to capture structural code dependencies, temporal evolutionary changes, and cross-file ownership boundaries across complex enterprise repositories. Mapping modern software codebases requires combining Abstract Syntax Trees (ASTs), Architectural Decision Records (ADRs), git blame topologies, and bi-temporal knowledge graphs.  
Graphiti—the engine powering Zep's temporal context graph architecture—introduces a bi-temporal data model that explicitly records both valid time (when a fact was true in the real-world software system) and transaction time (when the agent ingested the fact). In dynamic software development, where continuous refactoring invalidates prior design decisions, temporal edge invalidation prevents the system from retrieving obsolete API signatures or outdated class structures.  
Formally, an edge `e = (u, r, v)` asserting relationship `r` between entities `u` and `v` carries two independent intervals: a **validity interval** `[valid_from, invalid_at)` recording when the fact held in the modelled system, and an **ingestion interval** `[ingested_at, retracted_at)` recording when the system believed it. When a mutation event `m` is observed at time `t`, any pre-existing edge `e'` inconsistent with `m` is invalidated by setting `e'.invalid_at = t`, and a successor edge `e''` is created with `e''.valid_from = t`. Retrieval as-of time `τ` selects edges satisfying `valid_from ≤ τ < invalid_at`, which is what prevents obsolete API signatures and superseded design decisions from re-entering context.

Note the scope limit established in the memory module: this machinery applies to **learned, contestable facts**. Code structure is not modelled this way, because git already records both time axes — valid time is commit time, transaction time is index time — and structure re-derives exactly at any ref.
Graphiti avoids expensive LLM-in-the-loop reranking during retrieval by executing vector similarity, keyword full-text search, and temporal graph traversals within a single compiled query execution step. Its authors report gains on the LongMemEval benchmark against vector-only and sliding-window baselines.

> [!NOTE]
> **Vendor-reported, not independently verified, and not transferable.** Specific accuracy and latency
> figures previously quoted here have been removed: they are the engine authors' own numbers, and
> **LongMemEval measures conversational long-term memory, not code retrieval**. No claim about
> repository search follows from them. SAGIHA's retrieval is evaluated on its own terms — recall@k
> against a labelled query set drawn from the target repository — and that is the only number this
> project will report.

To comprehensively index a codebase, SAGIHA unifies four distinct structural topologies:

> [!WARNING]
> **Superseded by [ADR-0011](../../08-decisions/0011-split-code-and-episodic-graphs.md).**
> External graph daemons like Neo4j or FalkorDB break the local-first, zero-dependency principle. The structural code graph is backed by SQLite FTS5 / relational tables locally, while the episodic graph is isolated in SQLite-WAL.

> * **AST Dependency Graph**: Tracks module imports, class inheritance hierarchies, function call graphs, variable definitions, and interface implementations generated via Tree-sitter parsers.  
> * **Architectural Decision Map**: Formulates a directed acyclic graph connecting high-level system requirements, ADR markdown files, pull request rationales, and architectural module boundaries.  
> * **Code Ownership Topology**: Maps git blame metadata to contributor nodes, calculates module volatility metrics, and tracks historical co-change coupling scores across files.  
> * **Temporal Context Graph**: Captures agent execution trajectories, conversational turns, tool outputs, dynamic edge invalidations, and active workspace mutations in real time.

### **Vector Search and Online Quantization Mechanics**

Repository indexing for multi-million-line codebases with high-dimensional vector embeddings (such as 1536-dimensional or 3072-dimensional embeddings) incurs substantial memory footprints and high search latencies. Standard Scalar Quantization (SQ) achieves 4x memory compression with minimal recall drop, but cannot compress below 8 bits per dimension without loss of precision. Traditional Product Quantization (PQ) achieves higher compression ratios but requires offline codebook training over static data, making it ill-suited for rapidly evolving repositories undergoing continuous commits.  
TurboQuant (Zandieh et al., ICLR 2026\) addresses this challenge via a data-oblivious, online vector quantization algorithm that achieves optimal theoretical distortion rates without offline codebook pre-training.  
The TurboQuant algorithm operates via a two-stage vector transformation pipeline:  
First, an input vector `x ∈ ℝᵈ` undergoes a random orthogonal transformation `x̃ = Rx`, where `R` is generated efficiently via a Randomized Walsh-Hadamard Transform. This rotation spreads variance evenly across coordinates, driving the marginal distribution of each coordinate toward a concentrated Beta form and removing the axis-alignment that scalar quantizers otherwise suffer from.

Stage 1 then applies coordinate-wise Lloyd-Max scalar quantization `q(x̃)` using centroids precomputed for the unit sphere, yielding the compressed representation. Because MSE-optimal quantizers introduce **bias** in inner-product estimation, Stage 2 applies a Quantized Johnson-Lindenstrauss transform to the residual `r = x̃ − q(x̃)` using a 1-bit sign projection `S`, capturing the residual's contribution without storing it.

The resulting unbiased estimator for the inner product of two vectors `x`, `y` is:

```
⟨x, y⟩ ≈ ⟨q(x̃), q(ỹ)⟩ + c · ⟨sign(Sr_x), sign(Sr_y)⟩
```

where `c` is a scalar derived from the expected residual norm. The first term supplies the bulk estimate from quantized coordinates; the second corrects the bias that quantization introduced.

> [!NOTE]
> **Adoption status**: deferred. At this system's corpus size (~10⁵–10⁶ vectors) an exhaustive SIMD scan completes in single-digit milliseconds, so quantization addresses a cost not yet incurred. Retained here for the day a measured latency or memory ceiling triggers it — at which point it is an adoption decision (LanceDB in-process, or Qdrant's existing TurboQuant engine) rather than an implementation project.  
Fast-TurboQuant optimizes this process further by replacing dense orthogonal rotations with a Rademacher phase inversion followed by a Fast Walsh-Hadamard Transform (FWHT), eliminating floating-point multiplications during preprocessing and yielding a 19.7x speedup under sequential execution.

| Quantization Framework | Bit-Width per Dimension | Compression Factor | Codebook Pre-Training | Search Execution Speed | Inner Product Bias Mitigation | Target Runtime Environment |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Float32 Baseline** | 32-bit | 1x | None | Baseline | Exact Unbiased | Uncompressed In-Memory Search |
| **Scalar Quantization (SQ)** | 8-bit | 4x | Min/Max Calibration | Fast | Minimal Bias | Low-latency Vector Databases |
| **Product Quantization (PQ)** | 2-bit to 4-bit | 8x to 16x | Required (K-Means Clustering) | Moderate | High Distortion at Low Bit-Widths | Static Enterprise Indexes |
| **TurboQuant (ICLR 2026\)** | 2.5-bit to 3.5-bit | 9.1x to 12.8x | **Data-Oblivious (Zero Training)** | Fast SIMD Kernels | **Unbiased via 1-bit QJL Residual** | Dynamic KV Caches & Real-time DBs |
| **Fast-TurboQuant** | 2-bit to 4-bit | 8x to 16x | **Data-Oblivious (Zero Training)** | Multiplier-Free (FWHT) | Unbiased via Residual FWHT | Low-power Local Search Engines |
| **tqdb (Pure Go)** | 4-bit | 8x | Zero Training (mmap Native) | Zero-Copy Memory Mapped | Embedded Scalar Approximation | Pure Go Local Codebase Search |
| **Qdrant 1.18 (TurboQuant Engine)** | 1-bit to 4-bit | 8x to 32x | Precomputed Standard Centroids | AVX-512 / NEON SIMD | Anisotropy Compensation & Renormalization | Production Scale Vector Deployment |

> [!WARNING]
> **Superseded by [ADR-0010](../../08-decisions/0010-defer-exotic-components.md).** The passage below describes an approach that was evaluated and rejected. Retained for the reasoning only. Do not implement.

SAGIHA implements a hybrid retrieval engine combining lexical BM25 sparse indexes with dense TurboQuant-compressed vectors managed by LanceDB and sqlite-vec. For local embedded search scenarios, the harness utilizes tqdb memory-mapped quantization storage, enabling search execution directly over mapped files without decompressing vectors into floating-point arrays.

### **Tri-Tier Persistence Layer Architecture**

SAGIHA organizes state persistence across three unified adapters to maintain structural consistency and support rollback capabilities:

> * **Short-Term Memory (STM)**: In-memory sliding ring buffer over the active session, durably backed by the same SQLite-WAL store as the trajectory. **Redis is not adopted.** STM is per-session and small, it needs durability co-located with the trajectory rather than a network hop, and SQLite-WAL already supplies persistence, crash recovery, and queryability. Introducing a second daemon buys nothing at single-node scale, and the multi-node case that would justify it is not on the roadmap.
> * **Transaction Store**: SQLite with write-ahead logging and append-only event sourcing for step trajectories, tool payloads, diff deltas, and checkpoints. Scores arrive as separate `StepScored` events rather than mutations of stored steps, which is what makes "append-only" true rather than aspirational.
> * **Long-Term Memory (LTM)**: Split deliberately into two stores with different epistemics — see below.

#### **The Code Graph and the Episodic Graph Are Not the Same System**

Earlier revisions routed both structural code facts and learned experience through a single temporal graph engine. That conflation is expensive and unsound, because the two have entirely different sources of truth:

> * **Deterministic code graph** — imports, call edges, definitions, inheritance, ownership, co-change coupling. These are *exactly derivable* from Tree-sitter and git. Passing them through LLM-based entity extraction pays tokens and latency for facts a parser already knows with certainty, and admits hallucinated edges into the dependency graph that downstream impact analysis then trusts. This tier is built directly by the indexer into SQLite tables, or an embedded property store such as Kùzu when recursive traversal outgrows SQL — embedded either way, which preserves the local-first principle that a Neo4j daemon would break. It is cheap, exact, and fully rebuildable from HEAD.
> * **Episodic and decision memory** — ADRs, pull-request rationale, "we tried X and it failed because Y", operator preferences. Here the facts are genuinely unstructured, genuinely contested, and genuinely change validity over time. This is where bi-temporal modelling and LLM extraction earn their cost, and where an engine such as Graphiti applies.

**A note on bi-temporality for code**: git is already a bi-temporal store. Valid time is commit time, transaction time is index time, and structure can simply be re-derived at any ref. Rebuilding that inside a graph database duplicates version control. Temporal invalidation is reserved for learned facts, which git does not track.

### **Protocol Standardization: Model Context Protocol (MCP) vs. Agent-to-Agent (A2A)**

Standardizing agent communication protocols requires distinguishing between vertical tool integration and horizontal inter-agent collaboration.

| Architectural Feature | Model Context Protocol (MCP) | Agent-to-Agent Protocol (A2A) |
| :---- | :---- | :---- |
| **Primary Integration Axis** | **Vertical Integration**: Single Agent to Local Tools and Resources | **Horizontal Collaboration**: Agent-to-Agent Peer Orchestration |
| **Governing Entity & Origin** | Anthropic (November 2024\) | Google / Linux Foundation (April 2025\) |
| **Capability Discovery** | JSON-RPC 2.0 handshake over standard IO / HTTP-SSE | Standardized JSON metadata published at /.well-known/agent-card.json |
| **Core Abstraction Primitives** | Tools, Prompts, Resources, Resource Templates | Skills, Tasks, Messages, Parts (TextPart, FilePart, DataPart) |
| **Transport Layer Mechanisms** | Stdio pipes, HTTP with Server-Sent Events (SSE) | HTTPS with JSON-RPC 2.0, SSE streaming, gRPC bindings (v.3+) |
| **Task Lifecycle Management** | Synchronous tool execution calls | Asynchronous state machine (submitted, working, input-required, completed, failed) |
| **Security & Authentication** | Local process boundaries, environment variable tokens | Enterprise OAuth, Bearer tokens, API keys, mutual TLS (mTLS) |

MCP defines a standard interface for agents to discover and invoke local host tools, inspect language server diagnostics, and read filesystem structures. A2A provides an enterprise framework for asynchronous, cross-system agent collaboration.  
In SAGIHA, an Orchestrator Super-Agent uses A2A to dispatch sub-tasks—such as writing an integration test or optimizing a database query—to remote specialized sub-agents. The sub-agent receives the task via an A2A task lifecycle, executes local tools via MCP servers, streams real-time updates over SSE, and submits completed artifacts back to the orchestrator.

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

> [!IMPORTANT]
> **The interface definitions that were here have been removed, not moved.**
>
> This section previously carried ~500 lines of `Protocol` and `BaseModel` definitions. They had
> drifted: they still described `Grant` parameters on `Workspace` methods,
> `CodeGraph.query(cypher_or_sql)`, `stream() -> AsyncIterator[ContentBlock]`, and a five-boolean
> `GateReport` — all superseded. Because this file is long-form rationale rather than specification,
> a reader retrieving over `docs/` had no signal that those signatures were dead.
>
> **The contracts live in [Hexagonal Ports](../../03-contracts-and-models/hexagonal-ports.md) and
> [Domain Schemas](../../03-contracts-and-models/domain-schemas.md), and nowhere else.** They are not
> restated here, because a contract stated in two places is a contradiction with a delay fuse.

What remains in this file is the **derivation**: the research, comparative analysis, and failure-mode
reasoning that produced those contracts. Read this to understand *why* a contract has the shape it
has. Read `03-contracts-and-models/` to know *what* the contract is.

The contract rules that govern the boundary — no `Dict[str, Any]` across a port, domain language never
storage language, aware-UTC timestamps, wire-implementability, and static-plus-conformance
verification over `@runtime_checkable` — are stated normatively in
[Hexagonal Ports](../../03-contracts-and-models/hexagonal-ports.md).


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

SAGIHA integrates a hybrid retrieval architecture combining sparse lexical search, graph traversal, and — eventually — dense vector search.

> [!WARNING]
> **Phase 2 below is deferred by [ADR-0014](../../08-decisions/0014-defer-dense-retrieval.md).** v1 runs
> phases 1 and 3 only: BM25/FTS5 plus code-graph expansion. The dense tier is gated on a measured
> recall@10 trigger, and the `EmbeddingProvider` port ships with no adapter behind it. The three-phase
> pipeline below describes the destination, not the v1 system.

When an agent initiates context retrieval for a code refactoring task, the pipeline is:

> 1. **Lexical Sparse Search**: BM25 keyword matching via SQLite-FTS5 extracts exact symbol names, class definitions, and error string matches. For code, exact-symbol lexical matching is the single strongest signal and is never demoted below dense retrieval.
> 2. **Dense Search** *(deferred)*: The query is embedded and scored against the vector index. When adopted, it starts as an exhaustive SIMD scan; see the sizing note below before adopting a quantizer.
> 3. **Graph Expansion**: The deterministic code graph expands the candidate set along import, call, and co-change edges, then episodic memory contributes decisions and rationale filtered to those still valid at read time.

**Chunking is the dominant variable.** Retrieval quality for code is governed far more by how source is split into retrievable units than by how those units are stored or compressed — and chunking is the least glamorous part of a retrieval stack, which is why effort routinely goes to the ranking layer instead. The unit is the **AST-bounded span** — a function, method, or class body emitted by Tree-sitter — prefixed with its enclosing file path, module docstring, and symbol path so a retrieved fragment carries the context needed to interpret it. Oversized bodies split on statement boundaries with the signature repeated in each part. Retrieval is evaluated directly, as recall@k against a labelled query set drawn from the target repository, and that number is the metric to move.

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

To enable multi-agent collaboration without file modification conflicts, SAGIHA isolates sub-agent execution contexts using Git worktrees and containerized sandboxes.

### **Git Worktree Concurrency and Lifecycle Management**

Instead of creating complete repository clones or allowing parallel sub-agents to operate within a shared working directory, SAGIHA assigns each sub-agent an isolated Git worktree attached to a separate branch.  
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

To optimize execution latency and token costs, SAGIHA integrates non-LLM machine learning models that act as deterministic co-processors.

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

SAGIHA employs Recursive Harness Self-Improvement (RHI) to systematically evolve its system prompts, context compaction parameters, and tool execution scaffolding over time.

### **Harness Evolution Cycle and Multi-Tier Verification**

The outer-loop self-evolution framework operates continuously across four operational steps:

> 1. **Trajectory Ingestion**: Traces, tool logs, and step scores are written through the **EventBus** and persisted by independent subscribers (TrajectoryStore and, later, an OTel GenAI exporter), following the OTel **GenAI semantic conventions** so ecosystem tooling works without bespoke adapters. The EventBus is the single source of truth; the span log and the trajectory store are **not** derived from each other — see [Microkernel & Bus](../../02-architecture/microkernel-and-bus.md).
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
> * *Mitigation Strategy*: SAGIHA implements a staged fallback protocol. If an edit action fails compilation or unit testing within a compacted context window, the harness automatically re-hydrates the context window with raw source files before attempting subsequent edit steps.

### **Serialization Latency in Multi-Agent Networks**

> * *Structural Failure Mode*: Relying on JSON-RPC 2.0 over HTTP-SSE across deep sub-agent hierarchies introduces message serialization overhead, high latency, and transport bloat during rapid tool dispatch loops.  
> * *Mitigation Strategy*: For co-located sub-agents running on the same host machine, use a local transport rather than HTTP-SSE.

> [!WARNING]
> **Superseded by [ADR-0010](../../08-decisions/0010-defer-exotic-components.md).** The passage below was evaluated and rejected. Retained for the reasoning only. Do not implement.
>
> *"SAGIHA utilizes high-performance gRPC over Unix domain sockets with shared memory buffers, falling back to HTTP/A2A transports only for remote cross-network calls."*
>
> The adopted answer is length-prefixed msgpack or JSON-RPC over a Unix domain socket. gRPC brings protobuf schema management across languages and a threading model that fights asyncio; it is adopted when a second consumer exists, not before. See [Performance Sidecars](../../02-architecture/performance-sidecars.md).

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
sagiha/
├── pyproject.toml
├── src/
│   └── sagiha/
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
│       │   ├── indexing/          # Tree-sitter chunker, FTS, vector tier
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
| **S: Verified Single-File Edit** | Agent resolves a failing test in one file, verified, logged, and replayable | `ModelProvider` + cassette replay, Pydantic domain models, dispatch choke point, `PolicyEngine`, SQLite-WAL trajectory store, Tree-sitter chunker + FTS, structured edit application, pytest runner, commit-per-step | ≥ 70% resolved on a pinned 30-task internal suite at ≤ $X and ≤ Y min per task; 100% of runs replay deterministically from cassettes; port conformance suite green |
| **S: Isolated & Sandboxed Execution** | Agent works in a materialized worktree inside a container with grants enforced | Worktree allocate/materialize/release, container sandbox, egress allowlist, secret redaction, resource governor, LSP supervisor with warm pooling | No run can write outside its worktree without a grant; no credential reachable from inside the sandbox; parallel runs show no port, cache, or database interference |
| **S: Retrieval & Memory That Earn Their Keep** | Retrieval measurably improves task success over a no-retrieval baseline | AST-bounded chunking, hybrid lexical + dense fusion, deterministic code graph, episodic memory with temporal reads | recall@10 ≥ target on a labelled query set from the target repo; ablation shows retrieval beats the no-retrieval control on the task suite |
| **S: Candidate Search** | Verifier-guided best-of-N with sequential repair on multi-file tasks | Candidate proposal, hard gates, pristine injected test suite, graph-partitioned decomposition, escalation ladder | Best-of-N beats single-shot on the suite by more than the measured A/A noise floor; zero instances of a candidate modifying its own grader |
| **S: Measured Self-Improvement** | Outer loop proposes mutations that survive statistical scrutiny | Commit-replay benchmark harvester, PRM scorer, calibrated AOI in shadow mode, Meta-Improver with TCB path restrictions, human sign-off gate | A/A noise floor established and published; every accepted mutation beats it under paired evaluation with multiple-comparison correction; TCB diffs rejected by CI in 100% of attempts |

**Deferred until a measurement demands them:** compiled sidecars, gRPC transport, vector quantization, external graph daemons, Redis, A2A, and tree search with backpropagation. Each has a named trigger condition in the migration matrix rather than a calendar slot.

## **Strategic Conclusions**

The **SAGIHA** specification defines a Meta-Harness for autonomous software engineering agents built on hexagonal boundaries, isolated worktrees inside real sandboxes, split deterministic and episodic memory, standardized protocols, and advisory local models — addressing the failure modes that dominate agent runtimes in practice: context degradation, execution locking, API cost, and fragile scaffolding.

**What this revision deliberately changed.** The prior specification's ambition outran its foundations in four ways, each now corrected in the text above. Its ports were storage drivers rather than domain contracts, and would have broken at the first adapter migration the roadmap itself called for. Its Control layer existed only in prose, with no interception point anywhere in the type system. Its self-improvement loop could edit its own evaluator and deploy without human sign-off. And its complexity was front-loaded onto exotic components — quantization, tree search, compiled sidecars, temporal graphs for facts a parser already knows — while the components that actually determine whether a coding agent works were unspecified: the model port, context and cache layout, chunking strategy, edit application, and error recovery.

The corrected sequencing is deliberately unglamorous. Boring components first, measured before replaced, each exotic addition gated on a number rather than a date. The hexagonal discipline is what makes that sequencing safe: a query-shaped `Indexer` port admits a compiled sidecar later without touching a consumer, and a domain-shaped `Memory` port admits a temporal graph without a caller knowing. Deferral costs nothing when the seams are drawn correctly, which is the entire return on drawing them correctly at Day Zero.

#### **References**

> 4. GitHub - getzep/graphiti: Build Real-Time Knowledge Graphs for AI Agents, https://github.com/getzep/graphiti
> 5. Graphiti — Zep, https://www.getzep.com/platform/graphiti/
> 6. Zep: A Temporal Knowledge Graph Architecture for Agent Memory - GraphRAG, https://graphrag.com/appendices/research/2501.13956/
> 8. TurboQuant in Qdrant, https://qdrant.tech/articles/turboquant-quantization/
> 9. TurboQuant quantization (ICLR 2026) · Issue #8524 - GitHub, https://github.com/qdrant/qdrant/issues/8524
> 10. TURBOQUANT: ONLINE VECTOR QUANTIZATION WITH NEAR-OPTIMAL DISTORTION RATE - OpenReview, https://openreview.net/pdf?id=tO3ASKZlok
> 11. TurboQuant: Redefining AI efficiency with extreme compression - Google Research, https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/
> 15. [2606.21448] Fast-TurboQuant: A Multiplier-Free Online Vector Quantization Approach, https://arxiv.org/abs/2606.21448
> 16. Building a Vector Database That Never Decompresses Your Vectors - Embedded Thought, https://scotteveritt.github.io/blog/quantization-native-vector-database/
> 17. What Is the Agent-to-Agent (A2A) Protocol? A Guide for API Teams - Zuplo, https://zuplo.com/learning-center/agent-to-agent-a2a-protocol-guide
> 18. Google A2A Protocol: How Agent-to-Agent Coordination Works - Atlan, https://atlan.com/know/google-a2a-protocol/
