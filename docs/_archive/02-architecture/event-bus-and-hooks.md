---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Event Bus & Hook System**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**

Kernel state transitions emit typed, immutable events to an in-process async `EventBus`.

```
                       ┌─→ TrajectoryStore   (append-only persistence)
                       ├─→ OTel exporter     (GenAI semantic conventions)
Kernel ──→ EventBus ───┼─→ TUI renderer      (live terminal output)
                       ├─→ SSE/A2A streamer  (remote pilots, bots, IDE)
                       ├─→ TTS narrator      (voice, optional)
                       └─→ User hooks        (lint, secret scan, custom gates)
```

## **Event Taxonomy**

Events are frozen Pydantic models containing `run_id`, `step_id`, `schema_version`, and aware-UTC `timestamp`. Detailed payloads are defined in the [Event Catalog](../04-workflows-and-loops/event-catalog.md).

* **Lifecycle**: `RunStarted`, `RunCompleted`, `RunFailed`, `RunCanceled`, `CheckpointCreated`.
* **Reasoning**: `StepStarted`, `ModelCallStarted`, `ModelDelta`, `ModelCallCompleted` (carries token/cache metrics), `StepCompleted`.
* **Tools**: `ToolCallRequested`, `ToolCallAuthorized`, `ToolCallDenied`, `ToolCallCompleted`, `ToolCallFailed`.
* **Workspace**: `EditApplied`, `CommandExecuted`, `DiagnosticsChanged`, `WorktreeAllocated`, `WorktreeReleased`.
* **Evaluation & Control**: `GateEvaluated`, `ReviewCompleted`, `CandidateProposed`, `CandidateSelected`, `ApprovalRequested`, `ApprovalResolved`, `BudgetWarning`, `BudgetExhausted`.
* **Steering**: `UserMessageReceived`, `TaskRevised`.

## **Subscriber Contracts**

Contracts live in [`src/sagiha/kernel/bus.py`](../../src/sagiha/kernel/bus.py):

### 1. Observers (`async def on_event(event) -> None`)
* Executed concurrently after emission with hard timeouts.
* **Non-blocking**: Errors or timeouts log and disable the observer for the run.
* **Backpressure**: Overflowing queues drop frames and emit metrics (except `TrajectoryStore`, which is unbounded and awaited for durability).

### 2. Interceptors (`async def before(event) -> Decision`)
* Executed sequentially on the critical path before execution.
* **Can deny, never mutate**: Interceptors may deny execution but cannot modify payloads.
* **Fail-closed**: Timeouts trigger an automatic denial (`Decision.deny()`).

## **Hook Points**

> [!NOTE]
> Currently `pre_tool` is active (`kernel/dispatch.py`); other hooks are reserved for upcoming loop milestones.

| Hook | Timing | Purpose |
| :--- | :--- | :--- |
| `pre_model` / `post_model` | Around provider calls | Prompt guards, cost caps, secret redaction |
| `pre_tool` / `post_tool` | Around tool dispatch | Custom policy narrowing, output truncation |
| `pre_edit` / `post_edit` | Around patch application | Linting, auto-formatting, index updates |
| `pre_gate` / `post_run` | Execution boundaries | Custom gate checks, notifications, cleanup |

*Invariant*: `pre_tool` can only narrow permissions; it cannot bypass `PolicyEngine`.

## **Configuration**

Hooks are explicitly declared in `config.toml` (no dynamic scanning):

```toml
[[hooks]]
event = "post_edit"
kind = "observer"
module = "myorg.hooks.autoformat:run"
timeout_ms = 5000
```

## **Cross-References**

* [Extension Model](./extension-model.md)
* [Event Catalog](../04-workflows-and-loops/event-catalog.md)
