---
status: normative
updated: 2026-07-29
---
# ADR-0017: Execution Profiles Over Task-Type Branching

**Status**: Accepted
**Date**: 2026-07-29

## Context

The architecture assumes every task is a coding task. `Orchestrator.execute` allocates and
materializes a worktree, the inner loop measures with a toolchain, and the `Evaluator` produces a
`GateReport`. There is no path that skips any of it.

That is wrong for a meaningful share of what an LLM harness is asked to do — explaining a codebase,
answering an architecture question, reviewing a diff, holding a conversation. On a two-turn question,
worktree materialization plus container start plus language-server indexing is the overwhelming
majority of wall-clock, spent to produce nothing the task needs.

The obvious fix is a `task_type: Literal["coding", "chat", "analysis"]` field on `TaskSpec` with
branch points in the orchestrator. It was rejected — see Alternatives.

## Decision

`TaskSpec` carries **`profile: str = "coding"`**, resolved at composition against a registry of
profiles defined in config.

A profile is data: it declares which optional ports are bound (`Workspace`, `Toolchain`, `Evaluator`),
which tools are available, which model role serves the run, and what admits the result. Four profiles
ship — `coding`, `analysis`, `review`, `chat` — and third parties add more through `sagiha.profiles`
entry points.

Three rules make it safe:

1. **Profiles compose ports; the kernel does not branch on them.** No `if profile == …` anywhere in
   the orchestrator.
2. **`gates = "none"` produces no `GateReport` and emits no `gate.evaluated`.** An empty report whose
   `admitted` property is vacuously `True` is never constructed.
3. **Profiles subtract capability, never supervision.** Every profile dispatches through the same
   choke point under the same `PolicyEngine`; `always_gate` and the TCB boundary are unaffected.

The field is `str`, not an enum, deliberately: an enum closes the set at the contract layer and
defeats the extension surface.

## Consequences

**Makes easy**: a chat or review task skips the entire filesystem pipeline and answers in one model
call. SAGIHA becomes usable as a general agent runtime — which is what "any human or AI can drive it"
requires — without a second codebase. The four shipped profiles cover the common cases and cost one
config block each.

**Makes hard**: two things now vary per run that previously did not. Every consumer of `GateReport`
must handle `None`, and every doc that says "the run materializes a worktree" needs the qualifier
"under the `coding` profile." Both are one-time costs; the second is why this ADR lands with a
consistency sweep rather than alone.

**A real downgrade, stated plainly**: a task under `gates = "none"` terminates on the model's own
completion signal. Nothing independently verifies it. That is exactly the property this architecture
otherwise refuses to accept, and it is why `coding` remains the default and why the profile is
recorded in `run.started` and in the trajectory — so no analysis ever mistakes an ungated run for a
gated one.

**Forecloses**: nothing. `coding` behaves exactly as before.

## Alternatives Considered

**`task_type` enum with orchestrator branch points.** Simpler and smaller. Rejected because every new
task shape becomes a kernel change plus an enum member, which contradicts
[ADR-0013](./0013-extension-registration.md) — a project that lets third parties ship an *adapter*
without a fork but requires a pull request to ask a question is incoherent. It also puts task-shape
knowledge inside the kernel, which is precisely what the port architecture exists to keep out.

**Separate entry points per task shape** (`execute_chat`, `execute_task`). Rejected: it breaks the
single headless boundary that makes "adding a channel requires zero core changes" true, and it would
fork the event stream that every cockpit subscribes to.

**Do nothing; run non-coding work through the coding pipeline.** Rejected on cost, but the honest
version of this argument is that a worktree for a read-only task is *merely wasteful*, not incorrect.
It was rejected because the waste is large enough to change what the harness is usable for, not
because it is unsound.

## Reversal Conditions

* Profiles accumulate beyond roughly a dozen, or begin encoding per-customer behavior — a sign the
  mechanism has become a configuration language and the boundary belongs somewhere else.
* Any profile requires a kernel branch to work. That falsifies rule 1 and means the composition model
  is not expressive enough for the case; the answer would be a new port, not a special case.
* Evidence that ungated profiles are being used for work that should have been gated — in which case
  restrict profile selection by autonomy level rather than removing the mechanism.
