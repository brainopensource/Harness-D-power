---
status: normative
updated: 2026-07-31
---
# ADR-0021: Layer-6 Retrieval Is Seed-Only

**Status**: Accepted
**Date**: 2026-07-31

## Context

[Context & Cache Engineering](../02-architecture/context-and-cache-engineering.md) orders the
prompt by stability so that growth is append-only and the prefix stays cached. Layer 6 —
pre-assembled retrieved repository context — sits in the semi-stable band, and the rule was
"retrieval is refreshed when the task changes."

That rule is ambiguous in the one case that matters. "When the task changes" invites a mid-task
refresh whenever the agent's focus shifts, and any rewrite of Layer 6 invalidates **every token
after it** — the entire tail. The saving from fresher retrieved context never pays for a full
prefix re-encode, and the cost lands on a schedule the model, not the harness, effectively
controls.

The ambiguity is not hypothetical. `v2-S6` builds the FTS5 indexer and code graph, and their first
consumer will need a legal insertion point. Deciding this *before* retrieval exists costs a
paragraph; deciding it after means unwinding whatever the first implementer assumed.

## Decision

**Pre-assembled retrieval is computed once, at task start, and is never refreshed mid-task.**

All subsequent retrieval is **agentic**: the model calls `grep`, `find_symbols`, `get_skeleton`, or
`impacted_by`, and the results land in the append-only tail as ordinary tool output. The model
decides what else it needs and pays for it in tail tokens, which are cheap and cached.

**The rule is enforced by shape, not by discipline.** `ContextAssembler` accepts `retrieval_seed`
**only at construction**, and exposes no public method that takes a `RetrievalHit`. A contract test
asserts that no public method accepts a `RetrievalHit` post-construction. Violating the rule
requires changing the constructor signature — a visible, reviewable act, not an accident.

## Consequences

**Easy.** The prefix digest becomes a genuine regression signal: an e2e test asserts
`prefix_digest` is constant across every step of a run. Cache-hit rate becomes attributable —
if it drops, something rewrote the prefix, and there is now exactly one place that could have.

**It is what makes interrupt-and-steer possible** (`v2-S7`). Steering is a pure tail append, so
layers 1–7 stay byte-identical and the cache survives the interruption. That affordance exists only
because nothing rewrites Layer 6 mid-run. This was not the motivation for the ruling, but it is the
larger payoff.

**Hard.** A bad seed cannot be repaired by the harness. If task-start retrieval misses the relevant
files, recovery depends on the model noticing and searching — which requires the retrieval tools to
be good and their descriptions to be honest. The failure mode moves from "expensive" to "requires
the agent to be competent", which is the trade we want but is still a trade.

**Foreclosed.** Any background re-indexing that pushes results into the prompt. An indexer may
update its own store continuously; it may not push into an assembled context.

## Reversal Conditions

* **Seed quality proves to be the binding constraint.** If `v2-S6`'s ablation shows tasks failing
  specifically because the seed was wrong *and* the model's agentic searches could not recover,
  the correct fix is a **re-seed at an explicit task boundary** — a new task, a new cache epoch,
  a logged event — not a silent mid-task refresh. Reopen this ADR for that narrow case only.
* **Prefix caching stops being the dominant cost lever.** If providers ship caching that survives
  mid-prefix edits, the entire constraint dissolves and this ADR should be re-argued on relevance
  rather than economics.
* **Agentic retrieval costs more than it saves.** If tail-resident retrieval consistently consumes
  more tokens than a refresh would have, measure it and reopen. Note that this is measurable only
  after `v2-S1` makes token accounting honest.

## Related

[Context & Cache Engineering](../02-architecture/context-and-cache-engineering.md) ·
[Prompt Architecture](../02-architecture/prompt-architecture.md) (exchange-granular compaction) ·
[ADR-0014](./0014-defer-dense-retrieval.md) (dense tier deferred)
