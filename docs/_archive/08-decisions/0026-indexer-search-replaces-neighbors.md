---
status: historical
updated: 2026-08-01
---
# ADR-0026: `Indexer.search(query)` Replaces `Indexer.neighbors(path)`

**Status**: Accepted  
**Date**: 2026-08-01  

## Context

`ports/indexer.py` declared `neighbors(self, path: str, limit: int = 20)`, while `FTS5Indexer` implemented `neighbors(self, query: str, limit: int = 20)`. This parameter mismatch caused structural pyright errors in `composition.py`. Callers passed goal strings (`query`), not file paths (`path`).

Graph expansion is already served by `CodeGraph.impacted_by(file_path, hops)`. Keeping an unbacked `neighbors(path)` method on `Indexer` violated [ADR-0023](./0023-port-rent-rule.md).

## Decision

**`neighbors` is deleted. Both `Indexer` Protocol and adapter adopt `search(query: str, limit: int = 20) -> list[RetrievalHit]`.**

`ports/indexer.py` consists of three methods: `find_symbols`, `get_skeleton`, and `search`.

- Graph expansion belongs exclusively to `CodeGraph.impacted_by`.
- `PORT_VERSION` remains at 1 (`STABILITY: provisional`).
- Added adapter-to-Protocol type conformance assertions in `tests/contracts/test_adapter_conformance.py` to prevent parameter drift.

## Consequences

- **Easy**: Aligns port interface with implementation semantics and resolves pyright type errors.
- **Blast Radius**: 1 production call site (`composition.py`) and 9 test call sites updated.
- **Foreclosed**: Re-introducing path-scoped expansion on `Indexer`.

## Reversal Conditions

Reintroduce a path-scoped expansion method on `Indexer` only if a production caller requires index-based path expansion **and** an adapter ships it simultaneously (per ADR-0023).

## Related

[ADR-0011](./0011-split-code-and-episodic-graphs.md) · [ADR-0014](./0014-defer-dense-retrieval.md) · [ADR-0019](./0019-port-consolidation.md) · [ADR-0023](./0023-port-rent-rule.md) · [ADR-0027](./0027-fixed-chunk-size-policy.md)
