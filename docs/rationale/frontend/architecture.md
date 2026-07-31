---
status: rationale
retrieval: excluded
updated: 2026-07-30
---
# **SAGIHA Frontend — Architecture**

## **The One Rule Everything Else Follows**

Both cockpits are pure functions of an event stream, exactly as
[Entry Points & Piloting](../../02-architecture/entry-points-and-piloting.md) specifies for the real
system: `TaskSpec` goes in, `AsyncIterator[Event]` comes out, every rendering surface is a subscriber.
During the mocked phase, the only thing that differs from the target architecture is **what produces
the stream** — a local, scripted `mock-engine` instead of a real kernel over SSE. Every layer above the
transport is written as if the transport were already real, because it will be swapped, not rewritten.

```
                    ┌────────────────────────────────────────────┐
                    │              @sagiha/protocol                │
                    │   TS types + Zod schemas mirroring the       │
                    │   backend's domain models & Event union      │
                    └───────────────────┬──────────────────────────┘
                                         │ imported by
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
   ┌──────────▼─────────┐   ┌────────────▼───────────┐   ┌──────────▼─────────┐
   │  @sagiha/mock-engine │   │   (future) transport    │   │     @sagiha/ui       │
   │  fake event producer │   │   real SSE/A2A client   │   │  design tokens +      │
   │                      │   │   (Phase 2, roadmap.md) │   │  React primitives     │
   └──────────┬───────────┘   └────────────┬────────────┘   └──────────┬─────────┘
              │                            │                           │
              └─────────────┬──────────────┘                           │
                             │ EventSource interface (see below)        │
              ┌──────────────▼──────────────┐                          │
              │        RunClient             │◄─────────────────────────┘
              │  (transport-agnostic facade) │
              └──────────────┬───────────────┘
                              │
              ┌───────────────┼───────────────┐
              │                               │
     ┌────────▼─────────┐           ┌─────────▼──────────┐
     │   apps/cli (Ink)   │           │   apps/gui (Tauri)   │
     │  Observer-style     │           │  Zustand store +      │
     │  components read     │           │  React components     │
     │  from RunClient       │           │  read from RunClient   │
     └────────────────────┘           └───────────────────────┘
```

## **The Transport Seam: `EventSource`**

The single interface that makes "swap mock for real" a one-file change:

```ts
// packages/protocol/src/transport.ts
export interface EventSource {
  /** Subscribe to a run's event stream. Mirrors Orchestrator.execute()'s AsyncIterator<Event>. */
  subscribe(runId: string, onEvent: (event: SagihaEvent) => void): Unsubscribe;

  /** Submit a new task. Mirrors the TaskSpec-in side of the headless entry point. */
  submitTask(task: TaskSpec): Promise<{ runId: string }>;

  /** Resolve a pending ApprovalRequested. Mirrors the CLI's rendering of that event as a decision. */
  resolveApproval(runId: string, callId: string, approved: boolean, note?: string): Promise<void>;

  /** Resume from a step (mirrors SSE `?since=<step_id>` resumability). */
  subscribeSince(runId: string, sinceStepId: string, onEvent: (event: SagihaEvent) => void): Unsubscribe;
}
```

* `@sagiha/mock-engine` implements `EventSource` by replaying/generating scripted events on a timer.
* The future real transport implements the same interface over SSE/ndjson, per the "Streaming Contract"
  section of [Entry Points](../../02-architecture/entry-points-and-piloting.md) (resumable, redacted at
  the boundary, backpressure-safe).
* **No component in `apps/cli` or `apps/gui` imports `@sagiha/mock-engine` directly.** They depend
  only on `EventSource` and a `RunClient` built on top of it. This is the mechanical enforcement of
  "swapping the backend touches a transport adapter and nothing else" — the same discipline the backend
  applies to its own ports.

## **`RunClient`: The Shared State Machine**

`RunClient` is a small, framework-agnostic class (used by both Ink and React) that:

1. Takes an `EventSource`.
2. Folds the incoming event stream into a normalized, queryable snapshot: current `RunContext`,
   current `TaskSpec` (latest revision), the ordered list of `TrajectoryStep`s so far, the set of
   pending `ApprovalRequested`s, the latest `GateReport`, cost/budget totals, and connection status.
3. Exposes that snapshot via a subscribe-to-changes API (a plain pub-sub — deliberately not
   framework-specific), which:
   * On the GUI side, a thin Zustand store wraps and re-exposes as hooks (`useRun()`,
     `usePendingApprovals()`, `useTrajectory()`).
   * On the CLI side, an Ink context provider wraps it and re-renders subscribed components on change.

This mirrors the backend's own separation: the `EventBus` doesn't know about the `TrajectoryStore` or
the TUI — they're both observers folding the same stream into their own shape. `RunClient` is our
frontend's `TrajectoryStore`-equivalent: the one place that turns "a stream of events" into "the current
state of the world."

**Why fold events into a snapshot rather than let every component read raw events:** components should
answer "what is true right now" (is there a pending approval, what's the last diff), not "replay every
event since the beginning." The event log itself remains available (for the trajectory/log view) as an
ordered array in the same snapshot — nothing is discarded, but the common case (render current state)
doesn't require every consumer to reduce the stream itself.

## **State Boundaries**

Three distinct kinds of state, kept in three distinct places — conflating them is the most common
source of unnecessary re-renders and stale-UI bugs in event-driven UIs:

| Kind | Examples | Owned by |
| :--- | :--- | :--- |
| **Server/run state** (derived entirely from the event stream, never locally mutated) | `RunContext`, `TrajectoryStep[]`, `GateReport`, pending approvals, cost totals | `RunClient` snapshot |
| **UI state** (exists only in this cockpit, never persisted, resets on reload) | Which timeline row is expanded, active tab in the tool-call inspector, diff view mode (inline/side-by-side), command palette open/closed | Zustand slice (GUI) / local Ink component state (CLI) |
| **Client/app state** (persisted locally, survives restarts, not part of any run) | Recent run history, theme preference, keyboard-shortcut customizations, window size/position | Tauri's local store plugin (GUI) / a dotfile under `~/.config/sagiha-mock/` (CLI) |

Run state is **never** locally mutated optimistically — e.g., clicking "Approve" does not flip the UI
to an approved state until `ApprovalResolved` actually arrives back through the stream (from the mock
engine, immediately; from the real backend, after the kernel processes it). This is deliberate: the
real system's approval is authoritative server-side state ("the run parks in `input-required` and waits
independent of which cockpit is attached," per Entry Points), and building the mock UI to depend on
that round-trip now means the real integration doesn't introduce a new "wait, why does the button feel
different now" regression.

## **Component Architecture**

Both apps organize around the same five feature areas, named after the events they render — reinforcing
that the UI is a projection of the event taxonomy, not an independently-invented information
architecture:

```
features/
  run-header/        RunContext, TaskSpec (goal, acceptance), autonomy level, budget meter
  plan-and-steps/     StepStarted → StepCompleted timeline, ModelDelta streaming text, reasoning blocks
  tool-calls/         ToolCallRequested → Authorized/Denied → Completed/Failed, per-call inspector
  approvals/          ApprovalRequested modal/prompt, blast-radius + rationale display, resolve action
  diff-and-gates/     EditApplied hunks, diff viewer, GateEvaluated / GateReport, criteria pass/fail
  run-log/            CommandExecuted output, DiagnosticsChanged, raw event log (debug view)
```

Each feature area is a package-internal module (not a separate pnpm package — these are app-specific
compositions of `@sagiha/ui` primitives) exporting:

* One or more **presentational components** (pure, given a slice of `RunClient` snapshot as props —
  identical props shape intended for both CLI and GUI implementations of the same feature, even though
  the rendering technology differs).
* A **selector hook** (`useToolCalls()`, `usePlan()`, etc.) that reads from `RunClient` and returns
  exactly the slice that feature needs, memoized, so a `model.delta` update doesn't re-render the
  approvals panel.

### GUI Layout (Tauri/React)

```
apps/gui/src/
  main.tsx                 Tauri entry, mounts <App/>
  App.tsx                  Top-level layout: sidebar (run history) + main pane (active run)
  routes/
    run/[runId].tsx         The primary view: header + plan/steps + tool-calls + diff, tabbed or split
    history.tsx              List of past mock runs (from local persisted history)
    settings.tsx              Theme, keyboard shortcuts, mock-scenario picker (dev-only)
  features/                 (as above)
  components/               Shared layout chrome: Sidebar, CommandPalette, Titlebar
  state/
    run-client-provider.tsx  Instantiates RunClient with the active EventSource, provides via context
    ui-store.ts               Zustand store for UI state
  lib/
    mock-scenarios.ts         Registry of named mock-engine scenarios selectable in dev/demo mode
```

### CLI Layout (Ink)

```
apps/cli/src/
  cli.tsx                   Entry, argument parsing (commander), dispatches to a command
  commands/
    run.tsx                  `sagiha-mock run --scenario <name>` — mounts <RunView/> full-screen
    replay.tsx                `sagiha-mock replay <run-id>` — non-interactive, renders a completed trajectory and exits
    trajectory-show.tsx        `sagiha-mock trajectory show <id>` — static detail view
  features/                 (as above, Ink components instead of DOM)
  state/
    run-client-context.tsx   React context wrapping RunClient, Ink-compatible
  ink-components/            Low-level reusable primitives: <Spinner/>, <ProgressBar/>, <DiffBlock/>, <Badge/>
```

### Shared

```
packages/
  protocol/         @sagiha/protocol — types, Zod schemas, EventSource interface, RunClient class
  mock-engine/       @sagiha/mock-engine — scenario scripts, event scheduler, fixtures
  ui/               @sagiha/ui — design tokens (packages/ui/tokens.css, tokens.ts), React primitives
  config/           @sagiha/config — shared tsconfig/biome configs
```

## **The Mock Data Layer, and How It Retires**

`@sagiha/mock-engine` is built as a small state machine per scenario:

```ts
type Scenario = {
  id: string;
  seedTask: TaskSpec;
  // A scripted list of (event, delayMs) pairs, OR a generator function for
  // scenarios that branch based on simulated approval decisions.
  timeline: ScenarioStep[];
};
```

It never talks to `@sagiha/protocol`'s types loosely — every emitted event is constructed through the
Zod schemas, so a scenario author gets a compile-time and runtime guarantee that mock data has the
exact shape real data will have. This is the single most important discipline in this plan: **if it's
easy to accidentally hand-wave a mock event's shape, the "minimal changes later" promise is void.**

Retirement path (detailed in [`roadmap.md`](./roadmap.md)):

1. A `RealTransport implements EventSource` package is added (`packages/transport-live/`), talking SSE
   to the actual `sagiha` process.
2. Apps gain a runtime switch (env var / CLI flag / settings toggle) between `MockEventSource` and
   `RealEventSource`.
3. `@sagiha/mock-engine` is **kept**, not deleted — it becomes the fixture layer for component tests
   and Storybook-equivalent visual review, and the offline demo mode. Mock data has permanent value
   beyond this phase; only its role as "the only data source" retires.

## **Streaming Performance Considerations**

`model.delta` is explicitly the high-volume, drop-tolerant event
([Event Bus & Hooks](../../02-architecture/event-bus-and-hooks.md): "the one high-volume event and the
only one observers are permitted to drop under backpressure"). The frontend honors that from the start:

* The mock engine simulates realistic delta cadence (token-by-token, ~15-40ms apart) rather than
  emitting full text blocks, so the streaming-text rendering path is exercised the same way it will be
  against a real model.
* `RunClient` coalesces rapid `model.delta` updates into a single state notification per animation
  frame (via `requestAnimationFrame`/microtask batching), never one React state update per token — this
  is the frontend's own backpressure handling, independent of whatever the transport does.
* Only the actively-focused step's delta text triggers a re-render; completed steps render their final
  `StepCompleted.step` payload once and freeze.

## **Error, Denial, and Degraded States**

Every screen has a defined appearance for the states the real system explicitly names — these are
first-class mock scenarios, not afterthoughts bolted on once the happy path works:

* `ToolCallDenied` (policy refused) — visually distinct from `ToolCallFailed` (it ran and errored):
  denial is a security-relevant "the system worked as intended," failure is "something broke."
* `RunFailed` with each `Disposition` (`RETRY`, `DEGRADE`, `SURFACE`, `ABORT`) rendered differently —
  a `RETRY` shows a transient/recovering state, `ABORT` shows a terminal failure.
* `BudgetWarning` → `BudgetExhausted` as a visible, escalating budget meter, not just a final error.
* Connection loss to the event source (mock: simulated disconnect scenario; real: actual SSE drop) —
  shows a reconnecting state and, on the GUI, a "there's a gap, resuming from step N" affordance
  matching the real `?since=<step_id>` resumability contract.

## **Cross-References**

* [`tech-stack.md`](./tech-stack.md) — libraries and versions referenced above.
* [`mock-data-and-flows.md`](./mock-data-and-flows.md) — the concrete scenarios `@sagiha/mock-engine`
  ships with, and their exact event sequences.
* [`ui-ux-guidelines.md`](./ui-ux-guidelines.md) — the design tokens and interaction patterns consumed
  by `@sagiha/ui`.
* [`roadmap.md`](./roadmap.md) — the milestone sequence for retiring the mock transport.
