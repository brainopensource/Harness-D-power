---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Neural-Symbolic Memory Subsystem**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

> [!NOTE]
> Storage layouts, WAL settings, and single-writer concurrency rules are defined in [Storage Layout & Concurrency](../05-tech-stack/control-plane-python.md#storage-layout--concurrency).

## **Persistence Tiers**

1. **Short-Term Memory (STM)**: Session sliding ring buffer backed durably by SQLite-WAL (no Redis daemon).
2. **Transaction Store**: Append-only SQLite-WAL log storing trajectory steps and `StepScored` events.
3. **Long-Term Memory (LTM)**: Dual-graph memory system separating structural code facts from episodic experience.

## **Dual Graph Architecture**

### 1. Deterministic Code Graph
* **Source of Truth**: Derived directly from Tree-sitter ASTs and Git history.
* **Storage & Scope**: SQLite tables or embedded **Kùzu** property graph; fully rebuildable from HEAD.
* **Use Cases**: Impact closure for worktree partitioning, neighbor expansions, blast-radius risk scoring.

### 2. Episodic & Decision Memory (Knowledge Net)
* **Source of Truth**: ADRs, operator preferences, and failure retrospectives parsed via LLM extraction (Graphiti).
* **Graph Linking**: Every `MemoryRecord` holds explicit `links: tuple[str, ...]` enabling **Neighborhood** and **Backlinks** traversals for invalidation cascades.
* **Code Pointers**: Memory records store path/`SymbolRef` pointers resolved against the Code Graph at query time.
* **Provenance Rules**: `Provenance` is node-specific and never inherited via graph traversal.

| Deferred / Excluded | Rationale |
| :--- | :--- |
| **Fourth Memory Store** | Tiers + explicit links cover all access patterns. |
| **Dedicated Graph Daemon** | Local-first embedded engines (SQLite/Kùzu) avoid daemon overhead. |
| **Automatic Link Inference** | Manual/harness link creation avoids hallucinated edges. |

## **The Memory Port**

Contract in [`src/sagiha/ports/memory.py`](../../src/sagiha/ports/memory.py): `remember`, `recall`, `invalidate`.
* Models defined in [`src/sagiha/domain/memory.py`](../../src/sagiha/domain/memory.py) (see [Domain Schemas](../03-contracts-and-models/domain-schemas.md#memory)).
* **No Vectors in Port Signature**: Embeddings live behind `EmbeddingProvider` inside adapters, per [ADR-0014](../08-decisions/0014-defer-dense-retrieval.md).

> [!IMPORTANT]
> Graph link extensions (`neighbors`, `backlinks`) represent planned S2 port updates (see 2026-07-29 Foundation Review).

## **Time Handling & Repo Writeback**

* **Timezones**: All timestamps are aware-UTC generated via `utc_now()`.
* **Repository Writeback**: Architectural decisions flush back to `docs/decisions/*.md` in the target repo. Writes require `OPERATOR` or `MODEL` provenance and pass through the approval gate.
