---
status: normative
updated: 2026-07-29
---
# ADR-0014: Defer Dense Retrieval and the Embedding Provider

**Status**: Accepted
**Date**: 2026-07-29

## Context

The dependency set pinned `sqlite-vec` as the "dense retrieval tier, Day 0" and the config shipped
`embedding_model`, `embedding_dims`, and a `dense_weight` fusion parameter. **Nothing generated the
vectors.** There was an `EmbeddingProvider` port with no adapter and no dependency behind it.

Both ways of closing that gap carry real cost that no budget in this tree accounts for:

* **Local** (`sentence-transformers`, `fastembed`, ONNX) pulls torch or onnxruntime — hundreds of
  megabytes, plus CPU/GPU contention with the agent's own workload, onto an otherwise lean dependency
  list.
* **API** (`voyage-code-3`, OpenAI embeddings) adds per-index cost and network latency to every
  re-index, and breaks the local-first, air-gapped operation the economics module promises.

Meanwhile [Indexing & Retrieval](../05-tech-stack/indexing-and-retrieval.md) already states that for
code, exact-symbol lexical matching is the single strongest signal and is *never demoted below dense
retrieval*. An agent looking for `UserRepository` wants that symbol, not five semantically adjacent
ones.

A prior revision recorded this deferral in prose while the dependency and the config keys stayed in
the manifests. A deferral that ships its dependency is not a deferral — it is a plan an implementer
will follow.

## Decision

v1 retrieval is **lexical + graph**: AST-bounded chunking, BM25 over SQLite FTS5, and code-graph
neighbor expansion.

The dense tier is deferred. Concretely:

* `sqlite-vec` is removed from `pyproject.toml`.
* `embedding_model`, `embedding_dims`, and `dense_weight` are removed from `config.example.toml` and
  the configuration reference.
* The `EmbeddingProvider` port is retained but marked **Experimental**, with no adapter.
* `RetrievalHit` keeps a normalized 0–1 `score`, so a future dense backend fuses without a shape
  change. BM25/FTS5 scores normalize to the same range.

The embedding provider choice becomes its own ADR **when the trigger fires**, not before.

## Consequences

**Makes easy**: S2 ships in a fraction of the time, with the heaviest dependency off the critical
path. The install stays small enough to be a plausible local-first tool. Retrieval quality becomes
measurable before it becomes expensive — recall@10 on a lexical+graph baseline is a real number, and
without it any dense tier is unfalsifiable improvement.

**Makes hard**: intent-shaped queries where the caller does not know the symbol name ("where do we
handle rate limiting") are weaker until the tier lands. This is the actual cost and it is accepted
knowingly.

**Forecloses**: nothing. The port exists and the score shape is compatible.

## Reversal Conditions

**The trigger, stated as a measurement**: recall@10 on the labelled retrieval benchmark falls below
target on the lexical + graph baseline, and error analysis attributes the misses to vocabulary
mismatch rather than to chunking.

That last clause matters. The most likely cause of poor retrieval is bad chunk boundaries, and adding
embeddings on top of bad chunks buys an expensive dependency and no recall. Chunking is fixed first;
the dense tier is considered only against a measured ceiling on a healthy baseline.

When it fires, the provider decision is recorded as its own ADR with the local-vs-API trade-off
resolved against the then-current dependency budget.
