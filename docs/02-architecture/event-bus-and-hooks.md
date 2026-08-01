---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Event Bus & Hook System**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

The event taxonomy and subscriber contract must be clearly specified. The trajectory store, OTel spans, TUI rendering, remote pilot streaming, voice narration, and custom quality gates are **all** consumers of this one mechanism. Specifying it once removes the temptation to bolt each of them onto the kernel directly.

## **One Stream, Many Consumers**

Every state transition in the kernel emits a typed event to an in-process async bus. The kernel itself has no knowledge of who is listening.

```
                       ┌─→ TrajectoryStore   (append-only persistence)
                       ├─→ OTel exporter     (GenAI semantic conventions)
Kernel ──→ EventBus ───┼─→ TUI renderer      (live terminal output)
                       ├─→ SSE/A2A streamer  (remote pilots, bots, IDE)
                       ├─→ TTS narrator      (voice, optional)
                       └─→ User hooks        (lint, secret scan, custom gates)
```

This is why remote piloting, voice, and IDE integration require **zero core changes** — they are subscribers, not features.

## **Event Taxonomy**

All events are frozen Pydantic models carrying `run_id`, `step_id`, `schema_version`, and an aware-UTC
`timestamp`.

> The summary below names the groups. The **normative registry** — payloads, emitters, subscribers, and
> replay-relevance for every event — is the [Event Catalog](../04-workflows-and-loops/event-catalog.md).

### Lifecycle
`RunStarted` · `RunCompleted` · `RunFailed` · `RunCanceled` · `CheckpointCreated`

### Reasoning
`StepStarted` · `ModelCallStarted` · `ModelDelta` (streaming) · `ModelCallCompleted` (carries `TokenUsage`, including cache hit counts) · `StepCompleted`

### Tools
`ToolCallRequested` · `ToolCallAuthorized` · `ToolCallDenied` · `ToolCallCompleted` · `ToolCallFailed`

The split between *requested* and *authorized* is deliberate: it makes the policy decision independently observable, so an audit can answer "what did the agent try to do" separately from "what was it allowed to do."

### Workspace
`EditApplied` (carries `EditResult`) · `CommandExecuted` · `DiagnosticsChanged` · `WorktreeAllocated` · `WorktreeReleased`

### Evaluation & Control
`GateEvaluated` (carries `GateReport`) · `ReviewCompleted` (soft score) · `CandidateProposed` · `CandidateSelected` · `ApprovalRequested` · `ApprovalResolved` · `BudgetWarning` · `BudgetExhausted`

### Steering
`UserMessageReceived` · `TaskRevised`

Mid-run steering appends to the tail and never touches the cache-stable prefix. A goal change produces
a **new `TaskSpec` revision** rather than a mutation, so the trajectory records what the agent was
graded against at each step. Rules in the [Event Catalog](../04-workflows-and-loops/event-catalog.md#steering).

## **Two Subscriber Kinds**

The distinction is the load-bearing part of this design.

### Observers — cannot influence execution

Contract: `Observer` in **`src/sagiha/kernel/bus.py`** (`async def on_event(event) -> None`).

Run **after** the fact, concurrently, with a hard timeout. An observer that raises is logged and disabled for the remainder of the run; it never fails the run. TUI, telemetry, trajectory persistence, and voice narration are all observers.

A slow or broken observer must never be able to break an agent run. That property is why observers cannot return anything.

### Interceptors — can deny, never mutate

Contract: `Interceptor` in **`src/sagiha/kernel/bus.py`** (`async def before(event) -> Decision`).

Run **synchronously** on the critical path at defined hook points, and may return a denial. They may **not** rewrite the event: an interceptor that silently altered a tool call would make the audit log a work of fiction, and the trajectory would no longer reconstruct what actually happened.

Interceptors are timeout-bounded, and a timeout is treated as **deny** — failing closed, consistent with the security posture elsewhere.

## **Hook Points**

> [!NOTE]
> Only `pre_tool` fires today (`kernel/dispatch.py`). The other seven are **reserved** — specified
> here so their name and semantics are fixed before code claims them, not because they are wired.
> `pre_model`/`post_tool` are the natural next additions as the outer loop grows (Sprint 3b/4);
> wiring the rest without a real emitter would be dead configuration surface.

| Hook | Fires | Typical use |
| :--- | :--- | :--- |
| `pre_model` | Before a provider call | Prompt-size guard, cost ceiling |
| `post_model` | After a response | Secret scanning of generated content |
| `pre_tool` | Before dispatch, after policy | Extra org-specific restrictions |
| `post_tool` | After a result, before it enters context | Redaction, output truncation policy |
| `pre_edit` | Before a patch is written | Custom lint, protected-path checks |
| `post_edit` | After a patch lands | Auto-format, incremental re-index |
| `pre_gate` | Before gate evaluation | Additional hard gates |
| `post_run` | On terminal state | Notification, report generation, cleanup |

**`pre_tool` supplements policy; it never replaces it.** The `PolicyEngine` decision and capability grant happen first, inside the dispatch choke point. A hook that could grant permission would reintroduce exactly the bypass the CAR model exists to prevent — hooks may narrow authority, never widen it.

## **Registration**

Hooks are declared in `config.toml` at explicit paths, never discovered by scanning:

```toml
[[hooks]]
event  = "post_edit"
kind   = "observer"
module = "myorg.hooks.autoformat:run"
timeout_ms = 5000
```

Explicit declaration keeps static analysis and "go to definition" working — the same reasoning that rules out a DI container in [Control Plane](../05-tech-stack/control-plane-python.md). It also makes the active hook set auditable from one file rather than inferred from the filesystem.

## **Ordering & Delivery**

* Events are delivered to observers **concurrently**; no ordering guarantee between different observers.
* Each individual observer sees events **in emission order** for a given `run_id`.
* Interceptors at one hook point run **sequentially** in declared order; the first denial short-circuits.
* The bus is in-process and does not persist. Durability is the `TrajectoryStore` observer's job — which is precisely why replay reads from the trajectory rather than from the bus.

## **Backpressure**

Each subscriber has a bounded queue. On overflow, observers **drop and count** (surfacing the drop as a metric) rather than blocking the kernel. Losing narration frames is acceptable; stalling the agent is not.

The `TrajectoryStore` observer is the sole exception: its queue is unbounded and its writes are awaited, because a dropped trajectory event would corrupt replay and audit.

## **Relationship to the Extension System**

Hooks are one of four extension surfaces — alongside adapters, tools, and skills. All four, their
registration mechanism, and their trust levels are specified in
[Extension Model](./extension-model.md).

The invariant that spans all of them: **extension is additive within the hexagon, never a hole through
it.** None may register new ports, reach past a port boundary, or widen authority. For hooks
specifically that means `pre_tool` supplements `PolicyEngine` and never replaces it.
