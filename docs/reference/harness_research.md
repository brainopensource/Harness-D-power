# Comparative Architecture and Operational Mechanics of Enterprise AI Agent Harnesses for Software Engineering

## Systemic Evolution of Coding Agent Harnesses

The transition of artificial intelligence in software engineering—from primitive autocomplete models to autonomous, goal-directed coding agents—has fundamentally shifted the design requirements of software infrastructure. Early paradigms relied on direct prompt-response loops managed by unstructured context windows. However, as language models were tasked with complex, multi-file refactoring, systemic architecture reviews, and long-horizon issue resolution, raw model capabilities proved insufficient without deterministic environment orchestration.

This necessity gave rise to the modern AI agent harness: a structured software runtime that wraps language models, enforcing strict execution boundaries, managing state persistence, optimizing context retrieval, and mediating tool interactions. An agent harness operates as the execution control layer. It converts non-deterministic neural network outputs into structured, deterministic operations within a target environment—such as local workspaces, remote containers, or version control repositories.

The underlying architecture of an enterprise-grade harness must address four fundamental engineering challenges:

1. **Context Entropy and Attentional Degradation**: As token context windows expand to millions of tokens, models suffer from retrieval degradation and increasing latency. Effective harnesses utilize graph-based syntax indexing, dynamic scope compression, and event-sourced context pruning to maintain high signal-to-noise ratios.
2. **State Divergence and Non-Deterministic Drift**: Autonomous loops frequently experience cascading errors when tool executions fail. Modern harnesses implement immutable event streams, atomic transaction logs, and checkpointing mechanisms that allow instant state rollback and step-by-step auditability.
3. **Execution Safety and Environmental Containment**: Running arbitrary LLM-generated code poses severe security risks. Harnesses implement layered containment strategies, ranging from ephemeral containerization to fine-grained write-permission policies and human-in-the-loop approval barriers.
4. **Multi-Agent Coordination and Interoperability**: Complex software projects exceed the cognitive throughput of a single model instance. Harnesses now provide IPC protocols, shared task ledgers, subagent delegation pathways, and standardized interfaces like the Model Context Protocol (MCP) and Agent Client Protocol (ACP).

---

## Deep-Dive Analysis of the Top 5 AI Agent Harnesses

### 1. Grok Build (SpaceXAI)

Grok Build is a high-performance, Rust-native terminal coding agent and harness developed by SpaceXAI. Designed for zero-latency interactive workflows, headless continuous integration scripting, and editor integration, Grok Build prioritizes deterministic tool dispatching and modular architectural decoupling.

#### Architectural Topology and Component Layout

The Grok Build codebase is structured as a modular Rust workspace managed under a strict composition-root design pattern. The separation of concerns across its primary crate closure ensures clear boundaries between the terminal UI, agent runtime logic, and system tools.

| Crate / Package Path | Operational Responsibility |
| --- | --- |
| crates/codegen/xai-grok-pager-bin | Composition-root package that compiles into the final xai-grok-pager executable |
| crates/codegen/xai-grok-pager | Manages the TUI components, scrollback buffers, prompt modals, and rendering engine |
| crates/codegen/xai-grok-shell | Drives the core agent runtime loop, standard I/O streams, leader election, and headless execution |
| crates/codegen/xai-grok-tools | Houses tool implementations, including terminal execution, file editing, and native tool ports |
| crates/codegen/xai-grok-workspace | Manages interactions with the host filesystem, version control systems, and execution checkpoints |

#### Execution Modes and Integration Standards

Grok Build supports three operational entry points:

1. **Interactive TUI Mode**: A mouse-enabled, keyboard-first terminal session that provides live diff views, multi-choice prompt interactions, and background task monitoring.
2. **Headless Scripting / CI Mode**: Non-interactive command-line execution designed for automated pipelines, pull request reviews, and batch code generation.
3. **Agent Client Protocol (ACP) Embedded Mode**: Native editor integration allowing external Integrated Development Environments (IDEs) to communicate directly with the underlying grok-shell runtime over a structured RPC interface.

#### Plan Mode, Subagents, and Interoperability

To prevent destructive codebase mutations, Grok Build implements an explicit Plan Mode. When active, all file modifications are intercepted and blocked by the workspace controller. The agent generates a structured execution plan, allowing human operators to critique individual steps, modify proposed diffs, or reject architectural choices prior to execution.

For high-complexity tasks, Grok Build spawns specialized subagents. Each subagent executes within an isolated Git worktree and maintains its own dedicated context window. This design allows parallel exploration, automated testing, and isolated research without dirtying the primary working directory.

Furthermore, Grok Build bridges directly into rival agent ecosystems via plugins such as grok-build-plugin-cc. This marketplace plugin allows Claude Code to delegate code reviews, design critiques, and rescue tasks directly to the grok CLI. Process state and execution ownership are strictly maintained via explicit Process ID (PID) tracking and Compare-And-Swap (CAS) state locks to eliminate race conditions during session cancellation.

### 2. SAFe Agentic Workflow (SAW)

The SAFe Agentic Workflow (SAW), developed by bybren-llc, represents an enterprise-grade multi-agent governance harness. SAW adapts the Scaled Agile Framework (SAFe) methodology and fuses it with AWS's AI-Driven Development Life Cycle (AI-DLC) to establish strict operational boundaries for autonomous agent teams.

#### Three-Layer Harness Architecture

SAW organizes system controls into three distinct governance layers that enforce compliance across automated and user-driven workflows:

- **Layer 1: Hooks (Automatic Guardrails)**: Intercepts raw operations to enforce mandatory compliance checks, syntax validation, and permission verification before tool invocation occurs.
- **Layer 2: Commands (User-Invoked Workflows)**: Manages structured slash commands such as /start-work and /pre-pr that trigger standardized multi-step operational sequences across the codebase.
- **Layer 3: Skills (Model-Invoked Expertise)**: Dynamic capabilities auto-loaded by agents based on task frontmatter annotations, adhering to the Open Knowledge Format (OKF v0.1).

#### Role Mapping and Governance Cadence

SAW enforces strict segregation of duties by instantiating 11 specialized agent profiles. Key roles include the Business Systems Analyst (BSA), System Architect, Scrum Master / Team Delivery Manager (TDM), Release Train Engineer (RTE), Data Provisioning Engineer (DPE), Quality Assurance Specialist (QAS), and Security Engineer (SecEng). Human operators retain exclusive control over the Product Owner / Product Manager (POPM) role, holding final approval authority for business requirements, secret configurations, and release sign-offs.

Traditional multi-week Scrum sprints are replaced by “Bolts”—rapid, evidence-driven execution swarms lasting from hours to days. A Bolt progresses through four distinct phases:

1. **Mob Elaboration**: Agents analyze requirements, identify architectural dependencies, and generate clarification questions prior to code generation.
2. **The Loop**: Continuous execution cycles where agents generate code, execute localized tests, and submit evidence artifacts to human validators.
3. **Immutable Quality Gates**: Mandatory, uncollapsible review barriers enforced by dedicated QAS and SecEng subagents.
4. **Evidence-Based Delivery**: Prohibition of unverified assertions; every pull request must attach verifiable build logs, test coverage reports, and security scans.

#### Persistent Autonomous Swarms and Knowledge Vault

For fully autonomous operations, SAW introduces the Dark Factory paradigm. Utilizing background tmux sessions on dedicated infrastructure, dark factory agents execute long-running refactoring tasks and pull request queue resolutions without requiring active terminal connections.

To prevent context drift across multi-agent sessions, SAW utilizes a centralized Knowledge Vault. Built on OKF v0.1, the Knowledge Vault links every architectural design decision and system boundary directly to specific Git commit hashes. Integrated drift validators continuously check model assertions against current repository states, rejecting stale context and preventing hallucinated API integrations.

### 3. Aider

Aider is a widely adopted, open-source, git-native command-line pair programming harness written in Python. Designed to run within local terminal environments, Aider treats the version control repository as the authoritative state engine, enforcing fine-grained commit tracking for all agent-generated modifications.

#### Tree-Sitter and PageRank Repo Map Engine

Aider solves the context-selection problem through an automated structural mapping pipeline known as the Repo Map. Rather than injecting entire files or relying solely on vector similarity search, Aider constructs a concise semantic representation of the workspace through a multi-stage process:

1. **Symbol Extraction**: Uses Tree-sitter AST parsers across 26+ programming languages to extract class signatures, function definitions, and explicit symbol references via language-specific .scm query files.
2. **Tag Caching**: Parsed AST tags are cached in SQLite databases with modification-time (mtime) invalidation, avoiding redundant re-parsing of unchanged files.
3. **Directed Graph Construction**: Builds a directed dependency graph where nodes represent source files and edges represent caller-callee symbol relationships.
4. **Personalized PageRank Ranking**: Runs a graph-ranking algorithm (Personalized PageRank) seeded with the active chat files. This identifies dependent signatures across the broader codebase.
5. **Token-Budget Elision**: Renders the top-ranked code definitions into scope-aware elided views. A binary search fits the rendered map within a configurable token budget (defaulting to 1,000 tokens).

#### Git-Native Transaction Dynamics

Aider strictly couples code edits with Git operations to maintain repository integrity:

- **Atomic Auto-Commits**: Upon applying a file diff, Aider executes automated test scripts (if configured) and constructs an atomic Git commit with a descriptive message.
- **Instant Rollbacks**: If model outputs break syntax or fail verification, invoking /undo triggers an immediate git reset, restoring the working tree to its clean pre-execution baseline.
- **Dual-Model Architect Mode**: Separates high-level reasoning from code generation. A powerful reasoning model acts as the “Architect” to plan modifications, while a faster, diff-compliant model acts as the “Editor” to apply concrete file changes.

### 4. OpenHands (Formerly OpenDevin)

OpenHands is an open-source platform designed for complex software development tasks. It is built around an event-sourced architecture and sandboxed execution container.

#### EventStream Event-Sourcing Pattern

The foundational core of OpenHands is the EventStream—an append-only, immutable event bus that records every step of an agent's lifecycle. The agent itself operates as a pure stateless function, consuming historical event sequences to emit the next discrete Action. Events fall into four primary categories:

- **MessageEvent**: Captures human inputs and system instructions.
- **ActionEvent**: Enforces code modifications, command execution, or browser interactions.
- **ObservationEvent**: Captures raw execution returns, stdout/stderr, exit codes, and DOM snapshots.
- **CondensationEvent**: Marks context window summarization boundaries, allowing historical events to be compressed without altering the underlying raw log.

This event-sourced model enables full replayability, step-level time-travel debugging, and audit logging across enterprise development pipelines.

#### Containerized Docker Runtime Architecture

To safely execute untrusted code, OpenHands decouples the backend logic from execution environments through a client-server Docker architecture. The platform builds custom OH Runtime Images using Docker BuildKit, injecting a lightweight Python runtime client on top of user-provided base environments. Inside the container, an internal FastAPI server (ActionExecutor) exposes dedicated REST endpoints (/run, /write, /edit) to execute actions in isolated Bash shells or Jupyter environments. Resource limits and network proxy controls prevent host process pollution and enforce memory/CPU quotas.

#### Automated Failure Handling Mechanisms

OpenHands includes automated safety checks within the execution loop to manage context growth and prevent runaway execution loops:

| Failure Pattern | Detection Threshold | Interventional Corrective Action |
| --- | --- | --- |
| Context Window Exhaustion | Context token limit reached | Emits CondensationRequest, creating a consolidated snapshot of the event stream |
| Repeating Action-Observation Pairs | 4+ identical action-observation pairs | Halts current loop, forcing the model to re-evaluate its strategy |
| Repeating Action-Error Cycles | 3+ identical error returns | Intercepts tool execution and injects diagnostic prompts into the context |
| Agent Monologue Loop | 3+ consecutive turns without tool calls | Prompts model to re-engage workspace tooling or await operator input |

### 5. Claude Code and the Multi-Agent Ecosystem

Claude Code is Anthropic's agentic command-line interface. It combines a high-capacity context window with dynamic codebase navigation and multi-agent coordination capabilities.

#### Large-Context Navigation Dynamics

Unlike systems reliant strictly on pre-computed embeddings or static graph maps, Claude Code utilizes an autonomous exploration model. Operating over context windows up to 1 million tokens, the agent dynamically executes low-level search tools—such as file reads, regular expressions, and vector-accelerated search (e.g., WarpGrep)—to explore codebases on demand. This approach provides comprehensive context retrieval in large codebases exceeding 100,000 lines of code.

#### Agent Teams and Parallel Orchestration

For large refactoring initiatives, Claude Code utilizes Agent Teams. A primary lead agent decomposes architectural objectives into sub-tasks, spawning parallel sub-agents with individual context windows. These sub-agents coordinate via a shared task ledger, resolving file dependencies, executing localized test suites, and submitting clean diffs back to the primary controller.

#### Marketplace Integration and Plugin Infrastructure

Claude Code includes an extensible marketplace model. Through host environments and hooks (such as SessionStart), external tools integrate directly into its runtime. A key example is the grok-build-plugin-cc extension, which embeds SpaceXAI’s Grok CLI directly into Claude Code sessions. This enables cross-harness delegation, where Claude Code can delegate read-only code reviews, design critiques, or rescue tasks directly to Grok Build, managing execution via background process trees and shared log files.

---

## Structural Comparative Matrix and Quantitative Dynamics

An architectural comparison highlights the trade-offs across design philosophies, state persistence strategies, and sandbox enforcement mechanisms implemented by each major harness.

| Architectural Feature | Grok Build | SAW | Aider | OpenHands | Claude Code |
| --- | --- | --- | --- | --- | --- |
| Primary Language Stack | Rust (99.6%) | Shell / Python / Cross-CLI | Python (3.9–3.13) | Python / TypeScript / Docker | TypeScript / Node.js |
| User Interface / Runtime | Mouse-interactive TUI, headless, ACP | CLI / tmux swarm / cross-harness | Terminal CLI | Web TUI, REST API, headless CLI | Terminal CLI, IDE hooks |
| Sandboxing & Safety Containment | Git worktree isolation, read-only sandbox, CAS PID locks | Layer 1 hooks, stop-the-line authority, POPM gate | File-scope boundary, optional --no-git | Docker containers, BuildKit client-server REST API | Permission approval, process containment |
| Context Retrieval Engine | Dynamic workspace search, file indexing, AGENTS.md | Knowledge Vault (OKF v0.1), link drift validation | Tree-sitter AST, PageRank repo map (~1k tokens) | EventStream history, context condensation events | Autonomous file search, 1M context window |
| State Persistence Model | Checkpointed workspaces, Config.toml, session logs | Git commit-linked vault, tmux sessions | Auto-git commits, SQLite tag caching | Append-only EventLog JSONL files | Session JSONL transcripts, host state roots |
| Multi-Agent Capabilities | Parallel subagents in isolated worktrees | 11 role profiles, Dark Factory swarms | Single-agent focus (Architect/Editor split) | Multi-agent hub, stateless event consumers | Agent teams with dedicated contexts |
| Git Integration Strategy | Diff view, worktrees, branch management | PR gates, merge queue rulesets, commit audits | Atomic auto-commit per edit, /undo via reset | Workspace file mounts, git operations in sandbox | Git-aware, manual/structured commit flow |
| Extension Framework | Skills, plugin marketplace, hooks, MCP servers | 20 frontmatter skills, 24 commands, 3 layers | Scriptable shell commands, custom prompts | Runtime plugins, custom container images | Marketplace plugins, MCP, session hooks |

### Benchmark Snapshot

Standardized benchmarks such as SWE-bench Verified and SWE-bench Pro evaluate autonomous software engineering capabilities across complex repositories. Performance scores reflect the combined efficiency of the underlying model and the harness context selection engine.

| Agent Engine / Harness Stack | Benchmark Evaluation Suite | Resolve Rate (%) | Average Cost / Resolved Issue | Dominant Architectural Driver |
| --- | --- | ---: | --- | --- |
| Claude 4.5 Opus (High Reasoning) | SWE-bench Verified | 76.80% | ~$0.75 | 1M context window, autonomous exploration |
| Gemini 3 Flash (High Reasoning) | SWE-bench Verified | 75.80% | ~$0.36 | High token throughput, low latency iteration |
| mini-SWE-agent (Minimalist Harness) | SWE-bench Verified | 74.00% | Configurable | Lightweight prompt loop, zero abstraction overhead |
| WarpGrep + Claude Code Engine | SWE-bench Pro | 57.50% | Variable | Vector-accelerated MCP search tooling |

Analyzing these benchmark outcomes reveals a fundamental architectural trade-off between lightweight flat-list harnesses and fully isolated heavyweight runtimes. Flat-list systems like mini-SWE-agent and Aider minimize execution latency and token overhead by passing direct command streams to the LLM. This results in cost-effective execution for localized bug fixes.

However, they lack the environment isolation necessary for safe autonomous execution. Conversely, containerized and event-sourced systems like OpenHands and SAW introduce higher startup overhead and system complexity, but provide the security containment, step-level auditability, and failure recovery required for enterprise deployments.

---

## Sub-System Mechanics and Architectural Optimizations

### Context Window Optimization Strategies

Efficient context window management is critical to prevent attentional degradation in large codebases. Harnesses utilize three primary strategies:

1. **Graph-Based Structural Compression (Aider)**: Employs language-aware AST parsing to construct directed dependency graphs. By processing this graph through Personalized PageRank, the harness compresses thousands of files into a compact, symbol-dense map of signatures. This provides the model with global structural awareness while consuming minimal context tokens.
2. **Event-Sourced Log Condensation (OpenHands)**: Treats conversation history as an append-only event stream. When history approaches model context limits, a special condensation event summarizes older interaction blocks. The raw underlying events remain preserved on disk for auditing, while the active LLM context is reduced to a concise state snapshot.
3. **Commit-Anchored Verification (SAW)**: Uses the Open Knowledge Format (OKF v0.1) to bind contextual assertions directly to Git commit hashes. If an agent references a function definition, the harness verifies whether the target file has mutated since the context was recorded. If drift is detected, the context is invalidated and re-parsed, eliminating hallucinations caused by stale data.

### Sandboxing, Execution Safety, and Tool Dispatching

Running autonomous agent loops safely requires containment mechanisms to protect host system integrity across different operational levels:

- **Container-Level API Isolation (OpenHands)**: Runs all user commands within dedicated Docker containers. Communication between the host and container occurs over an HTTP REST API managed by an internal FastAPI server (ActionExecutor). This ensures that destructive shell commands such as rm -rf or runaway processes remain contained within the sandbox environment.
- **Plan-Mode Enforcement and Process Locking (Grok Build)**: Intercepts tool calls at the runtime layer. In Plan Mode, write operations to the workspace filesystem are blocked until the user approves the execution plan. For process control, Grok Build uses atomic Compare-And-Swap (CAS) state locks. When a cancellation signal (/grok-build:stop) is emitted, the harness terminates the child agent process tree before clearing the state, preventing race conditions where background processes complete after cancellation.
- **Layered Guardrails and Stop-the-Line Authority (SAW)**: Implements mandatory pre-execution hooks that enforce security policies and block restricted system calls. SAW empowers any subagent with Stop-the-Line Authority, allowing execution to be halted immediately if an architectural violation or security risk is detected.

### Multi-Agent Orchestration and Cross-Harness Interoperability

As software projects grow in scale, single-agent architectures are replaced by coordinated multi-agent systems that utilize diverse inter-process communication techniques:

- **Dark Factory Persistence**: SAW orchestrates autonomous swarms using background tmux sessions. Agents assume specialized roles such as BSA, Architect, and QAS and communicate asynchronously through shared issue tracking items and Git pull requests.
- **Isolated Worktree Delegation**: Grok Build spawns subagents within independent Git worktrees. This design allows parallel code generation and testing without lock contention or dirty working directories in the main repository.
- **Inter-Harness RPC Bridging**: Harnesses can interoperate through lightweight bridges, such as grok-build-plugin-cc. This plugin allows Claude Code to invoke Grok Build via command-line flags. The bridge tracks process identifiers, formats stdout/stderr responses, and passes session transcripts between tools.

---

## Strategic Outlook and Engineering Synthesis

The engineering landscape for AI agent harnesses is transitioning from basic command wrappers toward deterministic, event-sourced execution environments. The primary driver of this evolution is the necessity to maintain safety, predictability, and efficiency as foundation models take on greater autonomy over software codebases.

Key trajectory vectors shaping the future of AI harness development include:

- **Standardization Around Inter-Process Protocols**: Proprietary tool interfaces are giving way to standardized protocols like the Model Context Protocol (MCP) for tool discovery and the Agent Client Protocol (ACP) for editor integrations. This standardization allows heterogeneous agent harnesses to interoperate seamlessly across IDEs, terminals, and cloud environments.
- **Event-Sourced Traceability**: Systems like OpenHands demonstrate that recording immutable event logs (EventStream) is critical for enterprise auditing, debugging, and time-travel replay. Future enterprise harnesses will adopt event sourcing as a standard to satisfy compliance and security requirements.
- **Formalization of Multi-Agent Governance**: Enterprise methodologies like SAW show that running autonomous agent swarms requires formal guardrails, clear separation of duties, commit-anchored knowledge bases, and explicit quality gates. Fusing agile governance frameworks with autonomous execution loops ensures that AI swarms operate within defined architectural boundaries.
- **Hybrid Execution Topologies**: Agent harnesses are increasingly decoupling high-level planning from localized code execution. High-reasoning models perform architectural planning and critique, while localized, open-weight models handle precise code edits and formatting within isolated sandboxes.

Ultimately, selecting an AI agent harness depends on operational requirements. Lightweight tools like Aider offer fast, git-native pair programming for local development. Systems like Grok Build deliver high-performance terminal UI experiences with fine-grained plan controls and subagent parallelization. For enterprise organizations requiring strict compliance, sandboxed execution, and multi-agent coordination, event-sourced and methodology-driven frameworks like OpenHands and SAW provide the isolation, traceability, and governance required for scalable autonomous development.

---

## References

1. xai-org/grok-build: SpaceXAI's coding agent harness and TUI. Fullscreen, mouse interactive, extensible. GitHub: https://github.com/xai-org/grok-build
2. Grok Build — SpaceXAI: https://x.ai/cli
3. GitHub — xai-org/grok-build-plugin-cc: Claude Code plugin that delegates reviews, rescue tasks, and session transfer to the Grok Build CLI: https://github.com/xai-org/grok-build-plugin-cc
4. Issues · xai-org/grok-build-plugin-cc — GitHub: https://github.com/xai-org/grok-build-plugin-cc/issues
5. scaled-agile-framework · GitHub Topics: https://github.com/topics/scaled-agile-framework?l=shell
6. bybren-llc/safe-agentic-workflow: SAW — GitHub: https://github.com/bybren-llc/safe-agentic-workflow
7. How to Use Aider: Atomic Git Commits & Architect Mode (2026 Guide) — DeployHQ: https://www.deployhq.com/guides/aider
8. Aider Tutorial 2026: Complete Setup Guide for the Open-Source AI Coding CLI — NxCode: https://www.nxcode.io/resources/news/aider-complete-tutorial-guide-install-setup-2026
9. Repository map — Aider: https://aider.chat/docs/repomap.html
10. Feature: PageRank Repo Map — Automatic Codebase Context Selection via Symbol Graph (inspired by Aider) · Issue #535 · NousResearch/hermes-agent — GitHub: https://github.com/NousResearch/hermes-agent/issues/535
11. OpenDevin: An Open Platform for AI Software Developers as Generalist Agents — ResearchGate: https://www.researchgate.net/publication/382527281_OpenDevin_An_Open_Platform_for_AI_Software_Developers_as_Generalist_Agents
12. Runtime Architecture — OpenHands Docs: https://docs.openhands.dev/openhands/usage/architecture/runtime
13. OpenHands — Deep Dive & Build-Your-Own Guide — DEV Community: https://dev.to/truongpx396/openhands-deep-dive-build-your-own-guide-1al0
14. Inside the Scaffold: A Source-Code Taxonomy of Coding Agent Architectures — arXiv: https://arxiv.org/html/2604.03515v2
15. Memo of OpenHands Understanding — Zenn: https://zenn.dev/giba/scraps/9cf5e632241d69
16. Aider vs Claude Code (2026): $0 With Any LLM vs $20/mo Locked to Anthropic — MorphLLM: https://www.morphllm.com/comparisons/aider-vs-claude-code
17. xai-org/plugin-marketplace — GitHub: https://github.com/xai-org/plugin-marketplace
18. hooks · GitHub Topics: https://github.com/topics/hooks?l=shell
19. Grok Build is Now Open Source — SpaceXAI: https://x.ai/news/grok-build-open-source
20. SWE-bench Leaderboards: https://www.swebench.com/
21. SWE-Bench Pro Leaderboard AI Coding Benchmark (Public Dataset) — Scale Labs: https://labs.scale.com/leaderboard/swe_bench_pro_public
22. Inside the Scaffold: A Source-Code Taxonomy of Coding Agent Architectures — ResearchGate: https://www.researchgate.net/publication/403562308_Inside_the_Scaffold_A_Source-Code_Taxonomy_of_Coding_Agent_Architectures
23. GitHub — ai-boost/awesome-harness-engineering: Awesome list for AI agent harness engineering: tools, patterns, evals, memory, MCP, permissions, observability, and orchestration.: https://github.com/ai-boost/awesome-harness-engineering

---

# Part II — Primary-Source Codebase Investigation

> The following chapters were produced by exhaustive source-code reading of four
> reference harness codebases included in the Harness monorepo at `src/`. Every
> claim below is traced to actual file paths, data structures, and control-flow
> patterns observed directly in the implementation. The codebases analyzed are:
>
> | Project | Language | Source Files | Path |
> | --- | --- | ---: | --- |
> | Claude Code (Anthropic) | TypeScript | ~1,915 | `src/claude_code/` |
> | Grok Build (xAI) | Rust | ~2,325 `.rs` | `src/grok_build/` |
> | Hermes Agent (Nous Research) | Python | ~3,634 `.py` | `src/hermes_agent/` |
> | OpenCode | Go | ~137 `.go` | `src/open_code/` |

---

## 6. Source-Level Architecture Analysis

### 6.1 Claude Code — TypeScript Service-Layer Architecture

Claude Code is structured as a TypeScript monolith with React (Ink) terminal rendering and a centralized `QueryEngine` orchestrator. The codebase is organized under `src/claude_code/src/` with the following primary modules:

**Entry-point chain:** `cli.js` → `src/entrypoints/cli.tsx` (Commander-based argument parsing, dispatching to daemon, MCP, or interactive modes) → `src/main.tsx` (React root component, initializes `AppStateStore`).

**Core orchestration files:**

| File | Size | Responsibility |
| --- | --- | --- |
| `src/QueryEngine.ts` | ~1,700 lines | LLM call assembly, response handling, token accounting |
| `src/query.ts` | Large | Async generator `queryLoop` — the agent execution cycle |
| `src/context.ts` | Medium | System and user context construction (`SystemContext`, `UserContext`) |
| `src/tools.ts` | Medium | Centralized tool registry using `buildTool()` |
| `src/Tool.ts` | Medium | Tool interface definition with `zod` schema validation |
| `src/history.ts` | Medium | Message history and conversation management |

**Build system:** Custom `build.mjs` wrapping esbuild for single-file bundle output. Configuration via `tsconfig.json` with strict mode. Dependencies managed through `package.json` with `@anthropic-ai/sdk`, AWS Bedrock SDK, GCP Vertex SDK, `@modelcontextprotocol/sdk`, `zod`, `chokidar`, and `commander`.

**Module topology:** The architecture is flat — there is no explicit layering enforcement. Any module can import any other module. The `bridge/` subsystem (24 files) handles remote sessions, JWT authentication, and transport for cloud-hosted operation. The `buddy/` directory contains an experimental companion sprite feature implemented as React components.

### 6.2 Grok Build — Rust Workspace with IPC Decoupling

Grok Build is organized as a Cargo workspace containing approximately 63 crates under `crates/codegen/`, `crates/common/`, and `crates/build/`. The workspace manifest at `Cargo.toml` defines all crate dependencies and shared configuration.

**Primary crate categories and their implementations:**

| Crate | Responsibility | Key Implementation Detail |
| --- | --- | --- |
| `xai-grok-pager-bin` | Composition root, final binary | Compiles to the `xai-grok-pager` executable |
| `xai-grok-pager` | Full-screen TUI | Ratatui rendering, scrollback buffers, prompt modals |
| `xai-grok-shell` | Agent runtime and leader election | Houses `MvpAgent`, `acp_session`, goal actors |
| `xai-grok-tools` | Tool implementations | Multiple edit strategies, terminal, search |
| `xai-grok-workspace` | Filesystem and VCS interaction | Worktree management, checkpoint persistence |
| `xai-chat-state` | Conversation state | `ChatStateSnapshot`, `ConversationItem`, `PruningConfig` |
| `xai-codebase-graph` | Code intelligence | Tree-sitter AST, `IndexManager`, scope graphs |
| `xai-acp-lib` | Agent Client Protocol | IPC between TUI and agent core |
| `xai-grok-sampler` | LLM API abstraction | Forked `async-openai` for streaming completions |
| `xai-grok-models` | Model management | Model prefetching and configuration |
| `xai-grok-mcp` | MCP integration | `McpState` session management |
| `xai-grok-sandbox` | Sandboxed execution | Policy enforcement and containment |
| `xai-sqlite-journal` | Persistent storage | SQLite with NFS detection and WAL/Truncate fallback |
| `xai-agent-lifecycle` | Lifecycle management | `ExtensionRegistry` for hooks (`TurnStart`/`TurnDone`/`TurnAbort`) |
| `xai-grok-subagent-resolution` | Sub-agent coordination | Spawning and tracking sub-agents |
| `xai-fast-worktree` | File traversal | Rapid gitignore-aware directory walking |
| `xai-hunk-tracker` | Edit tracking | Hunk-level undo/redo and conflict detection |
| `xai-grok-config` | Configuration | Runtime configuration management |
| `ptyctl` / `ptyctl-cli` | Terminal control | PTY multiplexing for background terminals |
| `xai-ratatui-textarea` | Custom widget | Multi-line text area for the TUI |
| `xai-grok-test-support` | Testing infrastructure | Hermetic test utilities |

**Strict IPC separation:** The TUI layer (`xai-grok-pager`) communicates with the agent core (`xai-grok-shell`) exclusively through the Agent Client Protocol (`xai-acp-lib`). `SessionCommand` messages enter the agent; `SessionNotification` events return to the TUI. This boundary is a Rust crate dependency — the TUI crate cannot directly call agent runtime functions.

**Concurrency model:** All hot-path async work uses Tokio channels. The `IndexManager` in `xai-codebase-graph` processes file events strictly via channel-based message passing — no `Arc<Mutex>` contention patterns were found in indexing code paths. File system events from FSNotify are debounced before processing, and files exceeding 5MB are explicitly skipped to prevent out-of-memory conditions.

**Toolchain:** Rust stable via `rust-toolchain.toml`, formatting via `rustfmt.toml`, linting via `clippy.toml` with specific allow/deny rules.

### 6.3 Hermes Agent — Python Semi-Monolithic Architecture

Hermes Agent is characterized by extremely large single-file modules that concentrate core logic:

| File | Size | Line Estimate | Responsibility |
| --- | --- | --- | --- |
| `cli.py` | 833 KB | ~20,000+ lines | Complete TUI/CLI using `prompt_toolkit` |
| `hermes_state.py` | 359 KB | ~9,000+ lines | SQLite-WAL state management |
| `run_agent.py` | 337 KB | ~8,000+ lines | `AIAgent` class, core execution loop |
| `hermes_state_search.py` | 87 KB | ~2,200+ lines | FTS5 full-text search across sessions |
| `trajectory_compressor.py` | 70 KB | ~1,700+ lines | Conversation history compression |
| `model_tools.py` | 66 KB | ~1,600+ lines | Tool definitions and `handle_function_call()` dispatch |
| `hermes_constants.py` | 47 KB | ~1,200+ lines | Central constants and configuration values |
| `toolsets.py` | 35 KB | ~900+ lines | Tool registration and environment-based filtering |
| `mcp_serve.py` | 34 KB | ~850+ lines | MCP server implementation |
| `hermes_logging.py` | 31 KB | ~800+ lines | Logging infrastructure |

**Supporting directories and their functions:**

| Directory | Contents | Notes |
| --- | --- | --- |
| `agent/` | Core agent logic, prompt builder | Modularized agent behavior |
| `tools/` | Tool implementations, `approval.py` | Security guardrails and tool execution |
| `skills/` | Agent-generated procedural skills | Self-improving skill persistence |
| `providers/` | LLM provider adapters | OpenAI, Anthropic, OpenRouter, Nous Portal |
| `plugins/` | Plugin system | Runtime extensibility |
| `gateway/` | Messaging integrations | Discord, Telegram, Slack bots |
| `apps/` | Application-level code | Multi-app deployment |
| `web/` / `website/` | Web interfaces | Browser-based access |
| `hermes_cli/` | CLI tooling | Command-line utilities |
| `tui_gateway/` / `ui-tui/` | TUI interfaces | Terminal UI components |
| `native/` | Native code extensions | Performance-critical paths |
| `scripts/` | Utility scripts | Setup and maintenance |
| `docker/` | Containerization | Docker and docker-compose configs |
| `optional-skills/` | Pre-built skill packs | Bundled optional capabilities |
| `optional-mcps/` | Pre-configured MCP servers | External tool integrations |

**Package management:** `pyproject.toml` with `uv` as package manager. Python 3.11–3.13 compatibility. Dependencies include `openai` (as a universal API proxy), `prompt_toolkit`, `fastapi`, `anyio`, `psutil`, and `sqlite3`.

### 6.4 OpenCode — Go Clean Architecture

OpenCode follows Go's `internal/` package convention, providing compiler-enforced encapsulation:

```
src/open_code/
├── main.go                    # Entry point
├── cmd/                       # cobra CLI commands
├── internal/
│   ├── app/                   # Application core, service wiring
│   ├── llm/
│   │   ├── agent/             # Agent loop, sub-agents, MCP tools
│   │   ├── models/            # Model definitions
│   │   ├── prompt/            # Prompt construction (coder.go)
│   │   ├── provider/          # Multi-provider abstraction
│   │   └── tools/             # Tool implementations + shell/
│   ├── db/                    # SQLite + goose migrations + sqlc
│   │   ├── migrations/        # Schema migrations
│   │   └── sql/               # Query definitions → code-generated Go
│   ├── tui/                   # Bubble Tea terminal UI
│   │   └── components/        # Chat, diff views, modals
│   ├── session/               # Session lifecycle
│   ├── message/               # Message handling
│   ├── history/               # Conversation history assembly
│   ├── permission/            # Permission system
│   ├── diff/                  # Unified diff (go-udiff, go-diff)
│   ├── lsp/                   # LSP client (protocol, util, watcher)
│   ├── pubsub/                # Event broker
│   ├── completions/           # Completion handling
│   ├── fileutil/              # File utilities
│   ├── format/                # Output formatting
│   ├── logging/               # Logging
│   └── config/                # Configuration parsing
├── go.mod                     # Go 1.24.0
├── sqlc.yaml                  # SQL code generation config
├── .opencode.json             # Project configuration
└── opencode-schema.json       # JSON Schema for config (IDE autocompletion)
```

**Key dependencies from `go.mod`:** `charmbracelet/bubbletea` (TUI), `mattn/go-sqlite3` and `pressly/goose` (persistence), `sqlc` (type-safe SQL code generation), `spf13/cobra` (CLI), `openai/openai-go`, `anthropics/anthropic-sdk-go`, `mark3labs/mcp-go` (MCP client).

**Code generation pipeline:** SQL queries are defined in `internal/db/sql/*.sql` files. `sqlc` reads `sqlc.yaml` and generates type-safe Go structs and functions, eliminating hand-written SQL parsing. Database migrations are managed by `goose` in `internal/db/migrations/`.

---

## 7. Execution Loop Implementations

### 7.1 Claude Code — Async Generator Loop

The core execution loop is implemented as an async generator function in `src/query.ts`:

```typescript
export async function* query(): AsyncGenerator<StreamEvent | Message>
```

This delegates to `queryLoop()`, which maintains a continuous cycle:

1. **Assemble context**: `context.ts` constructs `SystemContext` (git branch, status snapshot) and `UserContext` (reads `CLAUDE.md` files from project root and subdirectories).
2. **Call LLM**: Streaming request via the configured provider (Anthropic, Bedrock, or Vertex). Results are yielded as `StreamEvent` objects for real-time UI rendering.
3. **Check `stop_reason`**:
   - `tool_use` → execute requested tools, append results, re-call LLM.
   - `end_turn` → yield final response, terminate loop.
   - `max_tokens` → auto-extend by continuing the conversation.
4. **Error handling**: Tool execution errors are caught and returned as structured error results to the LLM, enabling self-correction without loop termination.

Multiple tool calls within a single LLM response are batched — all tools execute, all results are collected, and the batch is appended before the next LLM call.

**Token management**: `QueryEngine.ts` manages the context window dynamically. When conversation history approaches limits, `src/services/compact/autoCompact.ts` triggers a summarization pass that collapses older messages into a condensed summary, preserving recent context.

### 7.2 Grok Build — Actor-Based Session Loop

The agent loop is distributed across two components:

**`MvpAgent`** (`xai-grok-shell/src/agent/mvp_agent/`): High-level agent behavior, coordinating with the goal system and sub-agent coordinator.

**`acp_session`** (`xai-grok-shell/src/session/acp_session.rs`): The session actor that manages individual turns:

1. **Receive `SessionCommand`**: Arrives via ACP channel from the TUI.
2. **Enrich context**: `prompt_context.render()` constructs the full prompt, injecting environmental context. Context blocks are delimited with canonical `<memory-context>` tags to prevent silent deduplication of identical content from different sources.
3. **Call LLM**: `xai-grok-sampler` wraps the API call using the forked `async-openai` crate.
4. **Evaluate tool calls**: Tools execute through `ToolBridge`, which differentiates between local tools (run in-process) and `HostedTool`s (forwarded to backend server).
5. **Loop or return**: Tool results are appended and the cycle repeats; non-tool responses generate a `SessionNotification` event returned via ACP.

**Lifecycle hooks**: `xai-agent-lifecycle` dispatches `TurnStart`, `TurnDone`, and `TurnAbort` events through the `ExtensionRegistry`. These are zero-ownership hooks — extensions observe but cannot steal the dispatch control loop. This is enforced by the Rust type system: hook functions receive immutable references.

**Goal decomposition actors** (within `xai-grok-shell/src/session/`):

| Actor | Role |
| --- | --- |
| `goal_orchestrator.rs` | Top-level goal management and coordination |
| `goal_planner.rs` | Decomposes goals into executable steps |
| `goal_tracker.rs` | Tracks progress, completion state, dependencies |
| `goal_strategist.rs` | Selects execution strategies per goal |

These actors communicate via Tokio channels, forming a structured planning pipeline that operates independently of the main agent loop.

### 7.3 Hermes Agent — Budget-Bounded Conversation Loop

The core loop resides in `run_agent.py` within the `AIAgent` class:

1. **Client initialization**: `_create_openai_client()` resolves the workspace and creates an OpenAI-compatible LLM client for the selected provider.
2. **Context assembly**: `agent.prompt_builder` constructs the system prompt, loading `DEFAULT_AGENT_IDENTITY`, active skills from `skills/`, and explicit context files. Input is sanitized: `_sanitize_surrogates()` scrubs Unicode surrogates, images are stripped for text-only models, and `estimate_request_tokens_rough()` validates the assembled input fits within the model's context window.
3. **Bounded loop**: `run_conversation()` iterates under an `IterationBudget` — a hard cap on turns that prevents runaway execution regardless of the LLM's behavior.
4. **Tool dispatch**: On tool-calling responses, `handle_function_call()` in `model_tools.py` dynamically maps the function name to a Python tool implementation and executes it. Before execution, `ToolGuardrailDecision` from `tools/approval.py` checks security policies.
5. **Result feedback**: Tool outputs are appended to the conversation trajectory and the loop continues.
6. **Termination**: Loop exits when the LLM produces a non-tool response, the iteration budget is exhausted, or a fatal error occurs.

**Trajectory compression** (`trajectory_compressor.py`): When the conversation history exceeds token limits, the compressor applies a targeted strategy:
- The first N turns are **protected** (never compressed) — these contain the task definition and initial context.
- The last N turns are **protected** — these contain the most recent work.
- The middle turns are replaced with a **generated summary** produced by a fast, cheap model (typically via OpenRouter). This preserves both initial context and recent state while dramatically compressing the potentially enormous middle.

### 7.4 OpenCode — Goroutine-Based Event Stream

The agent loop in `internal/llm/agent/agent.go` uses Go's concurrency primitives:

1. **`Run()` method**: Spawns a goroutine via `processGeneration` for non-blocking execution.
2. **History fetch**: Retrieves recent messages from SQLite (associated by `session_id`).
3. **Prompt construction**: `internal/llm/prompt/coder.go` builds a provider-specific system prompt, dynamically injecting:
   - Environment information (working directory, git status, OS, date)
   - Quick `ls` output for current directory awareness
   - LSP instructions (when enabled)
   - Reference to `OpenCode.md` / `.cursorrules` / `CLAUDE.md` for project conventions
4. **Event stream**: The provider returns a `<-chan AgentEvent` channel. The agent consumes events as they arrive — streaming tokens, tool invocations, and completion signals.
5. **Tool execution**: When the model invokes tools, the agent executes them, appends results to history, and re-enters the stream loop.
6. **Auto-compaction**: When context length hits **95% of the model's context window**, a `SummarizeAgent` automatically compresses the conversation into a summary and spawns a fresh session to prevent overflow.

**Specialized sub-agents:**

| Agent | Role | Available Tools |
| --- | --- | --- |
| `CoderAgent` | Primary agent | All tools including `agent` delegation |
| `TaskAgent` | Research sub-agent | Read-only: `glob`, `grep`, `ls` |
| `TitleAgent` | Session naming | Auto-generates session titles |
| `SummarizeAgent` | Context compression | Summarizes conversations for compaction |

The `TaskAgent` is invoked via the `agent` tool in `internal/llm/agent/agent-tool.go`. It receives only read-only tools — it can search the codebase but cannot modify files. This keeps the main agent's context window small by offloading heavy search tasks.

---

## 8. Memory Subsystem Mechanics

### 8.1 Short-Term Memory Implementations

| Project | Mechanism | Backing Store | Compaction Strategy |
| --- | --- | --- | --- |
| **Claude Code** | In-memory message array in `history.ts` | Session files at `~/.claude/sessions/` | `autoCompact.ts`: dynamic summarization of old messages |
| **Grok Build** | `ChatStateSnapshot` with `ConversationItem` list | SQLite via `xai-sqlite-journal` | `PruningConfig`: soft-trim (truncate large outputs) or hard-clear (remove old items) |
| **Hermes Agent** | Conversation trajectory list in `AIAgent` | SQLite-WAL via `hermes_state.py` | `trajectory_compressor.py`: first-N/last-N protection with middle summary |
| **OpenCode** | Database-backed messages via `internal/message/` | SQLite via `internal/db/` with `sqlc` | `SummarizeAgent` triggered at 95% context capacity |

**Token tracking granularity:**

- **Claude Code**: Built-in estimation in `QueryEngine.ts`, used to trigger auto-compaction.
- **Grok Build**: Per-item token estimates in `ChatStateSnapshot` — enables precise budget management. `PruningConfig` supports configurable thresholds for when to trim.
- **Hermes Agent**: `estimate_request_tokens_rough()` performs pre-call validation. The compressor uses a separate fast model to generate summaries cost-effectively.
- **OpenCode**: Token usage and cost tracked **per session** in SQLite, enabling cost monitoring and budget enforcement across sessions.

### 8.2 Long-Term Memory and Persistence

**Claude Code** uses entirely file-based persistence:
- Session transcripts written to `~/.claude/sessions/`
- Task board files in `.claude/` (project directory) with file-system locks (`lockfile.ts`) for multi-agent coordination
- `CLAUDE.md` files at project root and subdirectories serve as persistent per-project instructions, read on every session start and included in the system prompt
- No database, no embeddings, no structured query capability over history

**Grok Build** uses SQLite with production-grade resilience:
- `xai-sqlite-journal` detects if the database file resides on an NFS mount (common in clustered development environments)
- On NFS, automatically degrades from WAL (Write-Ahead Logging) to Truncate rollback journal mode
- This prevents `SIGBUS` panics caused by peer NFS clients truncating the WAL file — a known SQLite failure mode on network filesystems
- Stores session state, checkpoints, and workspace metadata

**Hermes Agent** uses SQLite-WAL with FTS5 full-text search:
- `hermes_state.py` manages all persistent state via SQLite in WAL mode for multi-process safety
- `hermes_state_search.py` implements FTS5 full-text search across all historical interactions — not just the current session
- Enables session resumption based on git repository root or current working directory
- Uses `_delegate_from` tags to track hierarchical parent-child sub-agent session relationships
- **Procedural skills**: Successful task patterns are generated as reusable skills and persisted in `skills/`, loaded into future session contexts — creating an inference-time reinforcement learning loop

**OpenCode** uses SQLite with `sqlc` code generation:
- Database schema defined in `internal/db/migrations/` (managed by `goose`)
- SQL queries in `internal/db/sql/*.sql` → `sqlc` generates type-safe Go structs
- Tables: `sessions` (metadata), `messages` (full conversation), `files` (version tracking for rollback and diff visualization)
- Token usage and cost tracked per session

### 8.3 Code Intelligence and Indexing

**Claude Code — LSP Delegation (no custom parsing):**
`src/tools/LSPTool/LSPTool.ts` exposes standard Language Server Protocol methods as tools available to the LLM:
- `workspace/symbol` — find symbols across the workspace
- `textDocument/definition` — go to definition
- `textDocument/references` — find all references
- `textDocument/hover` — get type information

The LLM invokes these like any other tool. This means Claude Code leverages the same code intelligence that IDEs use (TypeScript language server, Pyright, gopls) without implementing any language-specific parsing. The harness adds zero maintenance burden for new language support — any language with an LSP server is automatically supported.

**Grok Build — Tree-Sitter Scope Graphs (deep custom indexing):**
`xai-codebase-graph` provides the most sophisticated code intelligence of any investigated project:
- Tree-sitter AST parsing with per-language grammar modules in `src/languages/`
- Scope graph construction in `src/scope_graph/` for symbol resolution — understanding where symbols are defined, referenced, and how scopes nest
- `IndexManager` (`index_manager.rs`) handles incremental file events **strictly via channels** — no `Arc<Mutex>` contention. File events from FSNotify are debounced.
- Files exceeding 5MB are explicitly skipped to prevent out-of-memory conditions
- Used for impact closure (partitioning parallel work), neighbor expansion during retrieval, and blast-radius estimation

**Hermes Agent — No Native Code Intelligence:**
Hermes relies entirely on runtime tool probing:
- No tree-sitter, no AST parsing, no LSP integration
- Code analysis happens on-demand via terminal tools (`ripgrep`, `find`, file reading)
- Session-level FTS5 search provides textual pattern matching across historical interactions
- This is adequate for many tasks but limits structural code understanding

**OpenCode — LSP Diagnostics Injection:**
`internal/lsp/` implements an LSP client that intercepts language server diagnostics:
- Connects to language servers (`gopls`, `typescript-language-server`, etc.) via stdio
- Intercepts diagnostics (type errors, lint warnings, compilation issues)
- Feeds them directly into the LLM context within `<file_diagnostics>` tags when tools are executed
- The agent automatically sees compiler feedback without explicit querying
- `internal/lsp/watcher/` monitors file changes to trigger diagnostic updates

---

## 9. Tool System Design Patterns

### 9.1 Tool Registration and Schema Validation

**Claude Code** — `buildTool()` in `src/Tool.ts`:
```typescript
// Conceptual interface
interface Tool {
  name: string;
  description: string;
  inputSchema: ZodSchema;      // zod-validated input
  checkPermissions(): boolean;  // capability-based authorization
  execute(input): Promise<ToolResult>;
}
```
Tools are registered centrally in `src/tools.ts`. Every tool input is validated against a `zod` schema before execution, catching malformed inputs at the dispatch boundary.

**Grok Build** — `ToolDefinition` + `ToolBridge`:
Tools register with a typed `ToolDefinition` (name, description, parameter schema). The `ToolBridge` handles dispatch and differentiates between:
- **Local tools**: Terminal execution, file editing — run in-process on the client machine
- **`HostedTool`s**: Forwarded to the backend server/sampler for execution — enabling server-side capabilities without client-side dependencies

**Hermes Agent** — Dynamic toolsets in `toolsets.py`:
Tools are defined dynamically and filtered by the active toolset. `sandbox_enabled` controls which tools are available in sandboxed environments. `toolset_distributions.py` allows different tool configurations for different deployment contexts (local dev vs. cloud vs. messaging bot). `handle_function_call()` in `model_tools.py` dynamically maps function names to implementations.

**OpenCode** — `BaseTool` interface:
```go
type BaseTool interface {
    Info() ToolInfo      // Returns JSON schema of arguments
    Run(ctx, args) Result // Executes the tool
}
```
Tools are registered and passed to the LLM. MCP tools from external servers register through the same interface via `internal/llm/agent/mcp-tools.go`.

### 9.2 File Editing Strategies

| Project | Strategy | Validation | Rollback |
| --- | --- | --- | --- |
| **Claude Code** | Literal `old_string` → `new_string` replacement in `FileEditTool.ts` | None — exact match required | Git (manual) |
| **Grok Build** | **Five pluggable strategies**: `codex`, `opencode`, `grok_build`, `grok_build_concise`, `grok_build_hashline` in `xai-grok-tools/src/implementations/` | Hunk tracking via `xai-hunk-tracker` | Hunk-level undo/redo |
| **Hermes Agent** | Terminal-based diffs and replacements via `tools/` | `ToolGuardrailDecision` security check | Git |
| **OpenCode** | Unified diff via `go-udiff` and `go-diff` in `internal/diff/` | Diff validation | File version tracking in SQLite `files` table |

Grok Build's approach of maintaining five pluggable edit implementations is unique. It suggests active experimentation to find the optimal edit strategy — each implementation can be tested against benchmark tasks and the best selected per context. The `xai-hunk-tracker` provides granular hunk-level tracking for precise undo/redo, superior to whole-file rollback.

### 9.3 Command Execution Patterns

| Project | Execution Model | Safety |
| --- | --- | --- |
| **Claude Code** | `BashTool` — shell string execution | `yoloClassifier.ts` heuristic/LLM classification |
| **Grok Build** | Terminal tool via `xai-grok-tools` | `xai-grok-sandbox` containment + `folder_trust.rs` |
| **Hermes Agent** | `ptyprocess` (Unix) / `winpty` (Windows) for full PTY support | `approval.py` regex guardrails + `ToolGuardrailDecision` |
| **OpenCode** | `bash` tool in `internal/llm/tools/shell/` | Permission system with Allow/Deny/Session modals |

Hermes Agent's use of full PTY support (`ptyprocess`/`winpty`) is noteworthy — it enables the agent to use interactive programs (editors, REPLs, debuggers), not just batch commands.

---

## 10. Search and Retrieval Capabilities

### 10.1 Local Search

All four projects use `ripgrep` (or equivalent) as the foundation for text search:

| Project | Grep Implementation | File Discovery | Additional |
| --- | --- | --- | --- |
| **Claude Code** | `GrepTool.ts` wrapping `src/utils/ripgrep.ts` | `GlobTool.ts` for pattern matching | `ReadFileTool.ts` with line ranges |
| **Grok Build** | Search tools in `xai-grok-tools` | `xai-fast-worktree` for rapid traversal | Parallel, gitignore-aware directory walking |
| **Hermes Agent** | Shell-based `ripgrep` and `find` via tools | File reading tools | FTS5 session search across all history |
| **OpenCode** | `grep` tool (regex/literal) | `glob` tool (pattern matching) | `sourcegraph` external code search integration |

OpenCode's `sourcegraph` integration is unique — it enables searching across external codebases for API usage patterns and library documentation.

### 10.2 Semantic and Structural Search

| Project | Symbol Search | Code Graph Traversal | Embedding-Based Search |
| --- | --- | --- | --- |
| **Claude Code** | LSP `workspace/symbol` | None | None |
| **Grok Build** | Tree-sitter scope graph queries | Import/call edge traversal via `xai-codebase-graph` | Not described |
| **Hermes Agent** | None native | None | None |
| **OpenCode** | None native | None | None |

Only Grok Build provides deep structural search via its scope graph. Claude Code delegates to LSP, which provides symbol search but not dependency graph traversal.

---

## 11. Multi-Agent and Sub-Agent Coordination

### 11.1 Sub-Agent Spawning Mechanisms

**Claude Code — Git Worktree Isolation:**
`src/tools/AgentTool/AgentTool.tsx` allows the LLM to spawn sub-agents with `isolation: 'worktree'`. When specified:
1. A temporary git worktree is created from the current branch
2. The sub-agent operates in this isolated copy of the repository
3. File edits by the sub-agent cannot corrupt the parent agent's working directory
4. On success, changes can be merged back into the main worktree
5. On failure, the worktree is simply discarded

**Swarm task board** (`TaskCreateTool`, `TaskUpdateTool`, `TaskListTool`):
Tasks are serialized to disk with file-system locks (`lockfile.ts`) using an atomic lock acquisition pattern. Multiple concurrent agents can safely read/write the shared task board. Task states: pending, in-progress, completed, failed.

**Grok Build — ACP-Mediated Sub-Agents:**
`xai-grok-subagent-resolution` handles sub-agent spawning. `subagent_coordinator.rs` within the `MvpAgent` module orchestrates delegation of nested objectives. Sub-agents communicate back via the same ACP channel system, maintaining the strict IPC boundary.

**Hermes Agent — Async Delegation with Isolated DB Sessions:**
`tools/async_delegation.py` spawns sub-agents that receive isolated database session constraints — they operate in separate SQLite sessions to avoid state corruption. Lock and lease tracking (`_COMPRESSION_LOCK_HOLDER_PID_RE`) ensures clean termination without dangling sub-processes. Parent-child relationships tracked via `_delegate_from` tags.

**OpenCode — Read-Only TaskAgent:**
The `agent` tool in `agent-tool.go` spawns a `TaskAgent` with only read-only tools (`glob`, `grep`, `ls`). This is designed to offload search-heavy tasks from the main context window, not for parallel editing.

### 11.2 Coordination Patterns Comparison

| Pattern | Claude Code | Grok Build | Hermes Agent | OpenCode |
| --- | --- | --- | --- | --- |
| **Isolation** | Git worktree | ACP message boundary | Isolated DB sessions | Read-only tool set |
| **Communication** | Shared task board (file locks) | ACP channels | `_delegate_from` tags | Return value |
| **Parallelism** | Yes (worktree per agent) | Yes (channel-based) | Yes (async) | No (sequential) |
| **Write capability** | Full (in worktree) | Full (in context) | Full (isolated) | None (read-only) |
| **Merge strategy** | Git merge/discard | ACP result propagation | Session linking | N/A |

---

## 12. Security Model Comparison

### 12.1 Permission and Authorization Systems

**Claude Code** — Pluggable permission modes in `src/utils/permissions/`:
- `plan` mode: read-only, no file modifications or command execution
- `auto` mode: automatic approval for safe operations, prompt for dangerous ones
- `yoloClassifier.ts`: Heuristic classifier analyzing shell commands for dangerous patterns (`rm -rf`, `sudo`, network access). Can be backed by an LLM call for nuanced classification.

**Grok Build** — Multi-level permission system:
- `xai-grok-sandbox`: Sandboxed execution environment
- `folder_trust.rs`: Per-directory trust level management
- `PermissionMode`: Gating based on `ClientType` (interactive user vs. automated pipeline)
- `PermissionEvent`: Configurable triggers for permission prompts
- CAS (Compare-And-Swap) state locks for process control during cancellation

**Hermes Agent** — Sophisticated regex guardrails:
- `tools/approval.py`: Iterative regex-based command analysis for destructive patterns
- `ToolGuardrailDecision`: Structured approval/rejection results with reasons
- Domain-based restrictions: Background tools restricted in unapproved domains
- Human-in-the-loop: Sensitive operations trigger approval prompts
- Environment-aware: Different guardrail levels per deployment context

**OpenCode** — Three-state permission model:
- `internal/permission/`: High-risk operations (bash, file writes) paused for user input
- Three choices: Allow (once), Allow for session (auto-approve subsequent), Deny (error to LLM)
- Permission requests sent to TUI via pub/sub event broker

### 12.2 Sandbox and Containment

| Project | Sandbox Mechanism | Network Control | Credential Protection |
| --- | --- | --- | --- |
| **Claude Code** | Process containment | Not described | Not described |
| **Grok Build** | `xai-grok-sandbox` + folder trust + CAS locks | Not described | Not described |
| **Hermes Agent** | Regex guardrails + approval | Not described | Not described |
| **OpenCode** | Permission modals | None | None |

None of the four reference projects implement true container-based sandboxing or network namespace isolation. All rely on application-level permission checks that can be bypassed by a sufficiently creative shell command.

---

## 13. LLM Provider Integration

### 13.1 Provider Support Matrix

| Provider | Claude Code | Grok Build | Hermes Agent | OpenCode |
| --- | --- | --- | --- | --- |
| Anthropic (first-party) | ✅ Primary | Via sampler | ✅ Via `openai` proxy | ✅ Native SDK |
| OpenAI | ❌ | Via sampler | ✅ Via `openai` SDK | ✅ Native SDK |
| AWS Bedrock | ✅ | ❌ | ❌ | ✅ |
| GCP Vertex | ✅ | ❌ | ❌ | ❌ |
| Google Gemini | ❌ | ❌ | ❌ | ✅ |
| Groq | ❌ | ❌ | ❌ | ✅ |
| OpenRouter | ❌ | ❌ | ✅ | ❌ |
| Nous Portal | ❌ | ❌ | ✅ | ❌ |
| xAI (Grok) | ❌ | ✅ Primary | ❌ | ❌ |

### 13.2 API Abstraction Patterns

**Claude Code**: Direct SDK usage (`@anthropic-ai/sdk`) with provider-specific adapters for Bedrock and Vertex. Model defaults to Claude Opus/Sonnet 4.6. All calls use streaming via the async generator.

**Grok Build**: `xai-grok-sampler` wraps a forked `async-openai` crate for streaming completions. `xai-grok-models` handles model management and prefetching. The fork likely adds xAI-specific API customizations.

**Hermes Agent**: All LLM calls proxied through the `openai` SDK as a universal interface. Custom behaviors injected via thin wrappers (e.g., `_effective_temperature_for_model` for per-model temperature overrides). Lazy provider loading: SDKs imported only when needed, keeping startup fast. Multiple models used within a session (fast model for compression, powerful model for reasoning).

**OpenCode**: `internal/llm/provider/` standardizes inputs and streaming outputs across all providers into a unified `AgentEvent` channel. Dynamic feature negotiation: automatically appends provider-specific flags (reasoning effort for models supporting extended thinking). Most architecturally clean abstraction of the four.

---

## 14. Configuration and Extensibility

### 14.1 Configuration Mechanisms

| Project | Config Files | Schema Validation | Environment Variables |
| --- | --- | --- | --- |
| **Claude Code** | `~/.claude.json` (global), `.claude.json` (project) | None | Standard Node.js env |
| **Grok Build** | `xai-grok-config` crate | Rust types | Standard Rust env |
| **Hermes Agent** | `hermes_constants.py`, `.env` files | Python constants | Extensive `.env.example` (24KB) |
| **OpenCode** | `.opencode.json` | `opencode-schema.json` (JSON Schema for IDE autocompletion) | Standard Go env |

OpenCode's provision of a JSON Schema for its configuration file is a thoughtful developer-experience touch — editors can provide autocompletion and validation when editing `.opencode.json`.

### 14.2 Extension Mechanisms

**Claude Code** — MCP + Skills + Marketplace:
- MCP client in `src/services/mcp/client.ts` connects to external MCP servers, dynamically discovering tools
- MCP tools registered as native Claude tools — the LLM invokes them transparently
- Claude Code can also run as an MCP server, exposing its tools to other clients
- Skills system in `src/skills/` for reusable capability bundles
- Marketplace plugin infrastructure for third-party extensions

**Grok Build** — Lifecycle Registry + MCP:
- `ExtensionRegistry` in `xai-agent-lifecycle` dispatches lifecycle hooks (`TurnStart`/`TurnDone`/`TurnAbort`)
- Hooks are zero-ownership — they observe but cannot hijack control flow
- `xai-grok-mcp` provides MCP client integration via `McpState`

**Hermes Agent** — Plugins + Skills + Multi-Gateway:
- `plugins/` directory for plugin extensions
- `skills/` for both user-authored and agent-generated procedural skills
- `optional-skills/` and `optional-mcps/` for pre-built extension packs
- No global module auto-discovery — strict package capability authorization
- Messaging gateways (Discord, Telegram, Slack) as deployment extensions

**OpenCode** — MCP + Configuration:
- `mark3labs/mcp-go` provides MCP client supporting `stdio` and `sse` transports
- External MCP servers configured via `.opencode.json`
- Theme support (Catppuccin, Dracula) as UI extensibility
- No plugin system beyond MCP

---

## 15. User Interface and Deployment

### 15.1 Terminal UI Implementations

| Project | Framework | Rendering Model | Key Features |
| --- | --- | --- | --- |
| **Claude Code** | React (Ink) | Component-based React tree | Streaming output, interactive prompts, multi-line input |
| **Grok Build** | Ratatui | Immediate-mode full-screen | Mouse-interactive, custom textarea widget, background terminals via `ptyctl` |
| **Hermes Agent** | `prompt_toolkit` | Widget-based | Syntax highlighting, fixed input areas, interrupt handling |
| **OpenCode** | Bubble Tea | Elm-architecture messages | Complex layouts, theme support, session history browser |

### 15.2 Deployment Versatility

| Mode | Claude Code | Grok Build | Hermes Agent | OpenCode |
| --- | --- | --- | --- | --- |
| Interactive TUI | ✅ | ✅ | ✅ | ✅ |
| Headless/Pipe | ✅ (`--print`) | ✅ (CI mode) | ✅ | ❌ |
| Daemon | ✅ | ❌ | ❌ | ❌ |
| MCP Server | ✅ | ❌ | ✅ | ❌ |
| MCP Client | ✅ | ✅ | ✅ | ✅ |
| Discord Bot | ❌ | ❌ | ✅ | ❌ |
| Telegram Bot | ❌ | ❌ | ✅ | ❌ |
| Slack Bot | ❌ | ❌ | ✅ | ❌ |
| Web Interface | ❌ | ❌ | ✅ | ❌ |
| Batch Evaluation | ❌ | ❌ | ✅ (`batch_runner.py`) | ❌ |
| Docker | ❌ | ❌ | ✅ | ❌ |

Hermes Agent is unmatched in deployment versatility — the same agent core runs across seven distinct deployment targets.

---

## 16. Testing and Quality Infrastructure

| Project | Test Presence | Test Framework | Benchmark Infrastructure | CI/Quality |
| --- | --- | --- | --- | --- |
| **Claude Code** | **None** — tests stripped from distribution | N/A | None in source | esbuild, TypeScript strict mode |
| **Grok Build** | Dedicated test crates (`xai-grok-test-support`, `xai-test-utils`) | Rust `#[test]` with hermetic helpers | None explicit | `clippy.toml`, `rustfmt.toml` |
| **Hermes Agent** | `tests/`, `tests-js/` | Python + JavaScript testing | `batch_runner.py` for trajectory evaluation | `pyproject.toml` with `ruff` |
| **OpenCode** | `_test.go` files | Standard Go `testing` | None | Standard `go test` |

Hermes Agent's `batch_runner.py` is the only benchmark-oriented evaluation infrastructure found in any of the four codebases.

---

## 17. Comparative Synthesis for SOTA Harness Design

### 17.1 Cross-Cutting Architectural Patterns

Based on the complete source-level investigation, the following patterns emerge as the highest-value design choices for a next-generation harness:

**Pattern 1 — IPC Boundary Between UI and Agent Core**
Proven by Grok Build (ACP) and supported by OpenCode (pub/sub). This decoupling enables:
- Headless operation without UI changes
- Remote/distributed deployment
- UI replacement without touching agent logic
- Testability of the agent core in isolation

**Pattern 2 — Channel-Based Concurrency for Indexing**
Proven by Grok Build (`IndexManager`). Using message-passing channels instead of mutex-based locking for background indexing eliminates contention with the agent loop. Combined with event debouncing and file-size guards (5MB skip), this ensures indexing never blocks tool execution.

**Pattern 3 — Pluggable File Editing Strategies**
Proven by Grok Build (five implementations). A single edit tool with swappable backend implementations enables experimentation and per-context optimization. Combined with hunk-level tracking (`xai-hunk-tracker`), this provides fine-grained undo/redo superior to whole-file rollback.

**Pattern 4 — LSP as Both a Tool and a Diagnostic Source**
Claude Code exposes LSP methods as tools the LLM can invoke. OpenCode intercepts LSP diagnostics and injects them into context. Combined, these provide both proactive code intelligence (understanding structure before editing) and reactive feedback (errors after editing).

**Pattern 5 — Trajectory Compression with Protected Boundaries**
Hermes Agent's first-N/last-N protection with middle-summary compression is the most sophisticated compaction strategy observed. Using a fast, cheap model for the summary is cost-effective. OpenCode's 95% threshold trigger provides a pragmatic emergency fallback.

**Pattern 6 — Inference-Time Skill Generation**
Unique to Hermes Agent. Capturing successful task patterns as reusable procedural skills creates a self-improving loop without model fine-tuning. Skills are loaded into future session contexts, effectively teaching the agent from its own experience.

**Pattern 7 — Type-Safe Database Access**
Proven by OpenCode (`sqlc`). Code-generating type-safe database accessors from SQL definitions eliminates an entire class of runtime errors. Combined with schema migrations (`goose`), this provides robust, evolvable persistence.

**Pattern 8 — NFS-Resilient SQLite**
Proven by Grok Build (`xai-sqlite-journal`). Detecting NFS mounts and degrading from WAL to Truncate journal mode prevents `SIGBUS` panics in clustered development environments — a real-world crash class that most agents silently ignore.

**Pattern 9 — Git Worktree Isolation for Sub-Agents**
Proven by Claude Code. Spawning sub-agents in isolated git worktrees provides safe parallel file editing. Changes are merged on success, discarded on failure. Combined with a shared task board (file locks), this enables multi-agent coordination without a database or message broker.

**Pattern 10 — Lifecycle Extension Hooks**
Proven by Grok Build (`ExtensionRegistry`). Zero-ownership hooks that let extensions observe the agent lifecycle without hijacking control flow. `TurnStart`, `TurnDone`, `TurnAbort` events fire at phase boundaries, enabling observability and analytics without coupling.

### 17.2 Anti-Patterns to Avoid

| Anti-Pattern | Observed In | Why It's Harmful |
| --- | --- | --- |
| 833KB single-file modules | Hermes Agent | Unmaintainable, untestable, merge-conflict magnets. No file should exceed ~500 lines in a well-structured codebase. |
| Literal string replacement for edits | Claude Code | LLM whitespace hallucination causes frequent failures. No fallback strategy. No structural validation. |
| ~63 crates in a single workspace | Grok Build | Over-fragmentation increases navigation difficulty, compilation time, and cognitive overhead without proportional benefit. |
| Stripping tests from distribution | Claude Code | Makes correctness verification impossible. Test suites must ship with source. |
| OpenAI-only API contract | Hermes Agent | Mapping everything through `openai` SDK limits access to provider-specific features (reasoning blocks, cache hints, extended thinking). |
| No formal security model | All four projects | None implement container-based sandboxing or formal threat analysis. Command blocklisting is the highest-level security in all cases — insufficient for autonomous operation. |
| No evaluation infrastructure | Claude Code, OpenCode | Without benchmark suites and gate verification, there is no way to measure improvement or detect regressions. |

### 17.3 Technology Stack Recommendations

Based on the comparative analysis, the optimal technology choices for a SOTA harness are:

| Component | Recommendation | Rationale |
| --- | --- | --- |
| **Control plane** | Python ≥3.13 | Fastest iteration speed, richest LLM SDK ecosystem, `anyio` structured concurrency |
| **Persistence** | SQLite-WAL with NFS detection | Proven by Grok Build. Zero-daemon, crash-recoverable, concurrent-read-capable |
| **Code intelligence** | Tree-sitter + LSP (dual) | Tree-sitter for deterministic code graphs (Grok Build pattern). LSP for real-time diagnostics (OpenCode pattern). |
| **Text search** | BM25 via SQLite-FTS5 | Proven by Hermes Agent. Exact symbol matching is the strongest signal for code retrieval. |
| **Dense retrieval** | Deferred behind recall@10 trigger | Most likely cause of poor retrieval is bad chunking, not vocabulary mismatch. Fix chunking first. |
| **File editing** | Search/replace with Tree-sitter validation + pluggable backends | Combines SAGIHA's spec with Grok Build's pluggable strategy pattern. Syntax validation catches broken edits immediately. |
| **Sandbox** | Rootless Podman container | The only real security boundary. Process-level permission checks are bypassable. |
| **Sub-agent isolation** | Git worktrees | Proven by Claude Code. Safe parallel editing with git-native merge/discard. |
| **TUI** | Decoupled via IPC/pub-sub | Framework-agnostic. Proven by Grok Build (ACP) and OpenCode (pub/sub). |
| **Extension** | Entry-point registration, frozen at composition | Declarative, auditable, statically analyzable. No runtime discovery. |
| **Compaction** | First-N/last-N + middle summary (Hermes pattern) with 95% emergency fallback (OpenCode pattern) | Sophisticated protection of context boundaries with pragmatic safety net. |
| **Self-improvement** | Skill generation (inference-time) + RHI outer loop (scheduled) | Cheap daily improvement via skills, expensive periodic improvement via RHI. |

### 17.4 Quantitative Codebase Metrics

| Metric | Claude Code | Grok Build | Hermes Agent | OpenCode |
| --- | --- | --- | --- | --- |
| Total source files | ~1,915 | ~2,325 | ~3,634 | ~137 |
| Primary language | TypeScript | Rust | Python | Go |
| Largest single file | ~1,700 lines (QueryEngine.ts) | N/A (distributed across crates) | ~20,000+ lines (cli.py, 833KB) | ~500 lines |
| Module count | ~50 directories | ~63 crates | ~31 directories + 20 top-level .py | ~25 packages |
| Dependency count | ~40 (package.json) | ~200+ (Cargo.lock) | ~80 (pyproject.toml) | ~30 (go.mod) |
| Test infrastructure | None in source | Dedicated test crates | `tests/`, `tests-js/`, `batch_runner.py` | Standard `_test.go` files |
| Configuration surface | 2 JSON files | Crate-level configs | 24KB `.env.example`, 47KB constants file | JSON + JSON Schema |
| MCP support | Client + Server | Client | Server | Client |
| Sub-agent support | Git worktree isolation | ACP + coordinator | Async delegation | Read-only TaskAgent |
| Deployment targets | 4 (TUI, pipe, daemon, MCP) | 3 (TUI, headless, ACP) | 7+ (TUI, Discord, Telegram, Slack, web, MCP, batch) | 1 (TUI only) |

---

## 18. Consolidated Design Recommendations for a SOTA Harness

Drawing from all four codebases and the broader harness landscape, a state-of-the-art autonomous coding harness should implement the following design choices:

### 18.1 Architecture
1. Enforce architectural layer boundaries at CI (import-linter contracts), not by convention.
2. Implement a single dispatch choke point between intent and effect — every tool invocation passes through one gateway where policy, authorization, logging, and budget accounting attach.
3. Decouple the UI from the agent core via an IPC protocol (ACP-style or pub/sub), enabling headless, remote, and multi-UI deployment.
4. Use hexagonal port-adapter architecture with `Protocol` interfaces — every component is swappable, and every adapter passes a conformance test suite.
5. Freeze the extension registry at composition — no runtime discovery, no dynamic registration.

### 18.2 Execution
6. Implement dual-process execution: fast ReAct for simple tasks, deliberate best-of-N with verifier scoring for complex tasks.
7. Use a deterministic escalation ladder for routing (System 1 → System 2), generating labeled training data for a future learned router.
8. Bound execution with iteration budgets (Hermes pattern) and resource governors.
9. Implement hard gates (binary admission) separately from soft scores (ranking) — proxies may rank but never admit.
10. Use record/replay determinism with `EffectClass` declarations — `PURE` calls re-execute, `DESTRUCTIVE` calls serve from recorded observations.

### 18.3 Memory
11. Split memory by epistemics: deterministic code graph (Tree-sitter + git, rebuildable from HEAD) vs. episodic memory (bi-temporal, LLM-extracted, with provenance tracking).
12. Track provenance on all memory records (`OPERATOR`/`MODEL`/`EXTERNAL`) to prevent laundering of untrusted data through the memory system.
13. Implement FTS5 full-text search across sessions for experiential memory (Hermes pattern).
14. Support NFS-resilient SQLite by detecting mount type and degrading WAL mode (Grok Build pattern).
15. Implement inference-time skill generation — capture successful task patterns as reusable procedural skills (Hermes pattern).

### 18.4 Context
16. Order prompt content by decreasing stability to maximize cache hit rates — stable prefix, semi-stable task context, append-only conversation tail.
17. Implement compaction as a deliberate checkpoint event, not a continuous process.
18. Use first-N/last-N protection with middle summary for trajectory compression (Hermes pattern) with a 95% capacity emergency fallback (OpenCode pattern).
19. Transport reasoning blocks as opaque provider-native payload — do not normalize to strings.
20. Truncate tool output with explicit `full_output_uri` so the model can deliberately re-fetch.

### 18.5 Tools
21. Cap core tools at ~20 to prevent model selection degradation. Use MCP for extensions beyond this budget.
22. Validate every edit with Tree-sitter syntax checking before the language server sees it (catch structural breaks immediately).
23. Take command arguments as `argv` lists, not shell strings — eliminate an entire class of quoting bugs.
24. Separate `run_tests` from `run_command` to prevent evaluation capture (tests run against pristine injected suite).
25. Mark MCP-discovered tools as `trusted_output=False` by default — third-party servers are injection vectors.

### 18.6 Security
26. The sandbox is the security perimeter — command-string blocklisting is a usability guardrail, not a security control.
27. Wrap all untrusted content (file reads, web fetches, tool output) in explicit `<untrusted-data>` envelopes with provenance tracking.
28. Never place credentials inside the sandbox — inject them per-grant, scoped, short-lived.
29. Control egress at the network namespace (hostname allowlist at HTTP proxy), not by inspecting commands.
30. The Trusted Computing Base (policy engine, evaluator, gate definitions, benchmark tasks) is never writable by the agent.

