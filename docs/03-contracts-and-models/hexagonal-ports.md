# **Hexagonal Interface Ports (`typing.Protocol`)**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Core Port Definitions**
All kernel components interact exclusively via stable Python `typing.Protocol` interfaces:

* **`ShortTermMemory`**: Append and retrieve step trajectories.
* **`LongTermMemory`**: Vector storage and similarity search.
* **`Indexer`**: Codebase AST indexing, file updates, and symbol resolution queries.
* **`KnowledgeGraph`**: Bi-temporal episode logging, fact searches, and edge invalidation.
* **`ToolRegistry`**: Register tool schemas and dispatch executions.
* **`WorktreeManager`**: Allocate, merge, and release ephemeral Git worktree branches.
* **`Workspace`**: File diff application and workspace root path retrieval.
* **`TreeSearchOrchestrator`**: MCTS candidate branch exploration and evaluation.
* **`Orchestrator`, `Evaluator`, `MetaImprover`**: High-level lifecycle, verification, and harness self-evolution.
