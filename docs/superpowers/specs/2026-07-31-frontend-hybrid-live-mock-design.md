---
status: rationale
updated: 2026-07-31
retrieval: excluded
---

# Frontend Hybrid Live/Mock Design — SAGIHA / AETHER

> Approved in design review 2026-07-31. Approach: **Hybrid** (mock-first completeness + `transport-live` stubs + bridge contract). CLI: **dual surface** (Ink cockpit + Claude Code / Grok-style commands) over one `EventSource`.

## Goal

Ship a SOTA Tauri+React GUI and Node dual-surface CLI that can **pilot the harness today on mocks**, and plug into a live Python EventBus bridge later **without rewriting views**. First usable product: coding chat / run / history / gates / cost / taint. AGI surfaces (Story-DAG, memory nets, skills, AETHER swarm, queue) ship as labeled mocks until backend sprints land.

## Non-goals

- Forking `src/grok_build` or `src/claude_code` into the frontend monorepo.
- YOLO / `bypassPermissions` modes that widen authority past `PolicyEngine`.
- Waiting for Conductor / Story-DAG / SSE before building cockpits.
- Replacing the Python `sagiha` CLI as the kernel reference pilot (Node `sagiha-fe` is a parallel cockpit).

## Architecture

```text
GUI (Tauri+React)  ─┐
CLI Ink cockpit    ─┼─► RunClient ─► EventSource ─┬─► MockEventSource (@sagiha/mock-engine)
CLI commands       ─┘                            └─► LiveEventSource (@sagiha/transport-live stub → SSE/IPC)
                         │
                         └─► useHarnessStore (single UI state)
```

### Packages

| Package | Responsibility |
| :--- | :--- |
| `@sagiha/protocol` | Zod domain + full `SagihaEvent` union (mirror `src/sagiha/domain/`); `EventSource`; `RunClient`; Zustand store |
| `@sagiha/mock-engine` | **Only** concrete mock `EventSource` — scripted runs, pause/steer/approve |
| `@sagiha/transport-live` | Stub `LiveEventSource` + env factory; real SSE/IPC in Wave 1 bridge |
| `@sagiha/ui` | Shared atoms/tokens for GUI + Ink adapters |
| `@sagiha/gui` | Tauri v2 shell + React views |
| `@sagiha/cli` | Binary `sagiha-fe` (alias `sagiha-mock`): Ink + Commander commands |

### Invariants

1. Apps **never** import concrete EventSource implementations — only `createEventSource()` from protocol (or a thin factory package).
2. Wire event names match Python literals (`step.completed`, not `StepCompleted`). Code wins: `src/sagiha/domain/events.py`.
3. Hard gates and CAR policy are never overridden in UI. Approvals only call `resolveApproval`.
4. Mock vs live is selected by `SAGIHA_TRANSPORT=mock|live` (default `mock`).
5. Every non-live surface shows an explicit **MOCK** badge or footer label.

## EventSource contract (extended)

Aligned with `frontend/packages/protocol/src/transport.ts` and planned Mode-B pilot verbs:

```ts
interface EventSource {
  submitTask(task: TaskSpec): Promise<{ runId: string }>;
  subscribe(runId: string, onEvent: (e: SagihaEvent) => void): Unsubscribe;
  subscribeSince(runId: string, sinceStepId: string, onEvent: (e: SagihaEvent) => void): Unsubscribe;
  resolveApproval(runId: string, callId: string, approved: boolean, note?: string): Promise<void>;
  // Hybrid extensions (mock now; live when v2-S7 / bridge lands)
  pause(runId: string, reason?: string): Promise<void>;
  resume(runId: string): Promise<void>;
  steer(runId: string, text: string): Promise<void>;
  cancel(runId: string, reason?: string): Promise<void>;
  listRuns?(): Promise<RunSummary[]>;  // history; mock fixture or TrajectoryStore later
}
```

Full wire shapes and resumability: [`frontend/docs/BRIDGE_CONTRACT.md`](../../frontend/docs/BRIDGE_CONTRACT.md).

## Live vs mock matrix

Authoritative matrix: [`frontend/docs/LIVE_VS_MOCK.md`](../../frontend/docs/LIVE_VS_MOCK.md).

**Summary:** coding run telemetry, gates, cost, taint *display*, trajectory list, export/replay become **live after thin bridge**. Pause/steer/approval loop stay **mock until v2-S7**. Story-DAG, AGENTS.md editor, skills, memory graphs, AETHER swarm, queue, behaviours ladder, model/prompt/harness editors stay **mock** until S6/C0+.

## GUI surfaces

| Nav | Behavior |
| :--- | :--- |
| Cockpit | Chat composer + Run/Pause/Resume/Stop/Steer; step/tool/gate feed; spend; taint modal |
| Story-DAG | n8n/ComfyUI-style drag-drop editor over mock Mission/Story fixtures |
| Context | Layers 1–7, compaction from events, AGENTS.md preview (mock file) |
| Memory | Short / long panes (mock graphs) |
| Skills & Behaviours | Skill catalog + profile picker (coding live-shaped; others mock) |
| Models / Prompts / Harness | Tier bindings, spend caps, loop params (mock editors) |
| Code Intel | Mock symbols until Indexer/CodeGraph land |
| Exporter | UI over mock then `sagiha export` / bridge |
| AETHER Swarm | Mock topology until Conductor |

## CLI dual surface (emulate Grok + Claude Code flows, not their stacks)

Binary: **`sagiha-fe`** (keep `sagiha-mock` alias).

| Mode | Pattern borrowed | SAGIHA mapping |
| :--- | :--- | :--- |
| Default / `cockpit` | Grok TUI / Claude REPL | Ink cockpit on `RunClient` |
| `run` / `chat [prompt]` | `claude -p`, `grok -p` | `submitTask` + stream events to stdout |
| `--continue` / `resume` | Grok `-c`/`-r`, Claude `--resume` | `subscribeSince` + thaw |
| `status` / `history` | sessions list | `listRuns` |
| `pause` / `steer` | interrupt + queue | `pause` / `steer` |
| `export` | grok export / sagiha export | mock then live CLI wrap |
| Slash in cockpit | Claude `/` registry | `/pause` `/steer` `/approve` `/model` `/cost` (local) |
| Approvals | sticky permission UX | `approval.requested` → `resolveApproval` |
| Never | `--yolo` / bypassPermissions | Forbidden — PolicyEngine only |

## Sprint waves

Checkbox ledgers live under [`frontend/docs/sprints/`](../../frontend/docs/sprints/):

| Wave | Focus |
| :--- | :--- |
| [FE-A](../../frontend/docs/sprints/FE-A.md) | Protocol truth — Zod parity with `events.py` + domain fields |
| [FE-B](../../frontend/docs/sprints/FE-B.md) | Mock `EventSource` + `transport-live` stubs + factory |
| [FE-C](../../frontend/docs/sprints/FE-C.md) | Cockpit + dual CLI over mock end-to-end |
| [FE-D](../../frontend/docs/sprints/FE-D.md) | DAG / Context / Memory / Skills / Models mock UIs |
| [FE-E](../../frontend/docs/sprints/FE-E.md) | Polish, labeling, verification, Wave-1 bridge checklist |

## Reference implementations (read, don't fork)

- `/home/rock_dev/Code/Harness/src/grok_build` — session resume, turn status, permission queue, streaming-json, slash palette.
- `/home/rock_dev/Code/Harness/src/claude_code` — Commander + Ink dual surface, interrupt+queue, tool-specific approvals, stream-json.
- Backend SoT: `src/sagiha/domain/`, `src/sagiha/ports/`, `docs/implementation/development_plan_v2.md`, `docs/STATUS.md`.

## Success criteria

1. `pnpm typecheck && pnpm lint && pnpm test` green across frontend workspace.
2. GUI and CLI drive the same mock `EventSource`; no direct simulator imports in apps.
3. `transport-live` package builds; selecting `live` fails with a clear “bridge not configured” message until Wave 1.
4. Every view is either event-driven or explicitly **MOCK**-labeled.
5. Docs (`LIVE_VS_MOCK`, `BRIDGE_CONTRACT`, sprint ledgers) match code.

## Out of scope for FE-A…E (deferred to Wave 1 bridge)

- Python SSE/ndjson streamer or Tauri subprocess IPC implementation.
- Real `ModelDelta` streaming from providers.
- Conductor / Story-DAG domain types in Python.
