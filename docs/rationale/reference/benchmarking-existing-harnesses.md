---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **SOTA AI Coding Agent Harnesses: Benchmarking & Architectural Teardown**

> [!NOTE]
> **Working Proposal Disclaimer**: This reference brief analyzes production-proven AI coding agent harnesses (Claude Code CLI, Aider, OpenHands, SWE-agent, Grok Code Build) to extract technical teardowns, prompt caching rules, tool interfaces, and actionable lessons for SAGIHA.

---

## 1. **Claude Code CLI (Anthropic)**

### **Architectural Teardown**
Claude Code is Anthropic's official terminal-based agentic CLI built with TypeScript and a React/Ink TUI. Its architecture cleanly separates LLM reasoning from execution boundaries across five core layers:

1. **Memory Layer (`CLAUDE.md`)**: Project-specific rules, architecture patterns, and conventions auto-injected at the root.
2. **Tool Execution Layer (MCP)**: Native Model Context Protocol (MCP) integration for file manipulation, shell command execution, and remote tool discovery.
3. **Permissions Boundary**: Deny-first security model requiring explicit human confirmation for destructive shell commands or file writes outside the working directory.
4. **Lifecycle Hooks**: Pre-tool and post-tool interception hooks that allow validation, linting, or log transformation before/after tool runs.
5. **Observability & Trajectories**: Persistent JSONL session transcripts logging exact prompt turns, tool calls, and model reasoning blocks.

### **Prompt Caching Mechanics**
* **Prefix Matching Rule**: Anthropic’s API caches static prompt prefixes. Claude Code structures its prompt layout with zero variation at the top:
  `[System Instructions] -> [Tool Schemas] -> [CLAUDE.md Memory] -> [Dynamic Context / Conversation Turns]`
* **Cache Invalidation Avoidance**: Changing tool definitions or model parameters mid-session breaks prefix matching and invalidates the cache. Keeping the prefix static and appending turns monotonically is what preserves the hit rate, and it is the single largest cost lever in a multi-step harness. *(Specific hit-rate figures for competing harnesses were previously quoted here without a source and have been removed — this tree does not tabulate numbers it has not measured.)*

### **Lessons for SAGIHA**:
* Adopt a **prefix-locked prompt layout** (System instructions -> Tool schemas -> Static repo context -> Dynamic turns) to maximize prompt caching efficiency.
* Implement pre/post tool hooks for LSP diagnostic checks and secret redaction.

---

## 2. **Aider (Paul Gauthier)**

### **Architectural Teardown**
Aider is a terminal-based AI coding assistant focused on interactive file editing using **Git as the single source of truth**:

1. **Tree-sitter Repository Map (`repomap`)**: Instead of dumping entire files into the prompt, Aider parses the repository using Tree-sitter AST queries (`@name.definition` and `@name.reference`).
2. **PageRank Context Selection**: Aider builds a directed graph of symbol definitions and call references across files, applying a PageRank-style ranking algorithm to select the most relevant function/class signatures within a strict token budget.
3. **Git Auto-Commit Engine**: Every edit applied by the model automatically triggers a Git commit with a generated commit message. Git serves as the primary transaction, rollback, and checkpoint engine.
4. **Caching & Invalidation**: Tree-sitter tag metadata is cached locally in SQLite (`diskcache`) and invalidated strictly using file modification timestamps (`mtime`).

### **Lessons for SAGIHA**:
* Use Tree-sitter for **deterministic AST symbol graph extraction** and PageRank-style relevance scoring instead of expensive LLM-based extraction.
* Enforce **commit-per-step inside Git worktrees** to provide instant rollbacks, audit logs, and diff verification.

---

## 3. **OpenHands (All-Hands-AI / OpenDevin) & SWE-agent**

### **Architectural Teardown**
OpenHands and SWE-agent focus on long-horizon autonomous software engineering and SWE-bench evaluation:

1. **Event-Stream Architecture**: Decouples the agent control loop from execution runtimes via a non-blocking asynchronous event bus. Actions (`CmdRunAction`, `FileWriteAction`) and Observations (`CmdOutputObservation`) flow through an append-only event stream.
2. **Agent-Computer Interface (ACI)**: Replaces raw shell calls with specialized, compact terminal tools (e.g. `scroll_up`, `goto_line`, `search_dir`) to prevent terminal output from blowing the context window.
3. **Containerized Sandbox Isolation**: Code execution runs inside containerized Docker / gVisor (`runsc`) sandboxes with restricted network egress and filesystem mounts.

### **Lessons for SAGIHA**:
* Decouple the event stream from the execution sandbox so agent state transitions remain replayable.
* Truncate and structure terminal output (with `truncated: true` flags and resource handles) to protect context windows.

---

## 4. **Grok Code / Grok Build Paradigms**

### **Architectural Teardown**
Grok Code emphasizes high-throughput ReAct execution and isolated parallel branch exploration:

1. **Git Worktree Concurrency**: Spawns sub-agents inside isolated Git worktree directories (`git worktree add`), allowing multiple hypotheses to be tested concurrently without file lock collisions.
2. **Extension System (Skills, Plugins, Hooks)**: Modular skills and dynamic plugins registered via configuration files without altering core kernel code.

### **Lessons for SAGIHA**:
* Use **Git worktrees as the primary parallel isolation primitive**, ensuring parallel sub-agents never collide on active file state.

---

## 5. **SAGIHA Synthesis & Superior Architectural Blueprint**

By synthesizing the best elements of these mature open-source harnesses while fixing their documented flaws, SAGIHA establishes a superior architecture:

| Feature / Dimension | Claude Code CLI | Aider | OpenHands | Grok Code | **SAGIHA Meta-Harness** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Control Plane** | TypeScript / Ink | Python / Click | Python / EventStream | Custom ReAct | **Python >=3.13+ Async Microkernel (`typing.Protocol`)** |
| **Tool Protocol** | Native MCP | Custom Block Edits | Event Stream Actions | MCP / Local | **MCP (Tools) + A2A (Peer Delegation)** |
| **Code Structure Index** | None (reads files) | Tree-sitter Repomap | File search | AST Indexing | **Tree-sitter AST Skeletonizer + BM25/FTS5 + code-graph expansion** (dense tier deferred, ADR-0014) |
| **Diagnostics Gate** | Manual / CLI | Auto pytest | Pytest runner | Unit tests | **First-Class `LSPAdapter` (Real-Time Type Diagnostics)** |
| **Parallel Isolation** | Single Workspace | Single Workspace | Single Docker Container | Git Worktrees | **Ephemeral Git Worktree Branches + Pristine Test Gate** |
| **Prompt Cache Strategy**| Static Prefix Match | Manual Windowing | Event Compaction | KV Cache | **Strict Cache-Stable Prefix Layout** (alert threshold > 0.80; no target claimed before measurement) |
| **Cognitive Engine** | ReAct Loop | Single-Turn ReAct | ReAct Loop | High-Throughput ReAct | **Dual-Process Engine (System 1 ReAct / System 2 verifier-guided Best-of-N + sequential repair)** |
