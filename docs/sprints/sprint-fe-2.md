# **Sprint FE-2: Walking Skeleton — One Event, From Mock to Pixels**

> **Status**: doing (protocol types + RunClient scaffolded; mock-engine + GUI/CLI wiring pending)
> **Source**: [Frontend Roadmap — Phase 1](../frontend/roadmap.md#phase-1--walking-skeleton)
> **Target**: prove the transport seam (`EventSource` → `RunClient` → both cockpits) end to end with
> a single hardcoded event, before any real feature is built on top of it. If this seam is wrong,
> every later sprint inherits the mistake.
> **Reads first**: [`docs/frontend/architecture.md`](../frontend/architecture.md) §"The Transport
> Seam" and §"`RunClient`: The Shared State Machine".

---

## A. Protocol types (minimum viable slice)

- [ ] **1.** In `packages/protocol/src/domain.ts`: port `TaskSpec`, `AcceptanceCriterion`,
  `RunContext` from `src/sagiha/domain/{work,control}.py` as Zod schemas + inferred TS types. Field
  names and optionality must match the Python models exactly (this is the contract this whole plan
  is built on — no renaming for "nicer" TS casing).
- [ ] **2.** In `packages/protocol/src/events.ts`: port the `Event` base fields (`event`,
  `schema_version`, `run_id`, `step_id`, `timestamp`) and exactly one concrete event, `RunStarted`,
  as a discriminated union member on `event: "run.started"`.
- [ ] **3.** `packages/protocol/src/transport.ts`: the `EventSource` interface from
  [`architecture.md`](../frontend/architecture.md) (`subscribe`, `submitTask`, `resolveApproval`,
  `subscribeSince`) — implemented by nothing yet, just the interface + `Unsubscribe` type.
- [ ] **4.** Unit test: a hand-built `RunStarted` object validates against the Zod schema; a payload
  with a wrong field name fails validation. This is the test that proves "shape drift is caught at
  build time," the load-bearing promise of the whole mock layer.

## B. `RunClient`

- [ ] **5.** `packages/protocol/src/run-client.ts`: `RunClient` class taking an `EventSource`,
  exposing `getSnapshot()` and `subscribe(listener)`. For this sprint, snapshot is just
  `{ task: TaskSpec | null, runContext: RunContext | null, connectionStatus: 'idle'|'connected' }`,
  updated only by `RunStarted`.
- [ ] **6.** Unit test: constructing a `RunClient` with a fake `EventSource` that emits one
  `RunStarted`, asserting the snapshot updates and the subscriber fires exactly once.

## C. Mock engine (minimum)

- [ ] **7.** `packages/mock-engine/src/hello-scenario.ts`: one hardcoded scenario emitting a single
  `RunStarted` after a fixed delay.
- [ ] **8.** `packages/mock-engine/src/mock-event-source.ts`: `MockEventSource implements
  EventSource`, driving the hello scenario's timeline on `subscribe()`.

## D. GUI wiring

- [ ] **9.** `apps/gui`: a `RunClientProvider` (React context) instantiating `RunClient` with
  `MockEventSource`, wrapping the app.
- [ ] **10.** Replace the blank shell's "SAGIHA" text with the run header rendering
  `task.goal` and `runContext.autonomy_level` once `RunStarted` arrives (show a loading state before
  it does).

## E. CLI wiring

- [ ] **11.** `apps/cli`: `sagiha-mock run --scenario hello` command mounts an Ink `<RunView/>` that
  subscribes to the same `RunClient`/`MockEventSource` pairing and prints the goal once available.

---

## ✅ Exit test

Running `sagiha-mock run --scenario hello` in the CLI and opening the GUI (pointed at the same
scenario id via a dev toggle) both display the identical `TaskSpec.goal` string, sourced from the
same `RunStarted` event, through the same `@sagiha/protocol` types. Deleting `MockEventSource` and
substituting any other `EventSource` implementation (verified with a second fake in the test suite)
requires no change to `RunClientProvider`, `<RunView/>`, or the GUI header component — only to the
one line that constructs the transport.

## 🚫 Non-goals

Any event beyond `RunStarted`. Any UI beyond the run header. Approval, tool-call, or diff rendering
(FE-3/FE-4). Persisted history or reconnect (FE-6).

## ⛓️ Dependency

FE-1 (scaffold) must be merged. Nothing else.
