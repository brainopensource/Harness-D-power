# **Control-Agency-Runtime (CAR) Architecture & Sidecars**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Architectural Layering**
The CAR model isolates system responsibilities into four distinct conceptual boundaries:

1. **Control Layer**: Manages security policies, financial token budgets, context allocations, and verification gates before authorizing execution.
2. **Agency Layer**: Handles high-level deliberation, reasoning loops, AST context synthesis, sub-agent task decomposition, and A2A delegation without direct shell access.
3. **Runtime Layer**: Executes sandboxed code, manages isolated Git worktrees, captures terminal streams, and executes local MCP tool drivers.
4. **Native Performance Sidecars (Rust / Go)**: Out-of-process compiled binary services running over gRPC / IPC for CPU-heavy tasks (Tree-sitter AST parsing, `tqdb` vector quantization).
