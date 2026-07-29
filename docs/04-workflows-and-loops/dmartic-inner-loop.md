# **DMARTIC Inner Loop — Dual-Process Cognitive Engine**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Dual-Process Execution Modes**
* **System 1 (Fast Execution):** Direct ReAct single-turn execution for localized, low-complexity tasks.
* **System 2 (Slow Reasoning & Tree Search):** Monte Carlo Tree Search (MCTS) with parallel Git Worktree branching for multi-file refactoring and architectural changes.

## **Operational Cycle Steps**
1. **Design**: Parse task goals; select System 1 or System 2 execution plan.
2. **Measure**: Gather baseline static analysis, LSP type diagnostics, and unit test metrics.
3. **Analyze**: Query AST sidecar index, Graphiti temporal graph, and TurboQuant vector store.
4. **Review (Plan Mode Gate)**: High-impact actions trigger Evaluator LLM or human approval gate.
5. **Test**: Speculative execution inside parallel Git worktrees; immediate LSP diagnostic & test validation.
6. **Improve**: MCTS candidate evaluation via PRM scores and LSP diagnostic deltas.
7. **Control**: Validate safety policies and token budgets, optimistic-rebase winning branch into main.
8. **Self-Reflect**: Trajectory compaction and event log commit into LTM.
