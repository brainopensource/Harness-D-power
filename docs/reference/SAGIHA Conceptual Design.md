# **SAGIHA — Super AGI Harness Agent**

### **A Self-Evolving Multi-LLM Orchestration Framework for Autonomous Software Engineering**

**Version:** Conceptual Design (July 2026) — revised against architectural review
**Classification:** Agent Systems Architecture | Meta-Harness Reference Design

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a proposed architecture and architectural blueprint for SAGIHA, not an imperative or immutable final solution. Further iterative prototyping, benchmarks, and practical evaluations will be conducted to refine and finalize the ultimate harness structure.

**Core Thesis:** The intelligence resides exclusively in the LLMs. The harness is a pure, modular, evolvable environment that supplies context, memory, tools, coordination, verification, and recursive self-improvement mechanisms. The system is designed so that its own source code becomes the primary artifact it optimizes until it can generate and evolve arbitrary software projects.

## **1\. Vision & Design Philosophy**

SAGIHA is not another agent framework. It is a **Meta-Harness**: a stable, hexagonal, plugin-based runtime whose primary purpose is to turn one or more frontier LLMs into a Super-Agent capable of orchestrating specialized sub-agents, executing long-horizon coding tasks, and continuously rewriting its own scaffolding under strict verification.  
**Foundational Principles**

> * LLMs own all intelligence, planning, creativity, and decision-making.  
> * The harness owns only: context assembly, memory, tool contracts, orchestration primitives, verification, observability, and safety boundaries.  
> * Zero coupling between domain logic and infrastructure (hexagonal \+ ports & adapters), enforced by conformance suites and import-graph contracts in CI rather than by convention.
> * Every functional block is independently replaceable without changing external contracts — which requires ports written in domain language, since a port phrased in storage terms silently welds one implementation into the core.
> * SOLID \+ DRY \+ Clean Code, with **explicit composition over dependency-injection containers**: dynamic wiring defeats the static analysis that both human and agent maintainers depend on.
> * **Boring components first, measured before replaced.** Every advanced component carries a trigger condition rather than a scheduled slot.
> * Model–Harness Co-evolution as first-class citizen, bounded by an immutable trusted computing base the improver cannot edit.
> * Separation of Generator and Evaluator, with the evaluator's inputs placed beyond the generator's reach.
> * Bounded Recursive Self-Improvement with held-out validation, calibrated against a measured noise floor, deployed only on human sign-off.
> * **Untrusted by default**: repository and web content is data, never instruction.

## **2\. High-Level Architecture**

┌─────────────────────────────────────────────────────────────────────────────┐  
│                     Super-Orchestrator LLM (Primary Intelligence)           │  
│              (owns goals, decomposition, meta-reasoning, final decisions)   │  
└───────────────────────────────┬─────────────────────────────────────────────┘  
                                │ A2A \+ MCP \+ Typed Ports  
┌───────────────────────────────▼─────────────────────────────────────────────┐  
│                         SAGIHA Meta-Harness Kernel                         │  
│  • Composition Root      • Lifecycle & Checkpoint Manager                   │  
│  • Dispatch Choke Point  • Observability (OTel GenAI \+ Trajectory Store)    │  
│  • Policy Engine (TCB)   • Resource Governor (concurrency, spend, leases)   │  
│  • Capability Grants     • Self-Improvement Outer Loop Controller           │  
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────────┘  
    │      │      │      │      │      │      │      │      │  
┌───▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──────────────┐  
│Model ││ STM ││ LTM ││Index││Graph││Tools││Work-││Orch.││ Eval \+ Meta     │  
│      ││     ││     ││     ││     ││+MCP ││space││     ││ (Outer Loop)    │  
└──────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────┘└─────────────────┘  
   ▲        ▲       ▲       ▲       ▲       ▲       ▲       ▲         ▲  
Adapters — interchangeable under stable Ports, verified by conformance suites

**Where the CAR boundary falls.** Agency (deliberation) holds no reference to Runtime
objects and emits intents only. Every effect passes through the kernel's single dispatch
choke point, where the Policy Engine authorizes it and mints a capability `Grant` that
Runtime methods require. Policy is therefore non-bypassable by construction rather than
by discipline, and the import-graph contract forbidding `agency/ → runtime/` is checked
in CI. Native sidecars are not a layer in this model; they are a deployment topology a
port's adapter may adopt once measurement justifies it.

**Key Separation**

> * **Inner Loop**: Task execution (DMARTIC \+ coding agents).  
> * **Outer Loop (Meta-Harness)**: Improvement of the harness itself (prompts, flows, adapters, policies) under held-out metrics.

## **3\. Functional Blocks (Plugin Architecture)**

Every block exposes a minimal, stable **Port** (Protocol / Interface). Implementations are pure adapters.

| Block | Port Name | Initial Adapter (Day 0) | Later Adapters | Responsibility |
| :---- | :---- | :---- | :---- | :---- |
| **Model Access** | **ModelProvider** | **Provider client + record/replay cassette** | **Multi-provider routing, local models** | **Streaming, tool schemas, retries, token accounting, cache breakpoints** |
| **Policy & Control** | **PolicyEngine** | **Static policy + capability grants** | **Risk-classified policy, learned escalation** | **Authorizing every effect; minting grants** |
| **Admission Control** | **ResourceGovernor** | **In-process semaphore + spend ledger** | **Distributed leases** | **Concurrency, rate limits, budget enforcement** |
| Short-Term Memory | ShortTermMemory | In-memory ring buffer over SQLite-WAL | Trajectory-compressed context ring | Session context, step trajectories, compaction |
| Long-Term Memory | Memory | SQLite + sqlite-vec | LanceDB; episodic temporal graph | Durable knowledge, decisions, preferences |
| **Code Graph** | **CodeGraph** | **SQLite tables from Tree-sitter + git** | **Embedded property store (Kùzu)** | **Deterministic imports, calls, ownership, co-change** |
| Indexing | Indexer | Tree-sitter chunker + FTS5 + dense tier | Out-of-process index service | Symbol lookup, skeletons, neighbors — query-shaped only |
| Language Diagnostics | LSPAdapter | Warm server supervisor over stdio LSP | Pooled multi-language supervisor | Type checking, diagnostics, definitions, references |
| Tools & Scripts | ToolRegistry | Local functions + stdio MCP | Full MCP ecosystem | Tool discovery and dispatch under grants |
| **Workspace** | **Workspace** | **Mediated FS + subprocess** | **Container / remote runtime** | **Read, write, structured edit, run, checkpoint, restore** |
| **Trajectory** | **TrajectoryStore** | **Append-only SQLite + OTel GenAI spans** | **Columnar analytics store** | **Replay, audit, outer-loop training data** |
| Orchestration | Orchestrator | Native async microkernel (ReAct) | Candidate search + A2A delegation | Agent lifecycle, state machine, DMARTIC engine |
| Candidate Search | CandidateSearch | Best-of-N + sequential repair | Tree search, once a calibrated value model exists | Exploring and selecting alternative solutions |
| Evaluation | Evaluator | Pytest against pristine injected suite | Multi-judge + PRM scoring | Independent quality gate |
| Meta-Improvement | MetaImprover | Propose-Evaluate-Accept, human sign-off | RHI under held-out validation | Evolution of the *mutable* surface only |

Rows in **bold** are ports the prior revision lacked entirely. Their absence was not cosmetic: without `ModelProvider` the system had no contract for its single most important dependency, and without `PolicyEngine` the Control layer of the CAR model had no interface at all.

**Contract Guarantee**: replacing any adapter never requires changes to consumers.

This guarantee is only worth stating if it is *enforced*, and enforcement is a specific mechanism rather than a discipline. Two rules make it real:

> * **Ports speak domain language, never storage language.** A port with `store_vector(key, vector: list[float])` is a vector-database driver wearing a Protocol: it forces the core to own the embedding model, and it cannot accept a temporal graph engine that takes text episodes and has no vector to receive. The earlier LTM port had exactly this shape, and would therefore have broken against this document's own Day-2 migration target. `remember()` / `recall()` survives that swap; `store_vector()` cannot.
> * **Conformance suites, not `isinstance`.** `@runtime_checkable` verifies method *presence* only, never signatures, so an adapter with wrong argument types passes it. Every port instead owns a behavioral conformance suite in `tests/contracts/`, parametrized across every adapter implementing it, run in CI. That suite is what makes the migration matrix safe to execute; without it, "swappable" is an aspiration that fails silently on the day it is first exercised.

## **4\. Core Workflows**

### **4.1 DMARTIC Cycle (Inner Loop — Dual-Process Cognitive Engine)**

The inner loop operates as a Dual-Process Cognitive Engine:
* **System 1 (Fast Execution):** Direct ReAct single-turn execution for low-complexity, localized edits.
* **System 2 (Deliberate Search):** Verifier-guided **best-of-N with sequential repair** across parallel worktrees, for multi-file refactoring and architectural change.

**On the name.** System 2 is deliberately not called MCTS. Monte Carlo Tree Search requires a persistent tree, visit counts, UCT selection, and backpropagation of values to ancestors; proposing *n* candidates and scoring each is best-of-N at depth one. Naming it MCTS invites building machinery the system does not need and cannot yet afford — MCTS assumes cheap rollouts, whereas one expansion here costs a full agent run plus a test suite, putting a branching factor of 3 at depth 3 near thirty leaf evaluations in minutes and dollars. Best-of-N against a strong verifier, plus sequential repair of the best failing candidate, is the higher-yield technique at this cost profile. Tree search with backpropagation is deferred until a **calibrated** value model exists, which makes the PRM a hard prerequisite rather than a peer deliverable.

Extended DMARTIC execution sequence:

> 1. **Concept** — Goal formulation, requirement parsing, and hypothesis generation, producing a `TaskSpec` with machine-checkable acceptance criteria
> 2. **Design** — Architectural plan and decomposition; route by the deterministic escalation ladder (System 1 first; escalate on repeated failure, multi-file scope, or diff size)
> 3. **Measure** — Baseline static analysis, LSP diagnostics, and coverage collection
> 4. **Analyze** — Query the code index, deterministic code graph, and episodic memory
> 5. **Review** — Independent Evaluator check; Plan Mode gate for high-risk actions, as a durable approval request rather than a synchronous prompt
> 6. **Test** — Speculative execution inside parallel worktrees, verified against a **pristine injected copy** of the test suite the candidate cannot reach
> 7. **Improve** — Admit candidates through hard gates, rank survivors by score, repair sequentially on failure
> 8. **Control** — Policy and budget validation, land the winning candidate, invalidate stale episodic facts
> 9. **Self-Reflect** — Trajectory compaction and event log commit

**Why gates and scores are separate.** Diagnostic deltas and coverage are proxies, and each is trivially gamed by deleting failing code, adding a suppression, widening a type, or swallowing an exception. Proxies may *rank* candidates; only hard gates may *admit* one. The single most important gate is that a candidate has not modified the tests it is scored against — with full filesystem access to its own worktree, an agent can otherwise edit its own grader, and any selection built on that measurement is meaningless.

### **4.2 Outer Loop — Recursive Harness Self-Improvement (RHI)**

> * Represent harness behavior as editable artifacts — **but only within the mutable surface**: prompts, workflows, retrieval and compaction parameters, tool descriptions, routing heuristics, and non-Control adapter code.
> * **The trusted computing base is not editable**: the policy engine, the Evaluator, the gate and benchmark definitions, secret handling, the sandbox boundary, and the deployment gate itself. A self-improving system able to modify its own evaluator has a trivial optimum — modify the evaluator. Enforced by path allowlist, by residing where the agent cannot push, and by CI rejection.
> * Outer agent proposes modifications; the AOI pre-filter ranks them so that only promising candidates reach expensive evaluation.
> * **Establish the noise floor before measuring anything.** Run the unmodified harness against the suite twice (A/A) to characterize the score-delta distribution under pure stochasticity. Most harness mutations produce effects smaller than run-to-run variance, so "accept if the score improved" ratchets permanently on noise without this baseline.
> * Evaluate on a **held-out** suite never seen by the improver, using paired runs with fixed seeds, k ≥ 3 repetitions per task, reporting variance rather than a point estimate, with the acceptance threshold corrected for multiple comparisons — screening many candidates against one threshold manufactures winners from noise.
> * Accept only if the improvement exceeds the noise floor and no safety or cost metric regresses.
> * **Deployment requires human sign-off.** Validated mutations are staged, never self-committed to the production baseline.
> * Version every accepted change with full trajectory and diff.
> * Budget deliberately: a few hundred tasks × several dollars × k repetitions × many candidates puts one outer-loop iteration in the thousands of dollars, which is why the loop is scheduled rather than continuous.

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

> * Primary Control Plane: Python 3.13+ (async-first, Pydantic v2 + typing.Protocol)
> * High-Performance Sidecars: **deferred, and scoped down when they arrive.** See the sidecar note below.
> * Optional UI/IDE Layer: TypeScript / React

**Sidecar reassessment.** The original rationale — compiled services so the Python event loop stays unblocked — is satisfied far more cheaply by `asyncio.to_thread` and a process pool. A separate compiled service is justified only when a process must stay warm holding large in-memory state. Three consequences follow:

> * **Draw the boundary at the query, never at parsing.** A sidecar that returns ASTs or bulk symbol tables serializes the entire structure across the process boundary and rebuilds it as Python objects, reintroducing precisely the cost the sidecar existed to avoid. The `Indexer` port is therefore query-shaped (`find_symbols`, `get_skeleton`, `neighbors`), which both keeps payloads small and lets the index move out of process later without touching a consumer.
> * **The Go vector sidecar is dropped.** LanceDB is already Rust, embeds in-process, memory-maps, and returns zero-copy Arrow with no IPC at all; Qdrant already ships a production TurboQuant engine. Building `tq_vector_go` would duplicate two mature engines and add a second language toolchain — doubling build, CI, cross-compilation, release, and debugging burden for no architectural gain. One sidecar language at most, and zero for now.
> * **No LSP daemon sidecar is written.** Language servers *are* already daemons speaking JSON-RPC over stdio; wrapping them in another compiled service adds indirection, not speed. The real problems are cold-start latency on large repositories, `didChange` synchronization for unsaved edits, and **server explosion under parallel search** — N worktrees × M languages, each with its own server, exhausts memory. The answer is a Python supervisor holding warm servers driven by in-memory document overlays with a bounded pool, not one server per worktree.

The Rust AST indexer remains a legitimate future option, gated on a measured Python baseline. `py-tree-sitter` binds the same C library, and multiprocessing across files typically recovers most of the available gain, so the ≥5× indexing target may well be met without leaving Python.

**Orchestration Core**

> * Native Async Microkernel: Deterministic event-bus and state machine kernel (zero external framework lock-in)  
> * LangGraph / Microsoft Agent Framework: Supported strictly as optional external adapters behind the `Orchestrator` Port

**Memory & Retrieval**

> * STM: In-memory sliding buffer durably backed by SQLite-WAL. **Redis is not adopted** — STM is per-session and small, wants durability co-located with the trajectory rather than a network hop, and SQLite-WAL already provides persistence, crash recovery, and queryability. A second daemon earns nothing at single-node scale.
> * LTM / Index: SQLite + sqlite-vec (Day 0) → LanceDB. Quantization is adopted against a measured ceiling, not on schedule: a large repository chunks to ~10⁵–10⁶ vectors, where an exhaustive SIMD scan runs in single-digit milliseconds and compression solves a problem the system does not have. **Chunking strategy, hybrid fusion, and reranking govern retrieval quality far more than the quantizer**, and are specified in the retrieval module.
> * Graph: **split by epistemics.** Deterministic code structure (imports, calls, ownership, co-change) is derived exactly from Tree-sitter and git into SQLite, or an embedded store such as Kùzu — never through LLM extraction, which charges tokens for facts the parser already knows and admits hallucinated edges into dependency analysis. Episodic and decision memory, where facts are genuinely unstructured and lose validity over time, is where a bi-temporal engine such as Graphiti earns its cost. Note that git is already bi-temporal for code: valid time is commit time, and structure re-derives at any ref.

**Execution Safety & Language Tooling**

> * Container / gVisor (runsc) sandboxes per agent — **required early, not deferred**. The sandbox is the security perimeter; command-string blocklisting is a usability guardrail that fails to `bash -c`, `python -c`, base64, `$IFS`, and symlinks. If the agent has a shell, it has whatever the sandbox grants that shell.
> * Git worktrees for parallel branch exploration, with an explicit **materialization** step for ignored-but-required artifacts (`.env`, `node_modules`, `.venv`), without which every build fails on a fresh worktree.
> * LSP Integration: warm server supervisor with pooling and document overlays for real-time diagnostics.

**Observability & Governance**

> * OpenTelemetry + custom Trajectory Store  
> * Cost, latency, token, success-rate dashboards  
> * Circuit breakers, budgets, autonomy policies (configurable per domain risk)

**Evaluation**

> * **Commit-replay harvesting as the primary suite**: mine real commits from the target repository's history, revert them, and pose them as tasks. This yields an unbounded, uncontaminated, in-distribution benchmark that stays current as the repository evolves — and removes the need to hand-author synthetic bugs whose distribution nobody can defend.
> * Public suites as a smoke test only. **SWE-bench Lite is unsuitable as a primary screen**: it is contaminated across frontier models, Python-only, and shaped as single-repo issue resolution, which is not the long-horizon multi-file target. Prefer SWE-bench Verified and Multi-SWE-bench where public comparison is wanted.
> * Retrieval evaluated on its own terms, as recall@k against a labelled query set from the target repository. **LongMemEval measures conversational memory, not code retrieval**, and cannot support a claim about repository search.
> * Public/private score split; multi-judge and process reward models; A/A noise-floor calibration before any comparison is believed.

## **7\. Safety, Autonomy & Control**

> * Autonomy levels: Interactive → Hybrid → Fully Autonomous → Scheduled
> * Human-in-the-loop gates by risk class, delivered as **durable, asynchronous approval requests** — nobody watches a six-hour run, so a gate that requires someone present is a gate that will be disabled. Requests survive restarts, notify out of band, deny by default on timeout, and resume cleanly on approval.
> * Immutable audit log of every decision, grant, and harness mutation
> * Hard iteration / token / wall-time limits, enforced centrally by the `ResourceGovernor` — parallel agents against a frontier API otherwise exhaust rate limits and spend wall-clock in retries
> * **The sandbox is the security perimeter.** Command-string blocklisting is a usability guardrail and nothing more: it fails to `bash -c`, `python -c`, base64, `$IFS`, and symlinks. Credentials stay outside the sandbox, egress is allowlisted at the network namespace, and secrets are redacted from output before entering memory or logs.
> * **Repository and web content is untrusted data, never instruction.** An autonomous agent reading issues, READMEs, comments, and dependencies while holding shell access is the canonical prompt-injection target; retrieved content is delimited and labelled as data, and no content encountered in tool output carries authority.
> * Writes outside the worktree, and any action touching credentials, CI configuration, or harness policy, require an explicit human grant at every autonomy level.
> * Self-improvement accepted only after multi-metric held-out validation against a measured noise floor, and deployed only on human sign-off.

## **8\. Phased Adapter Migration Matrix (Day 0 → Day N Evolution)**

The authoritative roadmap is the **vertical slice plan** in `07-roadmap/phased-migration-matrix.md`. Each slice cuts thin through every layer and is independently useful, because the risk in this system lives in integration rather than in any single component. The matrix below is the component appendix to that plan, and every advanced entry carries a **trigger condition** instead of a date — a component migrates when a measurement demands it, never because a phase elapsed.

| Component | Day 0 (Baseline) | Day 1 (Production) | Later — and its trigger |
| :---- | :---- | :---- | :---- |
| **Model Access** | Provider client + record/replay cassettes | Cache-aware assembly, budget accounting | Multi-provider routing — *when cost or availability data justifies it* |
| **Kernel Orchestrator** | Native async ReAct loop | State machine + checkpoints | Candidate search; A2A fleet — *when single-agent plateaus on multi-file tasks* |
| **Control Layer** | Static policy + capability grants | Risk-classified gates, durable approvals | Learned escalation — *once approval history exists* |
| **Short-Term Memory** | Ring buffer over SQLite-WAL | Compaction at checkpoints | Trajectory-compressed ring — *when sessions exceed the window routinely* |
| **Long-Term Memory** | SQLite + sqlite-vec | LanceDB | Episodic temporal graph — *when decision recall demonstrably fails* |
| **Code Graph** | SQLite tables from Tree-sitter + git | Impact closure queries | Embedded property store — *when recursive traversal outgrows SQL* |
| **Indexing Engine** | AST-bounded chunking + FTS5 + dense tier | Incremental update on file watch | Out-of-process index service — *when measured Python indexing misses its latency budget* |
| **Diagnostic Layer** | Subprocess pytest + linter | Warm LSP supervisor with pooling | Broader language coverage — *per language actually used* |
| **Execution Sandbox** | Local subprocess + worktree | **Container + materialization + egress allowlist** | gVisor — *when the threat model requires syscall-level isolation* |
| **Protocol Integration** | Stdio MCP drivers | HTTP-SSE MCP | A2A — *when a genuinely remote peer agent exists* |
| **Self-Improvement** | Manual iteration | PRM scoring in shadow mode | RHI under held-out validation — *once the A/A noise floor is established* |

**Two corrections to the previous matrix.** Containerization moved earlier: it is the only mechanism that makes the isolation claim true, so treating it as a late performance concern left the Day-1 gate ("zero cross-branch contamination") unreachable by construction. And the previous Day-2 LTM entry would have broken the contract guarantee, because the port it had to satisfy demanded a vector that a temporal graph engine has no way to accept.

## **9\. Package Structure (Clean Architecture)**

```
sagiha/
├── composition.py          # THE composition root. Explicit wiring, no container.
├── ports/                  # All Protocols. Imports nothing internal.
├── domain/                 # Pydantic models. Pure: no I/O, no adapter imports.
├── kernel/                 # Dispatch choke point, policy (TCB), governor, bus
├── agency/                 # Deliberation. CI forbids importing runtime/ or adapters/
├── runtime/                # Worktree, sandbox, structured edit application
├── adapters/               # Concrete implementations behind ports
│   ├── model/              # Provider clients + record/replay cassette
│   ├── memory/             # SQLite baseline; episodic graph
│   ├── indexing/           # Chunker, FTS5, dense tier, code graph
│   ├── lsp/                # Warm server supervisor
│   └── tools/              # MCP client drivers
├── aoi/                    # Advisory only, shadow mode by default
├── outer_loop/             # Meta-Improver, path-restricted away from the TCB
├── observability/          # OTel GenAI conventions; trajectory store
├── benchmarks/             # Commit-replay harvester + public suite runners
└── tests/contracts/        # Per-port conformance suites, parametrized over adapters
```

**On the DI container and plugin discovery.** Both are dropped in favor of a single explicit composition root. A container with runtime plugin discovery defeats static analysis: type checkers cannot see dynamically registered implementations, and neither can "go to definition." Since this codebase's principal maintainer is an LLM navigating it through a language server — the system's own stated purpose — static navigability is a first-class architectural requirement, not a style preference. Explicit imports and one wiring function are strictly better here than dynamic indirection.

**On layering enforcement.** `agency/` not importing `runtime/` is not a convention; it is an import-linter contract checked in CI. Architectural boundaries that exist only in prose are boundaries that erode.

## **10\. Success Metrics (World-Class Definition)**

Every metric below is reported **with variance across k ≥ 3 runs**, never as a point estimate, and every comparison is judged against the measured A/A noise floor. A single-run number from a stochastic system is an anecdote.

> * Task success rate on a pinned internal suite plus commit-replay splits, with public suites as smoke tests only
> * Self-improvement delta per outer-loop iteration, **net of the noise floor** and corrected for multiple comparisons
> * Cost and latency per *successful* task, tracked alongside cache hit rate — a token-reduction claim that ignores cache economics measures the wrong quantity
> * Regression rate after harness mutations
> * Retrieval recall@k on a labelled query set from the target repository, reported separately from task success so retrieval regressions are attributable
> * Replay fidelity: fraction of recorded trajectories that replay deterministically from cassettes
> * Human intervention rate, segmented by whether the intervention was a *policy gate* (working as designed) or a *rescue* (a failure)
> * Ability to generate and maintain its own subsequent versions

## **11\. Closing Statement**

SAGIHA synthesizes what the original specification required — modular hexagonal packages, DMARTIC, replaceable indexing, LLM-centric intelligence — with what it lacked: independent evaluation whose inputs the generator cannot reach, self-improvement bounded by an immutable trusted computing base, a real security perimeter, and honest measurement.

The harness remains deliberately "dumb." All intelligence, creativity, and ambition live in the models. The Meta-Harness's only job is to give those models the richest possible environment in which to think, act, verify, and improve — including the environment itself.

**And the discipline that makes that possible is restraint.** The failure mode for a document like this one is not insufficient ambition; it is building the exotic components first. Quantization, tree search, compiled sidecars, and temporal graphs are legible and satisfying to design. What actually determines whether a coding agent works is the model port, context and cache layout, chunking, edit application, feedback latency, and error recovery — none of which appeared in the previous revision at all. Correct seams are what make deferral free: a query-shaped `Indexer` accepts a compiled sidecar later without touching a consumer, and a domain-shaped `Memory` accepts a temporal graph without a caller noticing. That is the entire return on drawing the hexagon properly at Day Zero, and it is why the roadmap now trades scheduled sophistication for triggered sophistication.

This is the architecture of a system that does not merely use AI to write code. It is the architecture of a system that uses AI to become a better system for writing code — and that can prove the improvement is real.

## **12\. Incremental Improvements from Grok Build (v1.1)**

The following enhancements are incorporated from the publicly available Apache 2.0 Grok Build harness. They strengthen parallelism, extensibility, and operational robustness without altering the core hexagonal architecture or the Outer Loop philosophy.

### **12.1 Parallel Execution with Isolated Git Worktrees**

SAGIHA now treats **git worktrees** as a first-class isolation primitive for parallel agents:

> * Each sub-agent (or specialized worker) can be spawned inside its own worktree.
> * Tracked file changes remain isolated until explicitly selected or discarded.
> * The Orchestrator maintains a worktree registry and lifecycle (allocate, materialize, list, release, gc).
> * This enables concurrent work on one repository without file conflicts.

**A worktree isolates tracked file state and nothing else.** Stating the limit precisely
matters, because a plan that assumes full isolation from worktrees alone produces failures
that look like model errors. Not isolated: the object database (`index.lock` contention,
`git gc` races), network ports, dependency trees (`node_modules`, `.venv`, `target/` —
minutes and gigabytes per branch), global caches, dev databases, and environment
variables. Full isolation of those requires **containers with per-branch volumes and a
network namespace**, which is why containerization moves earlier in the roadmap rather
than arriving as a late performance concern.

**Materialization is a required step, not an optimization.** A fresh worktree contains
only tracked files, so `.env`, installed dependencies, and build caches are simply absent
and every build fails immediately. The lifecycle therefore links or copies
ignored-but-required artifacts before the agent runs.

**Port:**

```python
class WorktreeManager(Protocol):
    async def allocate(self, base_ref: str = "HEAD", branch: str = ...) -> Workspace: ...
    async def materialize(self, workspace: Workspace) -> None: ...
    async def release(self, branch: str) -> None: ...
```

Note that `allocate` returns a `Workspace`, not a path. Handing out a filesystem path lets
consumers call `open()` directly, which permanently forecloses substituting a container or
remote runtime — the single leak most likely to block the isolation roadmap.

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

> * **Skills** — reusable, versioned instruction + tool packages (loaded from skills/ or MCP).  
> * **Plugins** — static adapters registered via explicit composition root.
> 
> > [!WARNING]
> > **Superseded by [ADR-0004](../08-decisions/0004-explicit-wiring.md).**
> > Runtime plugin discovery and dynamic port registration are rejected. All wiring is explicit and static to preserve language-server type resolution and "go to definition" for AI agents.
> 
> * **Hooks** — lifecycle callbacks (pre-tool, post-tool, pre-plan, post-improve, etc.) that allow observation or interception without modifying core code.

### **12.4 Plan Mode with Human Review Gate**

Before any destructive or multi-file change set is applied, the system can enter **Plan Mode**:

> * The Orchestrator (or a dedicated Planner agent) produces a structured plan (files to touch, commands to run, expected outcomes).  
> * The plan is presented for human approval (or auto-approved under low-risk autonomy policies).  
> * Only after approval does the system proceed to execution (possibly spawning parallel worktree agents).

This directly implements the “plan-then-execute” pattern and strengthens the Control step of DMARTIC.

### **12.5 Workspace Abstraction & Headless Operation**

A dedicated **Workspace** port mediates every filesystem and process interaction. This
resolves a contradiction between earlier drafts, where one document defined
read/write/run/checkpoint/restore while another reduced the port to `get_path()` and
`apply_diff()`:

```python
class Workspace(Protocol):
    async def read(self, path: str) -> str: ...
    async def write(self, path: str, content: str, grant: Grant) -> None: ...
    async def apply_edit(self, diff_text: str, grant: Grant) -> EditResult: ...
    async def run(self, command: list[str], grant: Grant) -> CommandResult: ...
    async def checkpoint(self, label: str) -> str: ...
    async def restore(self, checkpoint_id: str) -> None: ...
```

Three properties are deliberate:

> * **No `get_path()`.** Exposing a real path lets consumers bypass the port entirely, which
>   would make the container and remote-runtime adapters unreachable.
> * **Side-effecting methods require a `Grant`.** The capability token is minted only by the
>   Policy Engine, so authorization cannot be forgotten at a call site.
> * **`apply_edit` returns `EditResult`, not `bool`.** Edit application is the highest-frequency
>   operation in the system; a bare boolean discards which hunks failed and why, leaving the
>   model unable to repair its own patch. The result carries per-hunk outcomes and a
>   Tree-sitter syntax check, so a structurally broken edit is rejected before the language
>   server ever sees it. Whether edits are expressed as search/replace, unified diff, or
>   whole-file rewrite is among the highest-impact empirical choices in a coding harness and
>   is settled by measurement, not assumption.

**Checkpoints are git commits inside the worktree.** Commit-per-step unifies checkpoint,
rollback, and audit at negligible cost. Replay honors `EffectClass`: only pure calls
re-execute, while idempotent and destructive calls are served from recorded observations —
without which "time-travel debugging" would happily re-run `git push` and `rm`.

> * Supports interactive sessions and fully **headless** execution (CI, scheduled runs, outer-loop experiments).
> * Local-first configuration via a single `config.toml` (model endpoints, autonomy level, worktree root, MCP servers).

### **12.6 Updated Package Structure (additions)**

See §9 for the full tree. The extension layer is retained with one constraint: hooks and
skills are discovered from explicit, declared locations rather than by scanning, so that
static analysis and "go to definition" keep working for the agent maintaining this code.

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

AOI integrates through dedicated Ports. Every prediction is a calibrated object rather
than a bare float, because a scalar carries no way to express uncertainty and therefore no
way to decide whether it may be acted upon:

```python
class Prediction(BaseModel):
    value: float
    confidence: float
    calibrated: bool          # uncalibrated predictions may never gate a decision
    shadow_mode: bool = True  # predict and log; do not act

class RewardPredictor(Protocol):
    async def score_step(self, run_id: str, step_id: StepId) -> Prediction: ...

class FailurePredictor(Protocol):
    async def predict_risk(self, run_id: str) -> Prediction: ...

class ConfigurationSelector(Protocol):
    async def select(self, task: TaskSpec, candidates: list[Config]) -> list[RankedConfig]: ...

class CostPerformanceEstimator(Protocol):
    async def estimate(self, task: TaskSpec) -> Prediction: ...
```

These Ports are wired in the composition root.
Concrete adapters may be implemented with:

> * Gradient Boosting (XGBoost, LightGBM, CatBoost)  
> * Small neural networks (PyTorch / MLX)  
> * Linear / logistic models with strong regularization  
> * Embedding-based rankers (sentence-transformers)

All adapters must support both inference and incremental/online updates.

### **14.4 Data Sources**

AOI is trained exclusively on data generated by SAGIHA itself:

> * Complete and partial trajectories (from Trajectory Store)  
> * Configuration snapshots used in each run  
> * Observed metrics: success/failure, test pass rate, cost, latency, token usage  
> * Human preference signals (when available)  
> * Outer-Loop proposal outcomes (accepted / rejected \+ reason)

Every experience is stored in a structured, versioned format that can be replayed for offline training or used for online updates.

### **14.5 Training and Update Strategies**

> * **Offline batch training**: periodic retraining on the accumulated dataset (nightly or after N new trajectories).
> * **Online / continual learning**: lightweight updates after each significant run.
> * **Experience replay \+ prioritization**: more weight to rare failures and high-impact configuration changes.
> * **Held-out protection**: a portion of the data never trains the models that influence the Outer Loop, preserving evaluation integrity.

**Correcting for censored outcomes.** A failure predictor that halts runs it expects to fail
destroys its own training signal: halted runs never produce success labels, so the model's
false positives are never observed and it confirms itself indefinitely. This is the standard
selection-bias trap in learned early stopping, and the previous specification walked straight
into it with a fixed 0.85 halt threshold. Three countermeasures are mandatory:

> * **Shadow mode first.** The model predicts and logs but does not act until a reliability
>   diagram and Brier score on held-out runs justify promotion. A threshold chosen before
>   calibration data exists is an arbitrary number wearing a decimal point.
> * **A fixed exploration fraction always runs to completion**, regardless of predicted risk,
>   which keeps the label distribution alive.
> * **Censored outcomes are never trained as negatives**, and where halting does occur,
>   training corrects the selection with inverse-propensity weighting.

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

sagiha/  
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
> * **Statistically humble**: models are narrow, calibrated, and express uncertainty. Calibration is demonstrated on held-out runs, never assumed.
> * **Advisory, never authoritative**: AOI ranks and filters; it does not admit or reject. Hard gates remain deterministic.
> * **Shadow by default**: every model ships predicting-and-logging, and is promoted to acting only on evidence.
> * **Non-blocking**: if a model is unavailable, low-confidence, or out of distribution, control reverts to deterministic policy. Degradation is always toward the safe default, never toward a stall.
> * **Fully observable**: every prediction, promotion, and update is logged in the Trajectory Store, so a model's real-world hit rate is auditable after the fact.
> * **Decoupled from deliberative intelligence**: AOI never generates plans or code; it only scores, ranks, and selects.

### **14.10 Expected Impact**

The introduction of AOI transforms SAGIHA from a system that improves itself through expensive trial-and-error into a system that improves itself through statistically guided, sample-efficient search.  
It directly addresses the core economic problem of Meta-Harness evolution: how to explore a large configuration and design space without prohibitive cost.  
**End of Technical Specification**