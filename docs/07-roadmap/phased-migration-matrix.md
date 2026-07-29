# **Phased Day 0 → Day N Adapter Migration Matrix**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Evolution Roadmap Matrix**

| Component | Day 0 (Simple Baseline) | Day 1 (Production Ready) | Day 2 (SOTA AGI Harness) |
| :---- | :---- | :---- | :---- |
| **Kernel Orchestrator** | Native Async ReAct Loop | Stateful State Machine + Checkpoints | Dual-Process MCTS + A2A Multi-Agent Fleet |
| **Short-Term Memory** | In-Memory Circular Buffer | Redis Persistence + Compaction | Trajectory-Compressed Context Ring |
| **Long-Term Memory** | SQLite + simple embeddings | LanceDB + SQLite-WAL Event Log | Graphiti Bi-Temporal Graph + LanceDB |
| **Indexing Engine** | Python Tree-sitter + BM25 | SQLite-FTS5 + AST Skeletonizer | Rust/Go gRPC Sidecar (tqdb + Tree-sitter) |
| **Diagnostic Layer** | Subprocess pytest + flake8 | Local Stdio LSP (`pygls`) Adapter | Multi-language LSP Daemon Sidecar |
| **Execution Sandbox** | Local Subprocess + Git Branch | Ephemeral Isolated Git Worktrees | Containerized Docker/gVisor Worktrees |
| **Protocol Integration** | Stdio MCP Tool Drivers | HTTP-SSE MCP Server/Client | Full MCP + A2A Protocol Infrastructure |
| **Self-Improvement** | Manual Prompt Iteration | Automated PRM Step Scoring | RHI Outer Loop under Held-Out Validation |
