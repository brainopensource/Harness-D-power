---
status: normative
updated: 2026-07-30
---
# ADR-0018: Macro-Workflow Is a Native Step Protocol, Not an Orchestration Framework

**Status**: Accepted
**Date**: 2026-07-30

## Context

Every doc in `docs/04-workflows-and-loops/` describes the **inner** loop: DMARTIC takes a `TaskSpec`
and drives it to a `GateReport`. Nothing describes the **macro** workflow that produces the
`TaskSpec` in the first place. A senior developer given a paragraph of intent does not start editing
— they write a spec, decompose it into stories, order them, pick one, implement it, verify it, record
what happened, and repeat. SAGIHA specifies the fourth of those eight steps and assumes a human
performs the rest.

This is the largest capability gap in the specification, and it is invisible in the current
comparative analysis because none of the four reference harnesses have it either. Grok Build comes
closest with its eight-actor goal system (orchestrator, planner, tracker, strategist, classifier,
evaluator, stop-detector, summarizer) — but those actors are hard-wired Rust types, not a composable
contract. Claude Code, Hermes, and OpenCode all delegate decomposition to the model inside a single
conversation, which is why none of them can gate, replay, or measure a *plan* as a first-class
artifact. The methodology kits circling this space (SpecKit, BMAD, GSD) are prompt collections, not
execution contracts.

So the decision is not *whether* to add a macro layer. It is what shape it takes, and specifically
whether to adopt an existing orchestration framework.

The candidates were LangGraph, LangChain LCEL, Prefect, and Temporal. Each was rejected, and the
reasons are structural rather than aesthetic:

* **Control-flow ownership.** LangGraph owns the loop. SAGIHA's loop is the kernel, and the kernel is
  the TCB ([ADR-0007](./0007-trusted-computing-base.md)). A framework that calls our steps rather
  than being called by them relocates the dispatch choke point outside `kernel/`, which
  `import-linter` exists to prevent and which no amount of care recovers.
* **Prompt-cache invalidation.** LangChain assembles its own message lists. The byte-identical prefix
  rule is the largest cost lever in the system and it cannot survive a third party deciding message
  order. This is the same reasoning that produced
  [ADR-0008](./0008-native-sdks-no-litellm.md).
* **Determinism.** [ADR-0012](./0012-record-replay-determinism.md) requires that every model call
  pass through `ModelProvider` so it can be recorded and replayed byte-for-byte. Frameworks that
  wrap provider clients directly put calls outside the cassette, and replay stops being total.
* **Durability duplication.** Prefect and Temporal solve durable execution well, and SAGIHA already
  solves it — `TrajectoryStore` is the append-only event log, and D9's fix adds the `runs` table.
  Adopting either means running two persistence models and reconciling them.
* **Weight.** All four bring dependency trees larger than SAGIHA's <8,000 LOC target.

Python 3.13 provides everything the layer actually needs: PEP 695 generics for typed step
signatures, `typing.Protocol` for the contract, Pydantic for the payloads, and `anyio` for
structured concurrency.

## Decision

The macro workflow is a **native, declarative step protocol** owned by `agency/`.

**1. The contract is two Protocols, in `ports/workflow.py`, declared `experimental`.**

```
WorkflowStep[In: BaseModel, Out: BaseModel]   — name, async execute(ctx, input_data) -> Out
PipelineRunner                                — composes steps, emits events, persists between them
```

Steps are ordinary Python classes. A step is not permitted to hold a tool reference, mint a `Grant`,
or call a provider outside `ModelProvider` — the same restrictions every other `agency/` module
carries. Composition order is declared in `config.toml` and resolved once at the composition root
([ADR-0004](./0004-no-di-container.md)), which is what makes stages reorderable without touching
kernel code.

**2. Pipeline execution is a first-class, replayable, gated artifact.** Each step boundary emits an
event, and each step's output is persisted to `TrajectoryStore`. A pipeline is therefore resumable at
step granularity, replayable from a cassette, and measurable in E0 — the same three properties the
inner loop already has. A step that cannot be replayed is a defect, not a category.

**3. The initial stage set is four steps**, and no more until each has a gate that measures it
(§8.5 of the comparative analysis): `PRDGeneratorStep` (prompt → `PRDSpec`), `StoryDecomposerStep`
(`PRDSpec` → `StoryBoard`), `CodingStep` (`StorySpec` → DMARTIC inner loop → `GateReport`),
`VerifierStep` (`GateReport` + diff → accept or return to the board).

**4. `TaskSpec` remains the inner loop's sole input.** The macro layer produces `TaskSpec` values; it
does not replace or wrap them. `PRDSpec` and `StoryBoard` are new domain models in
[Task & Acceptance](../03-contracts-and-models/task-and-acceptance.md); `StorySpec` carries a
`parent_task_id` and the disjoint file-set closure that document already specifies for decomposition.
This is what keeps the macro layer optional: a `chat` profile binds no pipeline, and `sagiha run` with
an explicit goal skips straight to `CodingStep`.

**5. What is binding today versus provisional.** The rejection of third-party orchestration
frameworks, the ownership rules (steps live in `agency/`, the kernel is never called by a framework),
and the replayability requirement are **binding now**. The exact Protocol signatures are
**provisional** until the first two steps have adapters and a gate — they graduate under the normal
rule in [Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md),
on evidence rather than calendar.

**6. Sequencing.** This layer is a **non-goal until the inner loop closes.** Sprint 3's exit test
must be green — one failing test fixed, gated, logged, replayable — before any step class is written.
The layer lands with Block 4 / Sprint 5 at the earliest. Writing a planner above a loop that cannot
dispatch a tool (foundation-review D1) is the precise error the 2026-07-29 review diagnosed.

## Consequences

**Easy.** Swapping, reordering, or A/B-testing a stage becomes a config change plus a class, which is
what makes the macro layer a legitimate RHI target: the outer loop can propose a different
decomposition strategy and E0 can measure whether it helped. Each step is unit-testable with a fake
`ctx` and a Pydantic input. Because steps emit events through the same bus, the TUI, the HTTP/SSE
stream, and the audit log get pipeline visibility for free.

**Hard.** SAGIHA owns retry, timeout, cancellation, and partial-failure semantics for the pipeline
itself — work Temporal would have provided. Structured concurrency via `anyio` covers cancellation
and timeouts; retry policy is per-step configuration; partial failure resumes from the last persisted
step output. This is real work, and it is the price of keeping the kernel in control of its own loop.

**Foreclosed.** SAGIHA will not consume community LangGraph nodes. Given that consuming one would
mean granting a third party control of the loop, the prompt prefix, and the provider call, this
forecloses nothing we could have safely used.

**Risk we are accepting knowingly.** A pipeline of LLM-driven planning steps multiplies cost per task
and adds failure modes above the loop — a bad `StoryBoard` wastes every downstream step. The
mitigation is the gate requirement in §3: no stage enters the tree without an E0 measurement showing
it beats running the inner loop directly on the raw prompt. If planning does not beat no-planning on
the benchmark, the layer does not ship.

## Reversal Conditions

Revisit if any of the following becomes true:

* **A framework stops owning the loop.** If LangGraph (or a successor) offers a mode where it is a
  library called *by* our kernel, does not assemble messages, and routes every model call through an
  injected client, the control-flow, cache, and determinism objections all dissolve at once and this
  ADR should be re-argued on dependency weight alone.
* **Durable execution becomes the bottleneck.** If pipeline retry/timeout/resume semantics exceed
  roughly 500 LOC in `agency/`, we are rebuilding Temporal badly and should adopt it behind a port
  instead.
* **The layer fails to pay.** If E0 shows PRD-and-story decomposition does not beat direct execution
  on the benchmark suite after a genuine attempt, delete the stage set and keep only `CodingStep`.
  The Protocol can stay; the pipeline does not have to.
* **Multi-language steps appear.** If a step is better implemented as a non-Python sidecar, the
  in-process `PipelineRunner` needs the same wire treatment as every other port — see
  [Remoteable Ports](../02-architecture/remoteable-ports.md).

## Related

[ADR-0004](./0004-no-di-container.md) (composition root) ·
[ADR-0007](./0007-trusted-computing-base.md) (TCB) ·
[ADR-0008](./0008-native-sdks-no-litellm.md) (no universal abstraction layer) ·
[ADR-0012](./0012-record-replay-determinism.md) (record/replay) ·
[ADR-0017](./0017-execution-profiles.md) (profiles compose ports) ·
[DMARTIC Inner Loop](../04-workflows-and-loops/dmartic-inner-loop.md) ·
[RHI Outer Loop](../04-workflows-and-loops/rhi-outer-loop.md)
