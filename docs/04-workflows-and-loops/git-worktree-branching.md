# **Git Worktree Branching & Parallel Isolation**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Concurrency & State Isolation Primitive**
SAGIHA2 treats **Git worktrees** as a first-class isolation primitive for parallel sub-agent execution:

1. **Allocate**: `WorktreeManager` creates an ephemeral working directory linked to a dedicated feature branch off main.
2. **Isolate**: Sub-agents modify code, parse symbols, run compilers, and execute unit tests without file collisions or state corruption.
3. **Commit & Verify**: Changes commit locally upon sub-task completion and run through LSP diagnostics.
4. **Merge**: The Orchestrator validates the branch using optimistic concurrency control, rebasing onto main and running regression suites.
5. **Prune**: Ephemeral worktree directories are safely removed from disk and Git state.
