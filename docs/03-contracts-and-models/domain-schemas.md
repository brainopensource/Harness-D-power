# **Domain Schemas & Data Models**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Core Pydantic v2 Models**
SAGIHA2 defines frozen, type-safe data structures used throughout the kernel:

* **`TaskStatus`**: `submitted`, `working`, `input-required`, `auth-required`, `completed`, `failed`, `canceled`.
* **`ActionType`**: `file_read`, `file_write`, `shell_exec`, `graph_query`, `lsp_diagnostics`, `sub_agent_delegate`.
* **`ToolCall` & `ToolResult`**: Immutable payloads detailing requested actions, results, error strings, and execution latency.
* **`DiagnosticItem`**: LSP diagnostic information containing file path, line, column, severity, message, and diagnostic code.
* **`TrajectoryStep`**: Step-wise reasoning turn containing thought string, tool calls, tool results, timestamp, and PRM step score.
