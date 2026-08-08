---
status: normative
updated: 2026-08-06
---
# ADR-0017: A Sub-Agent Is a Subgraph, and Its Capabilities Only Narrow

**Status**: Accepted · **Date**: 2026-08-06 · **Fork**: raised by the Phase 0 lock audit

**Decided now, built at M3+.** The primitive it depends on — graph fan-out — lands at M3, and
[ADR-0005](./0005-eight-ports-adapter-first.md) forbids building ahead of that. What is settled
here is the shape, so that when multi-agent work starts it does not arrive as a new privileged
pathway.

## Context

Multi-agent orchestration is the capability most likely to be added as a new abstraction, because
it is usually described as one: a supervisor, workers, a message bus between them. Every one of
those descriptions implies a second execution structure alongside the workflow graph and a second
authorization path alongside dispatch.

The predecessor's own review already reached the correct conclusion one layer up: the long-horizon
"Conductor" holds **zero tools, zero shell, zero capability grants**, and every effect is a task
submitted down one port. A pilot, never an executor.

The genuinely new question is authorization. If a parent delegates to a sub-agent, what may the
sub-agent do — and the failure mode is not exotic: a sub-agent spawned to run tests acquires write
access because the delegation copied the parent's grants wholesale.

## Decision

- **A sub-agent is a workflow subgraph**, not a new construct. Its nodes call `ModelProvider` with
  a role-scoped context and a role-scoped capability policy. `Orchestrator` **remains a non-port**
  ([ADR-0005](./0005-eight-ports-adapter-first.md)): orchestration is domain logic over the graph,
  not an I/O boundary.
- **Capabilities attenuate, never amplify.** A sub-agent's capability set is **strictly ⊆ its
  parent's**, enforced at grant issuance in the kernel rather than by convention at the call site.
  An "Editor" sub-agent cannot hold a grant its parent does not hold, and no delegation depth
  restores one.
- **Budgets sub-divide through the existing triple.** N sub-agents carve N child leases from one
  parent reservation; a child's release refunds the **parent**, not the global pool, so cancelling
  losers refunds correctly. Best-of-N is the degenerate case of this and needs nothing extra.
- **Context is not inherited.** A sub-agent receives an explicitly assembled context with
  provenance labels intact ([ADR-0015](./0015-taintgate-provenance-model.md)); it does not receive
  the parent's transcript. Inherited context is how an untrusted span reaches a component that
  never audited it.
- **Delegation depth is 1**, and a sub-agent's tool set excludes delegation — enforced at the
  registry. Unbounded recursive delegation is unbounded cost with no gate at the bottom.

## Consequences

- Multi-agent work needs no new port, no new package and no new authorization path. If a proposal
  requires one, that is a signal the design is wrong, not that a fourth form is needed.
- Sub-agent topologies are admitted like any other topology
  ([ADR-0014](./0014-workflow-topology-is-data.md)) — through the
  [ADR-0003](./0003-statistical-admission-protocol.md) rev. 2 gate. "Multi-agent" is not a reason
  to skip an ablation; it is an expensive mechanism and therefore especially owed one.
- Attenuation makes some delegations impossible by construction. That is the point: a parent that
  cannot write cannot delegate writing.

## Reversal Conditions

If subgraph scoping proves insufficient for genuinely heterogeneous agents — a peer with its own
model, tools and lifecycle rather than a scoped role — it reopens **as a port question** under
ADR-0005, with its first adapter named.

**Not reversible:** attenuation itself. A delegation path that can widen capability defeats the
capability model outright, and depth-1 with strict subset containment is what keeps the blast
radius of a delegated compromise bounded by the parent's own authority.
