---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **AST Indexing & Retrieval**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

## **Chunking Architecture**

Code retrieval quality is primarily governed by AST chunking bounds rather than vector quantization:

* **AST-bounded Spans**: Tree-sitter splits code by function, method, or class boundaries rather than fixed character windows.
* **Context Prefixes**: Every chunk prepends file path, module docstrings, enclosing symbol paths (`module.Class.method`), and method signatures.

## **Hybrid Retrieval Pipeline**

1. **Lexical Retrieval (BM25 via SQLite-FTS5)**: Primary retrieval mechanism; exact symbol matching is prioritized over dense vector proximity.
2. **Graph Expansion**: Expands candidates along import, call, and co-change edges via `CodeGraph`, incorporating valid episodic memory records.
3. **Dense Vector Retrieval** *(Deferred — [ADR-0014](../08-decisions/0014-defer-dense-retrieval.md))*: Deferred until lexical + graph recall@10 targets fail due to vocabulary mismatch.

* `RetrievalHit.score` is normalized to $[0, 1]$ across backends for seamless future dense tier fusion.

## **Vector Storage & Quantization**

Exhaustive float32 SIMD scans complete in single-digit ms for expected repository sizes ($10^5\text{--}10^6$ vectors). Custom quantization sidecars are rejected; when dense retrieval arrives, uncompressed `sqlite-vec` or LanceDB / Qdrant will be evaluated against measured latency thresholds (see [design derivation](../rationale/reference/design-derivation.md)).

## **Skeletonization & Incremental Updates**

* **Skeletonization**: Tree-sitter strips implementation bodies while preserving interface signatures and docstrings for context compaction; re-hydrates full code on compilation failure.
* **Incremental Updates**: File-watcher triggers per-file incremental re-indexing (full re-indexing is fallback only).

## **Evaluation & Domain Contracts**

* Evaluated using **recall@k against repository-specific query sets**. (LongMemEval is excluded as it measures conversational memory, not repository search).
* Domain schemas defined in `src/sagiha/domain/graph.py` (`RetrievalHit`: path, chunk, normalized score, backend metadata); port defined in `src/sagiha/ports/indexer.py`.
