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
