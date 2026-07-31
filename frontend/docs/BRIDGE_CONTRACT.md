---
status: rationale
updated: 2026-07-31
retrieval: excluded
---

# Bridge Contract — Frontend ↔ SAGIHA Kernel

> Contract for Wave 1 `transport-live` so FE-A…E can finish without waiting on the Python SSE pilot.
> Design: `docs/superpowers/specs/2026-07-31-frontend-hybrid-live-mock-design.md`.

## Purpose

The headless kernel already exposes:

```text
TaskSpec + RunContext  →  Orchestrator / RunLoop  →  AsyncIterator[Event]  (EventBus)
```

Pilots today are CLI-only (`src/sagiha/cli.py`). The frontend assumes an `EventSource` that is a **thin remoting** of that loop — not a second chat API.

## Transport choices (Wave 1 pick one)

| Option | Shape | When |
| :--- | :--- | :--- |
| **A. SSE / NDJSON HTTP** (preferred for multi-client) | `POST /runs` + `GET /runs/{id}/events?since=` | Matches `entry-points-and-piloting.md` |
| **B. Tauri IPC → subprocess** | Spawn `sagiha` / embedded runner; pipe NDJSON on stdout | Fastest for Linux desktop |
| **C. Both** | Same NDJSON event frames; different carriers | Ideal end state |

Frontend `LiveEventSource` must speak **one frame format** regardless of carrier.

## Frame format

Newline-delimited JSON. Each line is one `Event` object as serialized by Pydantic (`event` discriminator).

```json
{"event":"run.started","schema_version":1,"run_id":"…","timestamp":"…","task":{…},"run_context":{…},"profile":"coding","extension_manifest":[]}
{"event":"step.started","schema_version":1,"run_id":"…","step_id":{…},"timestamp":"…"}
{"event":"step.completed","schema_version":1,"run_id":"…","step_id":{…},"timestamp":"…","step":{…}}
```

- Timestamps: ISO-8601 UTC.
- Field names: **snake_case**, matching Python.
- Unknown `event` values: log + ignore (forward compatible).
- Zod schemas in `@sagiha/protocol` must accept the Python payloads (loose extras ok via `.passthrough()` only on envelope if needed; prefer exact).

## HTTP sketch (Option A)

```http
POST /v1/runs
Content-Type: application/json

{ "task": { …TaskSpec… }, "context": { …RunContext… } }

→ 200 { "run_id": "…" }

GET /v1/runs/{run_id}/events?since={step_id}
Accept: text/event-stream
→ SSE: data: {event…}\n\n
   or NDJSON body

POST /v1/runs/{run_id}/approvals
{ "call_id": "…", "approved": true, "note": null }

POST /v1/runs/{run_id}/pause
{ "reason": "interrupt" }

POST /v1/runs/{run_id}/resume
{}

POST /v1/runs/{run_id}/steer
{ "text": "…" }

POST /v1/runs/{run_id}/cancel
{ "reason": "user" }

GET /v1/runs
→ [{ "run_id", "status", "started_at", "profile", "title" }]
```

Redaction, auth, and backpressure are backend concerns; UI must tolerate disconnect + `subscribeSince` replay.

## Event catalog (must mirror)

Authoritative list: `src/sagiha/domain/events.py` (generated catalog: `docs/04-workflows-and-loops/event-catalog.md`).

| Group | Events |
| :--- | :--- |
| Lifecycle | `run.started`, `run.completed`, `run.failed`, `run.canceled`, `checkpoint.created` |
| Reasoning | `step.started`, `model.call_started`, `model.delta`, `model.call_completed`, `step.completed`, `step.scored` |
| Tools | `tool.call_requested`, `tool.call_authorized`, `tool.call_denied`, `tool.call_completed`, `tool.call_failed`, `tool.taint_introduced` |
| Context | `context.compaction_applied`, `model.provider_failover` |
| Workspace | `edit.applied`, `command.executed`, `diagnostics.changed`, `worktree.allocated`, `worktree.released`, `index.updated` |
| Gates | `gate.evaluated`, `review.completed`, `candidate.proposed`, `candidate.selected` |
| Approval | `approval.requested`, `approval.resolved` |
| Budget | `budget.warning`, `budget.exhausted` |
| User | `user.message_received`, `task.revised` |
| Bench/Replay | `benchmark.task_harvested`, `benchmark.task_completed`, `replay.verified` |

**Cockpit v1 minimum fold set:** lifecycle + step/model/tool + compaction + gate + taint + budget + approval + user.

## Control verb semantics

| Verb | Mock behavior | Live behavior (target) |
| :--- | :--- | :--- |
| `submitTask` | Start scripted scenario; emit `run.started` | `build_kernel` + `RunLoop` |
| `subscribe` / `subscribeSince` | Replay buffer from mock bus | Bus / SSE with `since` |
| `pause` | Stop ticker; emit freeze-shaped status | `FrozenRunState(reason=interrupt)` |
| `resume` | Restart ticker | Thaw / `--resume` |
| `steer` | Emit `user.message_received`; inject into next mock step text | Tail-append / `TaskRevised` @ v2-S7 |
| `resolveApproval` | Emit `approval.resolved`; continue or deny branch | Unblock dispatch when ApprovalRequested wired |
| `cancel` | Emit `run.canceled`; stop | Cancel run |
| `listRuns` | Fixture sessions | TrajectoryStore |

## Package stub (`@sagiha/transport-live`)

Until the bridge exists:

```ts
export class LiveEventSource implements EventSource {
  constructor(_opts?: { baseUrl?: string }) {
    throw new Error(
      "SAGIHA_TRANSPORT=live but transport-live bridge is not configured. " +
        "See frontend/docs/BRIDGE_CONTRACT.md. Use SAGIHA_TRANSPORT=mock.",
    );
  }
  // …methods throw same error
}
```

Factory (in protocol or small `@sagiha/transport`):

```ts
export function createEventSource(): EventSource {
  const mode = process.env.SAGIHA_TRANSPORT ?? "mock";
  if (mode === "live") return new LiveEventSource();
  return new MockEventSource();
}
```

## Health check

`LiveEventSource.health(): Promise<{ ok: boolean; detail: string }>` — GUI footer shows LIVE only if `ok`. Stub returns `{ ok: false, detail: "bridge not configured" }`.

## Security

- Never send Grant tokens or raw secrets to the UI.
- Streamer redacts untrusted payloads per policy before leaving the TCB.
- UI must not offer a permission bypass mode.
- Path/file handles never cross the wire — only serializable domain models.

## Acceptance for “bridge ready”

- [ ] Python or Tauri carrier emits NDJSON frames matching Zod parsers for the v1 fold set.
- [ ] `subscribeSince` resumes without duplicate destructive side effects (replay rules).
- [ ] GUI Cockpit and `sagiha-fe run` work with `SAGIHA_TRANSPORT=live` against a local harness.
- [ ] Approvals round-trip when backend emits `approval.requested` (else remain mock).
