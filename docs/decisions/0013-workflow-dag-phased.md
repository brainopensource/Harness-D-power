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
| **M1a+** | **The repair edge** — `evaluate →(fail, k)→ repair → apply → evaluate`, a bounded iteration | Small |
| **M2** | **Per-node memoization keyed by input digest**; partial re-execution | Real |
| **M3** | Branching, fan-out, conditional paths — parallel candidates as graph structure | Real |

**The graph is the execution structure; the event stream is the observation structure.**
Nodes emit events as they run; **events never drive node scheduling.**

### The repair edge (rev. 2, 2026-08-06)

[`vision.md`](../vision.md) §2 names the failing-test→context repair edge **"the single
largest lever on score in the entire system."** Rev. 1's four-node pipeline terminates on
first evaluation and cannot express it. The project's stated biggest lever had no node, no
gate and no task.

**A bounded cycle is still a DAG.** A repair loop with a static unroll bound `k` expands to
`repair₁ … repair_k` at plan time, so the acyclic model is preserved exactly and no new
execution semantics are introduced. Topologies declare it as a block:

```
repair: { from_node: evaluate, via_nodes: [repair, apply], back_to: evaluate,
          max_iterations: k, budget_per_iteration: {...} }
```

Three constraints, enforced by the validator, not by convention:

1. **`max_iterations` is mandatory and bounded** (1–16). An unbounded repair loop is the
   "looping forever" failure `vision.md` names, expressed as a graph.
2. **Each iteration reserves its own budget** through the governor's reserve/commit/release
   triple — repair is where per-task cost actually escapes.
3. **`on_instrument_error` never routes into repair.** A `GateReport` of `None` means the
   instrument failed, not that the candidate is wrong; repairing against it teaches the loop
   to fix the harness's own bugs. It routes to a terminal flag node
   ([`measurement.md`](../measurement.md) §2, B4).

Because repair is a *node* rather than logic hidden inside `generate`, it is memoizable at
M2 and ablatable in isolation — which is the entire reason the graph abstraction exists.
Repair-on vs repair-off is **M2's first capability ablation**, ahead of the generated-context
and Architect/Editor ablations, because it is the largest expected effect and therefore the
one whose measurement is worth the most.

## Consequences

The M2 memoization is not a performance nicety. **No mechanism promotes without an ablation,
and an ablation re-runs a pipeline with one node changed.** Memoization turns that from a
full re-execution into a subtree re-execution. The cost of running ablations is therefore a
first-order design concern, and this is the mechanism that pays it down — which makes M2 the
phase where the abstraction starts earning its keep.

A second load appears at decomposition: task dependencies with auto-unblocking. That is a
real reason for the graph beyond memoization.

A third, added in rev. 2: **the repair edge makes the node abstraction earn its keep at
M1a+ rather than M2.** A pipeline that terminates on first evaluation would have made the
graph look gratuitous for a whole milestone.

**Node composition became data** in [ADR-0014](./0014-workflow-topology-is-data.md). Node
*implementations* remain code; the four-node skeleton and the repair block above are the
first declarative topologies. That amendment does not change any phase in the table.

## Reversal Conditions

If the node abstraction is still not carrying weight at the M2 boundary — **no measurable
memoization benefit and no branching in sight** — collapse it to a plain sequential pipeline.

The escape hatch stays open until M2 precisely because **four nodes are cheap to un-abstract;
forty would not be.**
