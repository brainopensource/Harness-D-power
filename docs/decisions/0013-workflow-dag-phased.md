---
status: normative
updated: 2026-08-05
---
# ADR-0013: The Workflow DAG Lands in Four Phases

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: the DAG

## Context

The workflow DAG was flagged as having "disappeared from three consecutive implementation
plans without anyone voting to drop it." **That premise is wrong** — it was deliberately
re-sequenced, and the re-sequencing carried a reversal condition, which is more than most
decisions in this set had. This ADR restates it so it stops being re-litigated.

It is the one component in AETHER with **no reference implementation**: no system in the
study set applies a node graph to agent cognition. The original placement was late, which is
the worst position for an unproven abstraction — introduced over code that already assumes a
straight line, with retrofit cost paid exactly when the system is most complex.

Two facts change the sequencing:

- **A linear pipeline *is* a DAG with no branches.** Starting with a trivial graph costs
  almost nothing.
- **The dependency direction is asymmetric.** Retrofitting a graph onto a pipeline is far
  more expensive than starting with a trivial graph.

## Decision

| Phase | What lands | Cost |
| :--- | :--- | :--- |
| **M0** | `WorkflowStep[In, Out]` — node and socket types only. **No executor** | Near zero |
| **M1a** | Walking skeleton runs as a **four-node linear graph** (`retrieve → generate → apply → evaluate`) through a trivial executor. Nodes execute unconditionally | Small |
| **M2** | **Per-node memoization keyed by input digest**; partial re-execution | Real |
| **M3** | Branching, fan-out, conditional paths — parallel candidates as graph structure | Real |

**The graph is the execution structure; the event stream is the observation structure.**
Nodes emit events as they run; **events never drive node scheduling.**

## Consequences

The M2 memoization is not a performance nicety. **No mechanism promotes without an ablation,
and an ablation re-runs a pipeline with one node changed.** Memoization turns that from a
full re-execution into a subtree re-execution. The cost of running ablations is therefore a
first-order design concern, and this is the mechanism that pays it down — which makes M2 the
phase where the abstraction starts earning its keep.

A second load appears at decomposition: task dependencies with auto-unblocking. That is a
real reason for the graph beyond memoization.

## Reversal Conditions

If the node abstraction is still not carrying weight at the M2 boundary — **no measurable
memoization benefit and no branching in sight** — collapse it to a plain sequential pipeline.

The escape hatch stays open until M2 precisely because **four nodes are cheap to un-abstract;
forty would not be.**
