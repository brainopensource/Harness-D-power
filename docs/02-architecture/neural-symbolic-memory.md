# **Neural-Symbolic Memory Subsystem**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

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

### On Bi-Temporality for Code

**Git is already a bi-temporal store.** Valid time is commit time; transaction time is index time; structure re-derives at any ref. Rebuilding that inside a graph database duplicates version control. Temporal invalidation is therefore reserved for learned facts, which git does not track.

## **The Memory Port**

```python
class Provenance(str, Enum):
    OPERATOR = "operator"    # human turn — authoritative
    HARNESS = "harness"      # tree-sitter, LSP, git — deterministic, trusted
    MODEL = "model"          # agent's own reasoning
    EXTERNAL = "external"    # repo content, web, MCP — untrusted

class MemoryRecord(BaseModel):
    # ...
    provenance: Provenance

class Memory(Protocol):
    async def remember(self, record: MemoryRecord) -> str: ...
    async def recall(self, query: RecallQuery) -> list[Recall]: ...
    async def invalidate(self, memory_id: str, at: datetime) -> None: ...
```

No vector appears in the signature. Embedding lives behind `EmbeddingProvider`, entirely inside the adapter.

## **Time Handling**

All timestamps are **timezone-aware UTC**, produced by a single `utc_now()` helper. This is a correctness requirement, not a style rule: bi-temporal invalidation compares valid-time against transaction-time across adapters, and naive datetimes are deprecated in Python 3.12 and guaranteed to raise or silently misorder when compared against aware values.

## **Decisions Are Written Back to the Repository**

Durable decisions belong in `docs/decisions/*.md` inside the target repository, not only in an opaque store. Repository-resident memory is versioned by git for free, reviewable in a pull request, diffable, and portable across harnesses. Writes to `docs/decisions/` require `provenance in {OPERATOR, MODEL}` and go through the approval gate.
