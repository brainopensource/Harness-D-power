---
status: normative
updated: 2026-08-01
---
# ADR-0027: Fixed Chunk-Size Policy; `max_chunk_tokens` Removed

**Status**: Accepted
**Date**: 2026-08-01

## Context

`RetrievalConfig.max_chunk_tokens: int = 1024` was exposed as an operator-facing knob and threaded
through `composition.py` → `IndexService` → `analyze_python_tree`. At the end of that chain the
chunker did:

```python
del max_chunk_tokens  # reserved for oversized-chunk splitting
```

The value was accepted, carried across three call layers, and discarded. Separately, `fts5.py`'s
`_index_python` hardcoded `1024` of its own, so the direct `reindex_file` path ignored the
configured value even in principle.

This is the H-series failure mode applied to configuration: an operator who lowers the setting to
bound prompt cost gets **no behaviour change and no warning**. Config honesty is instrument
honesty — a knob that does nothing is a lie told in a schema instead of in a number.

The audit (M-4) offered two repairs: implement statement-boundary splitting so the knob works, or
delete the field and document the fixed policy.

## Decision

**The field is deleted.** `RetrievalConfig.max_chunk_tokens` is removed, along with every parameter
threading it. Chunk size becomes a single module-level constant in the shared indexer vocabulary:

```python
# src/sagiha/adapters/indexer/walk.py
MAX_CHUNK_TOKENS: Final = 1024  # fixed policy until an ablation justifies tuning
```

Implementing the splitting was rejected. Splitting an oversized AST node at statement boundaries is
a **retrieval-quality change**, and this tree currently has no way to measure whether such a change
helps: the benchmark suite does not exist (audit M-1) and the A/A noise floor is unpopulated.
Shipping an unmeasured heuristic into the subsystem that had just produced a Critical retrieval
defect (C-1) inverts the project's own sequencing rule — measurement strictly before the thing
measured.

Deletion is small, immediately honest, and fully reversible.

## Consequences

**Easy.** One constant, one definition, one behaviour. The `fts5.py` hardcoded `1024` and the
configured value can no longer disagree, because there is only one of them.

**Compatibility — verified, no migration owed.** `RetrievalConfig` is
`ConfigDict(frozen=True)` and does *not* set `extra="forbid"`; Pydantic's default is `ignore`. An
existing `sagiha.toml` carrying `max_chunk_tokens` continues to load without error. It simply stops
pretending to do something.

**Index invalidation — a reindex is required after this change.** The shared-vocabulary refactor that lands `walk.py` also unifies
`module_name()` on the full dotted form, which changes indexer `symbol_path` values. The on-disk
index is a rebuildable cache ([ADR-0011](./0011-split-code-and-episodic-graphs.md)), so a reindex is
required and **no migration is owed for a cache**.

**Foreclosed.** No per-run or per-repo chunk-size tuning until it can be measured. An operator who
wants a different value edits a constant and rebuilds — which is honest about what they are doing.

## Reversal Conditions

Re-introduce a configurable chunk budget when **both** hold:

1. A pinned benchmark suite with a measured A/A noise floor exists (closes audit M-1), so a chunking
   change can be evaluated rather than asserted; **and**
2. an ablation over at least two chunk-size values shows a delta on recall@10 that beats that floor.

If the ablation is negative, the constant stays and the negative result is published — an honest
negative is a deliverable, not a reason to retry with a friendlier setting.

## Related

[ADR-0011](./0011-split-code-and-episodic-graphs.md) (the index is a rebuildable cache) ·
[ADR-0014](./0014-defer-dense-retrieval.md) (the same "no capability without a measured trigger"
discipline applied to the dense tier) ·
[ADR-0026](./0026-indexer-search-replaces-neighbors.md) (the other contract change taken in the same
remediation wave)
