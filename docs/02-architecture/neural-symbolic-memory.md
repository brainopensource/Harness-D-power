# **Neural-Symbolic Memory Subsystem**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Tri-Tier Persistence Layer**
1. **Short-Term Memory (STM)**: In-memory circular sliding ring buffer paired with SQLite-WAL and Redis for active conversational turns, intermediate context frames, and trajectory steps.
2. **Long-Term Memory (LTM)**: Persistent vector index in LanceDB powered by 4-bit TurboQuant scalar quantization for rapid code search.
3. **Bi-Temporal Knowledge Graph**: Graphiti temporal context graph tracking AST dependencies, ADR decisions, git-blame ownership, and dynamic temporal edge invalidation (`invalid_at`).
