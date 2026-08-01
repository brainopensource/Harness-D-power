---
status: normative
updated: 2026-08-01
---
# ADR-0026: `Indexer.search(query)` Replaces `Indexer.neighbors(path)`

**Status**: Accepted
**Date**: 2026-08-01

## Context

`ports/indexer.py` declared `async def neighbors(self, path: str, limit: int = 20) ->
list[RetrievalHit]` — a promise of path-scoped neighbour expansion. The only implementation,
`FTS5Indexer`, declared `async def neighbors(self, query: str, limit: int = 20)` and performed
full-text search over indexed chunks. The two had drifted apart in three ways at once:

* **Type.** PEP 544 makes parameter *names* part of a Protocol's structural contract, because a
  keyword call must work against any implementation. The mismatch produced a pyright error at
  `composition.py`, which went undetected for a sprint because `pytest` was green and nobody
  re-ran the type checker (audit defects C-R1 and C-2).
* **Semantics.** The sole production caller, `composition.build_retrieval_seed`, passes a **task
  goal string**. It was never passing a path. The port's `path` parameter was the lie, not the
  adapter's `query`.
* **Honesty.** A reader of `ports/indexer.py` — the file the project designates as contract truth —
  learned the wrong thing about what the subsystem does.

The audit offered two repairs: (A) rename the port's parameter to `query`, a one-line pyright fix;
or (B) split the APIs, renaming the FTS operation to `search` and *keeping* `neighbors(path)` on
the Protocol for graph expansion.

## Decision

**`neighbors` is renamed to `search(query: str, limit: int = 20) -> list[RetrievalHit]` on both the
Protocol and the adapter, and `neighbors` is deleted from the port entirely.**

`ports/indexer.py` is now exactly three methods: `find_symbols`, `get_skeleton`, `search`.

Option A was rejected: it clears the type error while baking the semantic lie into the contract
permanently. The parameter name was a symptom; the wrong method name was the defect.

Option B's second half was rejected on two independent grounds:

1. **Graph expansion already exists.** `CodeGraph.impacted_by(file_path, hops)` is specified,
   implemented against `TreeSitterCodeGraph`, and tested. A `neighbors(path)` on `Indexer` would be
   a second, competing name for the same capability, on a port that cannot serve it as well.
2. **[ADR-0023](./0023-port-rent-rule.md) forbids it.** A port method with zero implementations is
   unpaid rent from the moment it is written. Adding one *in the same change that removes a
   different piece of contract drift* would be a contradiction.

## Consequences

**Easy.** A reader of the port now learns what the subsystem does. `composition.py` type-checks.
Retrieval seeding and graph expansion are two clearly named operations on two clearly separated
ports.

**Blast radius (measured, not estimated).** One production call site (`composition.py`) and nine
test call sites across `tests/contracts/test_indexer_conformance.py`, `tests/unit/test_fts5_indexer.py`
and `tests/unit/test_index_service.py`. `pyright` catches any site missed, because the old method
no longer exists on the Protocol.

**Foreclosed.** Nothing may reintroduce a path-scoped expansion method on `Indexer`. Callers wanting
impact analysis use `CodeGraph.impacted_by`.

**Not bumped.** `PORT_VERSION` stays at 1 and `STABILITY` stays `provisional`. The port has one
adapter and one production consumer, both changed in the same commit, and a provisional port is
explicitly permitted to change shape without a migration. There is nothing to migrate.

**Guarded against recurrence.** This class of drift is now mechanically detected:
`tests/contracts/test_adapter_conformance.py` asserts adapter→Protocol assignability for every
adapter/port pair, so a divergence fails the type gate at a named assertion site instead of
surviving behind a green test run.

## Reversal Conditions

Reintroduce a distinct `neighbors`-style method on `Indexer` only when **both** hold: a production
consumer needs path-scoped expansion *from the index* rather than from the code graph, **and** an
adapter implements it in the same change. Absent an adapter, ADR-0023 applies and the method does
not go on the port.

## Related

[ADR-0011](./0011-split-code-and-episodic-graphs.md) (code graph vs. episodic memory — why
expansion belongs to `CodeGraph`) ·
[ADR-0014](./0014-defer-dense-retrieval.md) (the dense tier stays deferred; this ADR does not
change that trigger) ·
[ADR-0019](./0019-port-consolidation.md) (the deletion/re-promotion pattern reused here) ·
[ADR-0023](./0023-port-rent-rule.md) (why keeping `neighbors` unbacked was not free) ·
[ADR-0027](./0027-fixed-chunk-size-policy.md) (the other contract change taken in the same
remediation wave)
