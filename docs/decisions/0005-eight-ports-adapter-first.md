---
status: normative
updated: 2026-08-05
---
# ADR-0005: Eight Ports, and a Port Arrives With Its First Adapter

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F5

## Context

This was listed as a contested fork. **It was not contested** — the audit found both
proposals had written the same rule, one of them in three separate places including its
Sprint 0 deliverable and the first bar of its Gantt chart. The fork register described the
opposing position as the reverse of what that proposal actually said.

The rule itself is a post-mortem: the predecessor declared **seventeen ports and five had no
implementation at all**. An interface designed against an imagined adapter is a guess with
type annotations. The rule existed in the predecessor's own documentation and was not
enforced — which is an argument for mechanism, not for restating the rule.

## Decision

**Eight boundaries, nine protocols:**

`ModelProvider` · `Workspace` · `WorktreeManager` · `ToolRegistry` · `PolicyEngine` (TCB) ·
`ResourceGovernor` · `TrajectoryStore` · `Evaluator` (TCB) · `Indexer`

*(`Workspace` and `WorktreeManager` are two protocols on one boundary.)*

**Entry rule.** A port enters `src/aether/ports/` **in the same change as its first adapter
and its conformance test.** Not the same sprint — the same change.

**What counts as the first adapter (rev. 2, 2026-08-06).** A **mock adapter plus its
conformance test satisfies the entry rule only when the first real adapter is named** — a
specific adapter, in the same ADR or backlog task, with an owner. A mock with no named
successor is an imagined implementation with a test suite attached, which is the failure this
rule exists to prevent wearing a disguise.

The clause exists because the rule and the plan disagreed: M0 lands nine protocols while the
backlog funds one real adapter, and the mock-adapter set was already mandated by the Phase 0
brief as a Tier-4 deliverable. Left unreconciled, the flagship ADR would have been violated by
the first sprint. Mocks are also load-bearing beyond this: 100 turns in 50 ms with no API call
and no container is what makes the ablation cadence real rather than aspirational.

**Growth tier**, admitted only under that rule: `CodeGraph`, `Memory`, `Toolchain`,
`CandidateSearch`.

**Not ports:** `Orchestrator`, `MetaImprover`, short-term memory, measurement (it is a tool,
not a port), and `LSPAdapter` (ADR-0011).

## Consequences

- The port catalog cannot outrun the implementation, which is the failure this rule exists
  to prevent.
- Enforcement is a conformance meta-test, not review discipline. **A port whose conformance
  suite has an empty parameter list fails that meta-test** — a suite that selects no adapter
  tests nothing, the same defect class as a contract that selects no file.
- A port with no adapter is deleted rather than deprecated.
- The mock clause makes the conformance meta-suite (`TASK-005`) a **precondition of M0**, not
  an M1a nicety: mocks satisfy the entry rule only because they are conformance-tested.

## Reversal Conditions

A port with **two independent adapters planned in the same phase** may be introduced ahead
of the first, **with the second named** in the ADR that introduces it. This is the only
exemption, and it requires naming — not intending.

**On the mock clause:** if a mock-satisfied port reaches the milestone of its named real
adapter with that adapter unbuilt, the port is **deleted**, not carried. The clause buys
sequencing, not permanent credit.
