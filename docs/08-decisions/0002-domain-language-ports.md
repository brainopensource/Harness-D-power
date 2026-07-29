# ADR-0002: Ports Speak Domain Language

**Status**: Accepted
**Date**: 2026-07-28

## Context
The original `LongTermMemory` port exposed `store_vector(key, vector: list[float])` and `search_similar(query_vector)`. That is a vector-database driver, not a domain contract: it forced the core to own the embedding model, and it could not accept a temporal-graph adapter that ingests text episodes and has no vector to receive — which was the roadmap's own stated Day-2 target. The port broke the migration the same document promised.

## Decision
Every port is written in domain language. `Memory` exposes `remember` / `recall` / `invalidate`. Embedding lives behind a separate `EmbeddingProvider`, entirely inside adapters. No `Dict[str, Any]` crosses a port boundary; every payload is a Pydantic model. All timestamps are timezone-aware UTC.

## Consequences
Adapters are genuinely swappable, which is what makes deferring LanceDB, temporal graphs, and sidecars free. Adapters carry more internal complexity — they own embedding, pooling, retries, and schema migration. Some port methods look less efficient than a backend-shaped call would; that is the cost of the seam and it is worth paying.

## Reversal Conditions
A profiled case where the domain-shaped call imposes a real, measured performance cost that adapter-side optimization cannot recover.
