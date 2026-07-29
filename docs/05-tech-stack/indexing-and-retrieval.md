---
status: normative
updated: 2026-07-29
---

# **AST Indexing & Retrieval**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

This module was previously titled "Indexing & TurboQuant Vector Quantization." The retitle reflects a correction of priorities: **quantization was specified and chunking was not**, which is precisely backwards for retrieval quality.

## **Chunking — The Dominant Variable**

Retrieval quality for code is governed far more by how source is split into retrievable units than by how those units are stored, compressed, or scored. It is also the least glamorous part of a retrieval stack, which is why it is routinely left unspecified while effort goes to the ranking layer.

**The unit is the AST-bounded span**: a function, method, or class body emitted by Tree-sitter — never a fixed character window, which severs signatures from bodies and produces fragments that cannot be interpreted.

Every chunk is prefixed with the context needed to make sense of it in isolation:

* File path and module docstring
* Enclosing symbol path (`module.Class.method`)
* The signature itself, repeated when an oversized body must split on statement boundaries

## **Hybrid Retrieval Pipeline**

1. **Lexical (BM25 via SQLite-FTS5)** — exact symbol names, class definitions, error strings. For code, exact-symbol matching is the single strongest signal and is **never demoted below dense retrieval**. An agent looking for `UserRepository` wants that symbol, not five semantically adjacent ones.
2. **Graph expansion** — expand candidates along import, call, and co-change edges via `CodeGraph`, then contribute episodic decisions filtered to those still valid.
3. **Dense** *(deferred — [ADR-0014](../08-decisions/0014-defer-dense-retrieval.md))* — embedding similarity for intent-shaped queries where the caller does not know the symbol name.

**v1 is tiers 1 and 2.** The dense tier is deferred behind a measured trigger: recall@10 falls below
target on the lexical + graph baseline *and* error analysis attributes the misses to vocabulary
mismatch rather than to chunk boundaries. That second clause is the important one — the most likely
cause of poor retrieval is bad chunking, and adding embeddings on top of bad chunks buys an expensive
dependency and no recall.

`RetrievalHit.score` is normalized 0–1 for every backend, so the dense tier fuses in later without a
contract change. Fusion weighting is then tuned against the measured recall set, not assumed.

## **Vector Storage & Quantization Sizing**

A large repository chunks to roughly **10⁵–10⁶ vectors**. At 10⁵, an exhaustive float32 SIMD scan completes in single-digit milliseconds. Aggressive quantization becomes relevant around 10⁷ and above.

**Quantization therefore solves a problem this system does not yet have** — and the dense tier it would compress is itself deferred ([ADR-0014](../08-decisions/0014-defer-dense-retrieval.md)), so this is a deferral behind a deferral. When the dense tier does arrive it starts uncompressed (`sqlite-vec`, then LanceDB), and compression is adopted only against a **measured latency or memory ceiling** — at which point it is an adoption decision, not an implementation project: LanceDB embeds in-process with zero IPC, and Qdrant already ships a production TurboQuant engine. Building a bespoke quantization sidecar would duplicate mature work to solve a non-problem.

The TurboQuant research remains catalogued in the [design derivation](../reference/design-derivation.md) for the day the trigger fires.

## **Skeletonization**

Tree-sitter strips function bodies while preserving interfaces, attributes, signatures, and docstrings — used for context compaction, and re-hydrated in full when an edit fails to compile under the compacted view.

## **Incremental Update**

File-watch driven, per-file re-index. Full re-index is a fallback, not the normal path; a system that rebuilds the whole index on every save has a feedback loop too slow to be part of the inner loop.

## **Measuring Retrieval Directly**

Retrieval is evaluated on its own terms as **recall@k against a labelled query set drawn from the target repository**, reported separately from task success so that retrieval regressions are attributable rather than hidden inside an end-to-end number.

**LongMemEval is not an appropriate benchmark here** — it measures conversational long-term memory, not code retrieval, so no score on it supports a claim about repository search. It appears in vendor comparisons for graph memory engines, which is exactly why it is easy to adopt by accident.

## **Retrieval Port Shape**

Ensure the retrieval interface returns ranked, scored results:

```python
class RetrievalHit(BaseModel):
    path: str
    chunk: str
    score: float  # normalized 0-1, backend-agnostic
    metadata: dict[str, Any] = {}
```

Note: BM25/FTS5 scores normalize to 0-1; future dense (cosine) backends will use the same shape. This ensures the port is backend-agnostic without building dense retrieval now.
