---
status: normative
updated: 2026-07-30
---
# ADR-0018: Macro-Workflow Is a Native Step Protocol, Not an Orchestration Framework

**Status**: Accepted  
**Date**: 2026-07-30  

## Context

SAGIHA's inner loop (DMARTIC) drives a `TaskSpec` to a `GateReport`. The macro workflow—generating `TaskSpec`s from high-level intent, decomposition, and sequencing—is required for full autonomy.

External orchestration frameworks (LangGraph, LCEL, Prefect, Temporal) were evaluated and rejected for structural reasons:
- **Control-flow ownership**: Frameworks taking control of the loop relocate dispatch outside `kernel/`, violating [ADR-0007](./0007-trusted-computing-base.md) (TCB).
- **Prompt-cache invalidation**: Third-party message ordering breaks byte-identical prefix caching ([ADR-0008](./0008-native-sdks-no-litellm.md)).
- **Determinism**: Direct model provider wrapping bypasses `ModelProvider` cassette recording ([ADR-0012](./0012-record-replay-determinism.md)).
- **Durability duplication**: Rebuilds functionality already provided by `TrajectoryStore`.
- **Dependency weight**: Heavy external dependencies exceed light target footprint (<8,000 LOC).

## Decision

The macro workflow is a **native, declarative step protocol** in `agency/`.

1. **Protocols in `ports/workflow.py` (`experimental`)**:
   - `WorkflowStep[In: BaseModel, Out: BaseModel]`: `name`, `async execute(ctx, input_data) -> Out`
   - `PipelineRunner`: Composes steps, emits events, persists state between steps.
   Composition order is declared in `config.toml` and resolved at the composition root ([ADR-0004](./0004-no-di-container.md)).
2. **Replayable & Gated**: Step boundaries emit events and persist outputs to `TrajectoryStore`, supporting step-granularity resume and cassette replay in E0.
3. **Initial Stage Set (4 steps)**: `PRDGeneratorStep` (prompt → `PRDSpec`), `StoryDecomposerStep` (`PRDSpec` → `StoryBoard`), `CodingStep` (`StorySpec` → DMARTIC → `GateReport`), `VerifierStep` (`GateReport` + diff → accept/retry).
4. **`TaskSpec` Compatibility**: `TaskSpec` remains the inner loop's sole input; macro steps generate `TaskSpec`s without replacing them. `PRDSpec` and `StoryBoard` live in [Task & Acceptance](../03-contracts-and-models/task-and-acceptance.md).
5. **Binding vs. Provisional**: Framework rejection, TCB ownership, and replay requirements are binding. Protocol signatures remain provisional until initial adapters/gates land per [Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md).
6. **Sequencing**: Non-goal until the inner loop closes (Sprint 3 exit test green). Lands in Block 4 / Sprint 5 at earliest.

## Consequences

- **Easy**: Stages can be swapped, reordered, or A/B-tested via config. Replay and event streams work out-of-the-box.
- **Hard**: Harness must handle native retry, timeout, cancellation (`anyio`), and partial-failure resumption.
- **Foreclosed**: Cannot consume community LangGraph nodes.
- **Risk Accepted**: Multi-step LLM planning increases cost per task. Gated by requirement that planning steps must outperform raw prompt execution on E0 benchmarks.

## Reversal Conditions

- External framework allows in-kernel loop ownership, byte-level cache protection, and provider interception.
- Pipeline retry/resume logic exceeds ~500 LOC in `agency/` (warranting Temporal behind a port).
- E0 measurement proves PRD/story decomposition does not outperform direct inner-loop execution.
- Multi-language sidecar steps emerge requiring RPC wire treatment (see [Remoteable Ports](../02-architecture/remoteable-ports.md)).

## Related

[ADR-0004](./0004-no-di-container.md) · [ADR-0007](./0007-trusted-computing-base.md) · [ADR-0008](./0008-native-sdks-no-litellm.md) · [ADR-0012](./0012-record-replay-determinism.md) · [ADR-0017](./0017-execution-profiles.md) · [DMARTIC Inner Loop](../04-workflows-and-loops/dmartic-inner-loop.md) · [RHI Outer Loop](../04-workflows-and-loops/rhi-outer-loop.md)
