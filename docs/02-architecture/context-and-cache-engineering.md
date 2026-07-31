---
status: normative
updated: 2026-07-29
---

# **Context & Cache Engineering**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

Context assembly is the single highest-leverage cost decision in the system. What goes into the window, and in what order, determines both what the model can reason about and what fraction of every call is paid at full price.

## **The Cache Constraint**

Prompt caching requires a **byte-identical prefix**. Any scheme that repartitions the window each turn changes that prefix and forfeits the cache on *every single call*, paying full input price for content that was already cached moments earlier.

This rules out an entire class of design that looks appealing on paper: percentage-based token allocators that divide the window into shares (*n*% instructions, *n*% retrieved snippets, *n*% history) and recompute them per turn. Recomputed allocation churns the prefix continuously while saving nothing — it is the worst available layout, and it is the intuitive one. **Order by stability, not by budget share.**

## **Layered Assembly, Ordered by Stability**

Context is assembled in strict order of decreasing stability, so that growth is append-only and prior tokens stay cached:

| Layer | Contents | Change frequency |
| :---- | :---- | :---- |
| **Stable prefix** | System instructions, tool schemas, durable project conventions | Once per session |
| **Semi-stable** | Retrieved repository context for the current task | Only when retrieval genuinely changes |
| **Append-only tail** | Conversation, tool calls, observations | Every turn, appended |

A cache breakpoint closes the stable prefix. Retrieved context is inserted as messages *after* that prefix, never interleaved into it.

### Layer 6 retrieval is seed-only

**Pre-assembled retrieval is computed once, at task start, and is never refreshed mid-task.** All
subsequent retrieval is **agentic** — the model calls `grep`/`find_symbols`/`get_skeleton` and the
results land in the append-only tail like any other tool output.

The earlier rule ("retrieval is refreshed when the task changes") left a mid-task refresh path
open. Any such refresh rewrites a semi-stable layer that the entire tail is cached behind, which
invalidates every token after it. The saving from fresher context never pays for a full prefix
re-encode, and the cost is paid on a schedule the model does not control.

Making this a *ruling* rather than a guideline buys two things downstream:

* **It is enforced by shape, not discipline.** `ContextAssembler` accepts `retrieval_seed` **only
  at construction**, and exposes no public method that takes a `RetrievalHit` afterwards. A
  contract test asserts this. You cannot violate the rule without changing the constructor.
* **It is what makes interrupt-and-steer possible** (`v2-S7`). Steering becomes a pure tail
  append, so layers 1–7 stay byte-identical and the cache survives the interruption. That
  affordance only exists because nothing rewrites Layer 6 mid-run.

*Implements: `docs/rationale/reviews/next_gen_architecture_specs.md`. Ruling recorded as
[ADR-0021](../08-decisions/0021-seed-only-layer-6-retrieval.md); lands `v2-S3` (PR-3.1).*

## **Compaction Is a Checkpoint, Not a Background Process**

Compaction resets the cache exactly once, in exchange for reclaiming the window. Performed continuously, it pays that cost every turn while saving nothing. It therefore runs at deliberate checkpoints — on task boundaries, or when remaining headroom crosses a threshold — as an explicit, logged, traceable event.

## **Lossless Strategies (applied within the layout)**

* **AST Skeletonization**: strip function bodies, preserve interfaces, attributes, signatures, docstrings.
* **Symbol Context Injection**: scope-local definitions, imports, caller/callee signatures.
* **Log Condensation**: collapse repeated whitespace, duplicate tracebacks, progress spinners.

## **Staged Re-Hydration**

Compaction risks discarding subtle business constraints embedded in comments and docstrings. If an edit fails to compile or test under skeletonized context, the failing files are re-inserted **in full** before the next attempt. Failure to compile is the signal that compaction went too far.

## **Reasoning Blocks Are Transported, Not Owned**

Extended-thinking blocks carry provider signatures that must be returned **verbatim** to continue a tool-use turn. Normalizing reasoning into a plain string — as the previous `TrajectoryStep.thought: str` field required — breaks the signature and forfeits both reasoning continuity and cache hits. Reasoning is stored as opaque provider-native payload (`ReasoningBlock`), round-tripped unmodified, with a separate human-readable `summary` for display and analysis.

## **Tool Output Discipline**

Tool output overflowing the window is a top-tier practical failure mode. `ToolResult` carries explicit `truncated` and `full_output_uri` fields so the model knows output was cut and can retrieve the remainder deliberately, rather than silently reasoning over a truncated log.

## **Metrics**

Cache hit rate is reported alongside token consumption in every run. A token-reduction claim that ignores cache economics measures the wrong quantity — the same prompt can cost 10× more depending only on whether its prefix stayed stable.
