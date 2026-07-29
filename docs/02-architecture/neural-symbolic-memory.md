---
status: normative
updated: 2026-07-29
---

# **Neural-Symbolic Memory Subsystem**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

> [!NOTE]
> **Where these stores live and who writes to them** — file layout, WAL and `busy_timeout` as a
> connection-factory invariant, and the one-writer-per-database rule that keeps parallel worktrees from
> contending — is specified in
> [Storage Layout & Concurrency](../05-tech-stack/control-plane-python.md#storage-layout--concurrency).

## **Persistence Tiers**

1. **Short-Term Memory (STM)**: in-memory sliding ring buffer over the active session, durably backed by SQLite-WAL.

   **Redis is not adopted.** STM is per-session and small, it wants durability co-located with the trajectory rather than a network hop, and SQLite-WAL already supplies persistence, crash recovery, and queryability. A second daemon earns nothing at single-node scale, and the multi-node case that would justify it is not on the roadmap.

2. **Transaction Store**: append-only SQLite-WAL event log for trajectory steps, tool payloads, and diffs. Scores arrive as separate `StepScored` events rather than mutations of stored steps — which is what makes "append-only" true rather than aspirational.

3. **Long-Term Memory**: split into two stores with different epistemics. This split is the most consequential correction in the memory design.

## **The Code Graph and the Episodic Graph Are Different Systems**

Routing both structural code facts and learned experience through one temporal graph engine is expensive and unsound, because the two have entirely different sources of truth.

### Deterministic Code Graph

Imports, call edges, definitions, inheritance, ownership, and co-change coupling are **exactly derivable** from Tree-sitter and git. Passing them through LLM-based entity extraction pays tokens and latency for facts a parser already knows with certainty, and admits hallucinated edges into a dependency graph that impact analysis then trusts.

* **Storage**: SQLite tables written directly by the indexer; an embedded property store such as **Kùzu** when recursive traversal outgrows SQL. Embedded either way — a Neo4j daemon would break the local-first principle for no gain at this scale.
* **Rebuild**: fully derivable from HEAD. It is a cache, not a system of record.
* **Uses**: impact closure for partitioning parallel work, neighbor expansion during retrieval, blast-radius estimation for risk gating.

### Episodic & Decision Memory

ADRs, pull-request rationale, "we tried X and it failed because Y", operator preferences. Here facts are genuinely unstructured, genuinely contested, and genuinely lose validity over time — so LLM extraction and **bi-temporal modelling earn their cost**. An engine such as Graphiti applies here, and only here.

#### The Knowledge Net

Episodic memory is a **linked** store, not a bag of documents. Every `MemoryRecord` carries
`links: tuple[str, ...]` of other memory ids, which makes the tier a navigable graph in the sense a
personal knowledge base is one: a decision links to the episodes that produced it, an episode links to
the files it touched and the failure it explains, a preference links to every episode where it was
applied.

This costs one field, and it is what turns recall from ranked snippets into a traversal. Two queries
matter and neither is expressible over a flat store:

* **Neighborhood** — "what else is connected to this decision, one hop out." The context an engineer
  gets from following a wiki link, and the reason a good note-taking system beats a better search box.
* **Backlinks** — "what depends on this belief." Required for honest invalidation: when a decision is
  reversed, everything that cited it is stale, and without backlinks nothing knows.

The links are cheap because both endpoints already exist. What is deliberately **not** built:

| Not built | Why |
| :--- | :--- |
| A fourth store | The three tiers plus links carry it. A separate knowledge database would duplicate the episodic store with a different name. |
| A dedicated graph daemon | Same reasoning as the code graph: embedded or nothing. |
| Automatic link inference at write time | Cheap to add later against real data, and wrong links are worse than absent ones — a hallucinated edge is a fact the traversal then trusts. Links are written by whoever creates the record: the operator, the agent, or the harness. |

**Where it connects to code.** The two graphs stay separate (they have different sources of truth —
[ADR-0011](../08-decisions/0011-split-code-and-episodic-graphs.md)), but a memory record may reference
a path or `SymbolRef`. That reference is a *pointer*, resolved against the code graph at recall time,
never a copied edge. So "what did we learn about this module" is answerable while the code graph stays
fully rebuildable from HEAD.

**Trust travels the links.** A traversal that reaches an `EXTERNAL` record returns an `EXTERNAL`
record; provenance is per node and never inherited from the node that pointed at it. Otherwise the
graph becomes exactly the laundering path the provenance model exists to close.

### On Bi-Temporality for Code

**Git is already a bi-temporal store.** Valid time is commit time; transaction time is index time; structure re-derives at any ref. Rebuilding that inside a graph database duplicates version control. Temporal invalidation is therefore reserved for learned facts, which git does not track.

## **The Memory Port**

```python
class Memory(Protocol):
    async def remember(self, record: MemoryRecord) -> str: ...
    async def recall(self, query: RecallQuery) -> list[Recall]: ...
    async def neighbors(self, memory_id: str, hops: int = 1) -> list[Recall]: ...
    async def backlinks(self, memory_id: str) -> list[Recall]: ...
    async def invalidate(self, memory_id: str, at: datetime) -> None: ...
```

`Provenance`, `MemoryRecord`, `RecallQuery`, and `Recall` are defined in
[Domain Schemas](../03-contracts-and-models/domain-schemas.md#memory).

**No vector appears in the signature.** Embedding lives behind `EmbeddingProvider`, entirely inside the
adapter — which is what lets the dense tier be deferred ([ADR-0014](../08-decisions/0014-defer-dense-retrieval.md))
without any consumer knowing. A v1 adapter backed by FTS5 and link traversal satisfies this Protocol
completely.

## **Time Handling**

All timestamps are **timezone-aware UTC**, produced by a single `utc_now()` helper. This is a correctness requirement, not a style rule: bi-temporal invalidation compares valid-time against transaction-time across adapters, and naive datetimes are deprecated in Python 3.12 and guaranteed to raise or silently misorder when compared against aware values.

## **Decisions Are Written Back to the Repository**

Durable decisions belong in `docs/decisions/*.md` inside the target repository, not only in an opaque store. Repository-resident memory is versioned by git for free, reviewable in a pull request, diffable, and portable across harnesses. Writes to `docs/decisions/` require `provenance in {OPERATOR, MODEL}` and go through the approval gate.
