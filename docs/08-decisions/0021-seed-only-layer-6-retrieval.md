---
status: normative
updated: 2026-07-31
---
# ADR-0021: Layer-6 Retrieval Is Seed-Only

**Status**: Accepted  
**Date**: 2026-07-31  

## Context

[Context & Cache Engineering](../02-architecture/context-and-cache-engineering.md) places pre-assembled retrieved context in Layer 6 of the prompt prefix. Mid-task refreshes of Layer 6 invalidate all cached prompt tokens following it.

## Decision

**Pre-assembled retrieval is computed once at task start and never refreshed mid-task.**

Subsequent retrieval is purely **agentic**: the model invokes tools (`grep`, `find_symbols`, `get_skeleton`, `impacted_by`), placing results in the append-only prompt tail.

**Enforced by contract structure**: `ContextAssembler` accepts `retrieval_seed` only at construction time and exposes no post-construction update methods.

## Consequences

- **Easy**: `prefix_digest` remains constant throughout a task, ensuring measurable prompt cache hits. Enables interrupt-and-steer workflows (`v2-S7`).
- **Hard**: Bad initial retrieval seeds cannot be auto-repaired by the harness; recovery relies on agentic tool search.
- **Foreclosed**: Background prompt-push re-indexing mid-task.

## Reversal Conditions

- Ablation demonstrates tasks failing specifically due to unrecoverable initial seed errors (warranting task-boundary re-seeding).
- Provider caching mechanisms evolve to support cheap mid-prefix edits.
- Agentic tail retrieval costs exceed prefix invalidation refresh costs.

## Related

[Context & Cache Engineering](../02-architecture/context-and-cache-engineering.md) · [Prompt Architecture](../02-architecture/prompt-architecture.md) · [ADR-0014](./0014-defer-dense-retrieval.md)
