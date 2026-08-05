---
status: normative
updated: 2026-07-29
---
# ADR-0014: Defer Dense Retrieval and the Embedding Provider

**Status**: Accepted  
**Date**: 2026-07-29

## Context
Vector retrieval introduces heavy dependencies (`torch`, `onnxruntime`) or costly network calls (`voyage-code-3`, OpenAI). For code, lexical symbol matching is primary and must not be demoted below dense search. See [Indexing & Retrieval](../05-tech-stack/indexing-and-retrieval.md).

## Decision
- v1 retrieval uses **lexical + graph**: AST-bounded chunking, BM25 over SQLite FTS5, and code-graph expansion.
- Dense tier (`sqlite-vec`, `embedding_model` configs) is deferred and removed from default dependencies/configs.
- `EmbeddingProvider` port remains **Experimental** without default adapters.
- `RetrievalHit` standardizes scores (0–1) to allow future dense score fusion.

## Consequences
- Fast S2 release with minimal dependency footprint.
- Benchmark recall@10 is evaluated on the lexical baseline before adding dense complexity.

## Reversal Conditions
- Benchmark recall@10 falls below target on the lexical+graph baseline, and failure analysis attributes misses to vocabulary mismatch rather than poor chunking boundaries.
