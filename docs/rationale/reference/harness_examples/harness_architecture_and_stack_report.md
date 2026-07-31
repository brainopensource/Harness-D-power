# Harness Architecture, Design & Tech Stack Report

This report evaluates architectural patterns, technology stacks, UI/UX frameworks, and IPC designs for **AETHER DAG v2** by analyzing SOTA reference implementations (Grok Build, Claude Code, Hermes Agent, OpenCode/Crush, Gemini AGY).

## Summary Table: Proposed Architectural & Stack Improvements (Ranked by Complexity)

| Rank (Complexity) | Architecture / Stack Proposal | Proposed Tech / Design | Refactor Complexity | Target Component | Impact & Rationale vs Reference SOTA |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **1** | **Declarative TOML Composition & Profiles** | `tomllib` stdlib + Pydantic v2 | Low | `sagiha.toml` / `composition.py` | Single-file configuration (`gates="none"`, `autonomy`, model tiering) enabling hot-swappable execution modes (*Claude Code / OpenCode pattern*). |
| **2** | **CGO-Free SQLite WAL & Pure Persistence** | SQLite-WAL + `anyio` async wrappers | Low-Med | `TrajectoryStore` / `A-MEM` | Zero-daemon, crash-resilient local storage with bi-temporal transaction safety (*OpenCode WASM / Grok Build journal pattern*). |
| **3** | **Decoupled Terminal UI (ACP Engine)** | `Textual` (Python) / `Ratatui` (Rust) | Medium | `src/aether_tui/` | Decouples interactive UI from kernel core via Agent Client Protocol (ACP), eliminating monolithic UI/agent coupling (*Grok Build / OpenCode pattern*). |
| **4** | **Hybrid PyO3 Rust Offloading Engine** | Rust PyO3 crate (`aether-core-rs`) | Medium | `adapters/indexer/` & `compactor/` | Offloads Tree-sitter AST parsing, FTS5 chunking, and token BPE counting to Rust for 50x throughput (*Grok Build Cargo workspace pattern*). |
| **5** | **System 3 Hibernation & Worktree DAG Engine** | `FrozenRunState` + `GitWorktreeManager` | Med-High | `sagiha_conductor` / `agency/` | Enables multi-day mission hibernation, process restarts, and parallel worktree story merges with automated `IntegrationStep` re-gating. |

## Executive Summary & High-Level Recommendations

AETHER DAG's Hexagonal Port-Adapter architecture provides a solid foundation that avoids the monolithic clutter of Hermes Agent (~18k line CLI) and Claude Code (~1.7k line QueryEngine). By adopting **Textual/Ratatui via Agent Client Protocol (ACP)** for terminal rendering, leveraging **PyO3 Rust modules** for compute-bound AST indexing, and utilizing **SQLite-WAL** for zero-maintenance state persistence, AETHER DAG v2 achieves the performance of Grok Build's Rust infrastructure while maintaining Python's rapid AI development velocity.
