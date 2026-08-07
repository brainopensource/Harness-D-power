---
status: normative
updated: 2026-08-06
---
# ADR-0014: Workflow Topology Is Data

**Status**: Accepted · **Date**: 2026-08-06 · **Fork**: raised by the Phase 0 lock audit

## Context

[ADR-0013](./0013-workflow-dag-phased.md) ratified the workflow DAG as the execution structure
but left **node composition in Python**. A topology variant is therefore a code change: write
it, review it, merge it, redeploy.

Two consequences, one immediate and one structural.

**Now: experiment cadence is throttled to PR cadence.** The stated goal is that loop
engineering — try a variant, measure it, keep the winner — is a routine activity. The M2
memoization machinery exists to make ablations cheap to *run*; topology-as-code keeps them
expensive to *define*, which caps the same throughput from the other end.

**Later: the self-redesign goal has no safe rung.** [ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md)'s
mutable surface is prompts, skills, instructions and retrieval parameters — topology is not in
it. A meta-loop that wants to try "add a plan node before generate" must therefore open a code
PR. That is correct for safety today, and it means the *only* mechanical path from where we are
to machine self-redesign runs through **arbitrary code modification** — the most dangerous grant
in the system, and the first one we would be forced to hand out. The intermediate rung is
missing, and it is missing by omission rather than by decision.

The amendment is cheap **now** and not later, which is the same shape as I3: the
`WorkflowStep[In, Out]` socket types landing at M0 are exactly the validation substrate a schema
needs, and four nodes are trivial to express as data. At forty nodes over code that already
assumes Python composition, it is a rewrite.

## Decision

**Node implementations remain code. Node composition becomes data.**

Topologies are **declarative, hash-pinned artifacts** (`workflows/*.yaml`) validated against a
schema and executed by the executor. A topology's identity is the sha256 of its canonical JSON
form; every cross-reference is by hash, never by filename.

**The schema, the validator and the executor are TCB. The topologies are not.** The meta-loop —
and a human loop-engineer — may propose any graph the schema admits, and neither can change what
the schema admits.

Five static checks, enforced by the validator, which **refuses on violation with no `--force`**:

1. **Socket type compatibility** across every edge, using the registered `WorkflowStep[In, Out]`
   types.
2. **Evaluator termination** — every path from every entry node ends at an `evaluate` node.
   **No topology can route around the judge.** This is structural I7, checkable in milliseconds,
   and it is the check that makes the rest of this ADR safe.
3. **Bounded iteration** — repair blocks carry `max_iterations` (1–16). This is where
   [ADR-0013](./0013-workflow-dag-phased.md) rev. 2's repair edge becomes expressible.
4. **Declared fan-out** — Best-of-N sites carry `n` and a cache-sequencing hint; naive parallel
   fan-out over a cold prefix is **not expressible** in a valid topology.
5. **Budget annotation** on every effectful node, so the executor reserves before dispatch.

**Governance.** Topologies join the [ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md)
mutable surface as a new row, and are **admitted only through the
[ADR-0003](./0003-statistical-admission-protocol.md) rev. 2 gate** — a topology is a mechanism,
and no mechanism promotes without an ablation clearing the floor. Human proposers use the
identical path; the meta-loop is just another proposer, with no privileged route.

Schema: [`../development/schemas_and_contracts.md`](../architecture/schemas_and_contracts.md) §1.

## Consequences

- **Zero momentum cost.** M0 is unchanged. The M1a walking skeleton simply *is* the first
  data-defined topology — one trivial YAML instead of one trivial Python composition, the same
  afternoon. M2 memoization keys on node-input digests exactly as ratified.
- **Rollback is structural.** Topologies are hash-pinned data, so reverting an admitted topology
  is a one-line pin change rather than a revert-and-redeploy.
- The schema grows constraints as constructs land: iteration at M1a+, fan-out at M3. It does not
  need to be complete on day one.
- **The autonomy ladder gains its missing rung.** Prompts → topology → code, each admitted by the
  same gate, rather than prompts → code.
- The executor is now TCB-adjacent and carries a validator, which is real code that did not exist
  before. That cost is paid once.

## Reversal Conditions

**[ADR-0013](./0013-workflow-dag-phased.md)'s escape hatch extends to cover this ADR.** If the
node abstraction is not carrying weight at the M2 boundary — no measurable memoization benefit
and no branching in sight — the graph collapses to a sequential pipeline and this ADR is
superseded with it. **A four-node YAML is even cheaper to un-abstract than four-node Python.**

Separately: if the schema is repeatedly amended to admit graphs that were previously invalid,
the constraints are being negotiated rather than enforced, and topology returns to code until
the constraint set is stable. **A validator that grows a new exemption per proposal is a review
process wearing a schema.**
