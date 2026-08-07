---
status: normative
updated: 2026-08-07
---
# ADR-0019: Three Horizons — Harness, Framework, Meta-Loop

**Status**: Accepted · **Date**: 2026-08-07 · **Fork**: what this project is

## Context

Every document in this tree describes a **SWE-bench harness**. The stated goal is a
**decoupled framework for autonomous agents that can eventually improve its own workflows** —
with coding as one capability among several (Q&A over a codebase, explanation, research,
generic task solving), and with a community building on it.

Those are not the same system, and the difference is not rhetorical. It is welded into the
code:

1. **`domain/task.py` is a SWE-bench record.** `repo`, `base_commit`,
   `environment_image_digest`, `test_command_hash` — all mandatory, no defaults. There is no
   `task_type`, no `inputs`, no expected output, no rubric. A Task for *"explain how the
   dispatcher works"* cannot be constructed without fabricating four fields.
2. **The judge is a test runner.** `EvalSpec` is worktree + image digest + test-command hash;
   `GateReport` is pass/fail/none from an exit code. There is no verdict shape for *"the answer
   was correct"*.
3. **Non-benchmark tasks are structurally unexpressible.**
   `validator.check_evaluator_termination` requires every path from every entry node to reach a
   node of `kind: evaluate`. A topology `retrieve → answer` **fails validation**, and there is
   no `--force`. The framework goal is blocked by a TCB rule.

The word *framework* appears in no live document. So does *self-improvement*, *RAG*, and
*community*. The meta-loop is referenced by ADR-0006, ADR-0013, ADR-0014 and ADR-0017 and
designed by none of them.

**What the competitor survey established.** Four harnesses were read at source level
(`src/kimi_cli`, `src/hermes_agent`, `src/grok_build`, `src/openhands`, plus the `claude_refs`
documentation corpus). Two facts dominate:

- **Every one of them solved extensibility declaratively.** Kimi: YAML `AgentSpec` with
  `extend:`, tools as dotted `module:Class` paths. Grok: skills as markdown frontmatter, a
  plugin marketplace with `install ≠ trust`. OpenHands: ACP — any stdio subprocess is an agent.
  A third party adds capability without forking, everywhere.
- **Not one of them has an evaluation harness.** Zero graders across ~2,200 Hermes files.
  Kimi's completion signal is "the model emitted no tool calls". Hermes's is a magic substring
  in stdout (`MINI_SWE_AGENT_FINAL_OUTPUT`). Grok ships a complete embedded RAG stack and no
  benchmark runner. Hermes's `hermes_self_evolution` is a real GEPA loop whose Phase 5
  "continuous improvement loop" is a one-line empty file and which never opens a PR.

That is the exact inverse of AETHER, and it explains why: **nobody has closed the
self-improvement loop, because you cannot close it safely without a judge you trust.**

## Decision

**AETHER is a framework. SWE-bench is its proving ground, not its purpose.** Development
proceeds in three horizons, in this order, and the order is not reversible.

| Horizon | What it is | Proof it is done |
| :--- | :--- | :--- |
| **H1 — Harness** (M0–M4) | A SWE-bench harness with a deterministic judge and a calibrated instrument | A published lift number with its instrument tuple |
| **H2 — Framework** (M5) | Many task types, a verdict per type, capability declared in data, third parties extend without forking | A `qa` task and a `code_fix` task run on the same engine, each judged correctly |
| **H3 — Meta-loop** (M6) | The system proposes changes to its own roles, topologies and prompts; statistics admit or delete them | An admitted variant whose ancestry, family and derived N are all recorded |

### Why this order, and why it cannot be reversed

**H1 before H2** because a framework whose judge is uncalibrated is worse than a harness — it
produces confident numbers about more things. The A/A floor is what makes any verdict
interpretable, and it is only obtainable on a task type with a deterministic judge.

**H2 before H3** because a meta-loop needs a *space of variants* to search. With one task type,
one verdict and hard-coded roles, there is nothing to propose. The capability layer (M1b) and
the extension contract (M5) are what make the search space exist as **data**, which is what
keeps the meta-loop's grant small enough to be safe.

**H3 last** because [`vision.md`](../vision.md) §2 already names the failure: *"a self-improving
system's most efficient available strategy is to weaken its own judge — and that failure is
retroactive, invalidating every number the project ever produced."* Every horizon below H3
exists to make that impossible before the machinery that would exploit it is built.

### What this decision does not change

- **The invariants stand.** I1–I11 are unchanged in force. I7 and I9 are *restated* to cover
  non-test judges by [ADR-0020](./0020-verdict-capability-and-judge-integrity.md) — restated,
  not relaxed.
- **The TCB stands.** Kernel, evaluator, validator, executor, schemas and CI remain immutable
  by agent or meta-loop (ADR-0006, I8).
- **ADR-0002 stands.** No capability number before the floor, for any task type. A new task
  type gets its own floor before it gets a claim.
- **Sprints 4 and 5 do not move.** Instrument restoration, the A/A floor and the capability
  layer are H1 work and are prerequisites for everything above.

## Consequences

**Positive.** The mission becomes schedulable: M5 and M6 acquire exit gates and funded tasks
where before the framework goal existed only in conversation. The generic task model
(`architecture/task_types_and_verdicts.md`) makes `code_fix` one entry in a table instead of the
system's shape. The extension contract makes community contribution a mechanism rather than an
aspiration.

**Negative, and accepted.** Three ADRs and roughly 12,000 words of new specification before any
of it is built. `Task` gains a discriminated payload, which is a domain change touching the
manifest schema. `check_evaluator_termination` is renamed and generalised — a TCB edit needing
human review.

**Neutral.** The SWE-bench path is byte-identical after the generalisation: `CodeFixPayload`
carries today's four fields unchanged. If the existing 384 tests do not stay green, the
generalisation was done wrong.

## Reversal conditions

- **If H2 lands and no task type other than `code_fix` is exercised within two sprints**, the
  generic model is unearned abstraction: collapse `TaskPayload` back into `Task` and delete the
  verdict registry down to `TestSuiteVerdict`.
- **If a third party has not extended the system via the contract six months after M5**, the
  extension contract is indirection with one user (us), and it folds back into composition.
- **If any horizon is attempted out of order** — a meta-loop before a calibrated judge, a new
  task type before its floor — this ADR is being violated, not revised. The correct response is
  to stop, not to amend.
- **If generalising the verdict costs a single invariant**, revert. The framework is worth less
  than the property that makes its numbers mean anything.

## References

- [ADR-0020](./0020-verdict-capability-and-judge-integrity.md) — the verdict capability, I7/I9 restated
- [ADR-0021](./0021-extension-contract-and-trust.md) — how third parties extend without forking
- [ADR-0002](./0002-no-number-before-the-floor.md) · [ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md) · [ADR-0014](./0014-workflow-topology-is-data.md)
- [`architecture/task_types_and_verdicts.md`](../architecture/task_types_and_verdicts.md) — the design this ratifies
