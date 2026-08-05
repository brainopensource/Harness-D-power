---
status: normative
updated: 2026-08-01
---
# ADR-0027: Fixed Chunk-Size Policy; `max_chunk_tokens` Removed

**Status**: Accepted  
**Date**: 2026-08-01  

## Context

`RetrievalConfig.max_chunk_tokens: int = 1024` was exposed in configuration and threaded through `composition.py` → `IndexService` → `analyze_python_tree`, where it was discarded (`del max_chunk_tokens`). Meanwhile, `fts5.py` hardcoded `1024`. Exposing non-functional configuration knobs misleads operators.

## Decision

**`RetrievalConfig.max_chunk_tokens` and all threaded parameters are deleted.**

Chunk size is defined as a single module constant:
```python
# src/sagiha/adapters/indexer/walk.py
MAX_CHUNK_TOKENS: Final = 1024  # fixed policy until an ablation justifies tuning
```

Implementing statement-boundary splitting was rejected prior to establishing benchmark suites and A/A noise floors. Unmeasured retrieval changes violate the project rule: measurement strictly before implementation.

## Consequences

- **Easy**: Eliminates unused config parameters and aligns `fts5.py` chunking with `walk.py`.
- **Compatibility**: Existing `sagiha.toml` files with `max_chunk_tokens` load without error (Pydantic ignores extra fields).
- **Index Invalidation**: Dotted `symbol_path` refactoring requires index rebuilds (indexes are rebuildable caches per [ADR-0011](./0011-split-code-and-episodic-graphs.md)).
- **Foreclosed**: Configurable chunk sizes prior to empirical evaluation capability.

## Reversal Conditions

Re-introduce configurable chunk budgets only when:
1. A benchmark suite with a measured A/A noise floor is operational; **and**
2. Ablation across chunk size values demonstrates recall@10 improvements exceeding that floor.

## Related

[ADR-0011](./0011-split-code-and-episodic-graphs.md) · [ADR-0014](./0014-defer-dense-retrieval.md) · [ADR-0026](./0026-indexer-search-replaces-neighbors.md)
