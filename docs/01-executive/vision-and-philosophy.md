# **Vision & Foundational Design Philosophy**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Core Thesis**
All intelligence, planning, and creative decision-making reside exclusively within frontier LLMs. The SAGIHA2 Meta-Harness is a pure, modular, evolvable environment that provides rich context, structured memory, tool contracts, peer coordination, verification gates, and recursive self-improvement mechanisms.

## **Foundational Principles**
1. **LLM-Centric Intelligence**: Models own reasoning and goals; the harness owns context assembly, policy enforcement, and execution boundaries.
2. **Hexagonal Boundary Isolation**: Zero coupling between core domain logic and external infrastructure via rigid `typing.Protocol` ports and plugin adapters.
3. **Day-Zero Decoupling**: Every component (STM, LTM, AST Indexer, LSP adapter) is an interchangeable plugin from day one.
4. **Dual-Process Cognitive Loops**: Fast System 1 ReAct execution paired with Slow System 2 MCTS tree search over parallel Git worktrees.
5. **Model-Harness Co-Evolution**: The harness scaffolding (prompts, workflows, policies) is an editable artifact optimized via held-out outer-loop evaluation.
6. **Generator-Evaluator Separation**: Independent Evaluator agents and static analysis gates verify code changes before merging to prevent reward hacking.
