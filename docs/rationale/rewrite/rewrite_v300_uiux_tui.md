---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — UI, TUI and the Wire Protocol

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Satisfies **D-10** of the [Phase-0 charter](../reference/PLANNING.md) and the RFP's request for a
front-end / TUI plan. Closes **Q4**.

---

## 0. Position

**The engine is headless. Every surface is a client of one typed event stream.** The TUI, the CLI, the
GUI, an IDE extension, and CI all consume the same protocol; none has a privileged path.

This is not a UI preference — it is what keeps the protocol honest. The moment the CLI can do
something the protocol cannot express, the protocol stops describing the system and the second client
becomes a rewrite. SAGIHA demonstrates the cost: `cli.py` is 805 lines, the largest file in the tree,
because command definitions, composition wiring, and output formatting grew together in the only
surface that existed.

**A TUI is not a nicety here — it is an instrument.** E2E comparison against Hermes, OpenCode and
Claude Code requires driving all four the same way and watching what they do. Without a usable
surface, every comparison is mediated by log files, which is slow enough that in practice it does not
happen.

---

## 1. What already exists

`frontend/` is a working pnpm + turbo monorepo, and it is a genuine asset:

| Path | Contents |
| :--- | :--- |
| `frontend/apps/gui` | Tauri desktop shell (Rust host + web UI) |
| `frontend/apps/cli` | TypeScript CLI |
| `frontend/packages/protocol` | Zod schemas for event frames |
| `frontend/packages/mock-engine` | Deterministic fake engine — the frontend develops without a backend |
| `frontend/packages/ui`, `config` | Shared components and config |
| CI | `frontend-ci.yml`, path-filtered, `turbo lint typecheck test build` |

Two documents carry decisions worth keeping:

- **`docs/frontend/docs/BRIDGE_CONTRACT.md`** already fixes the frame format: newline-delimited JSON,
  one `Event` object per line, `event` as the discriminator, **snake_case field names matching
  Python**, ISO-8601 UTC timestamps, unknown event types logged and ignored for forward compatibility.
  That is the right shape and it survives.
- **`docs/frontend/docs/LIVE_VS_MOCK.md`** is a per-feature matrix tagging every surface `LIVE`,
  `MOCK`, `HYBRID`, or `BRIDGE`, with the standing rule *"update this file whenever a mock surface
  flips to live."*

That second document is the honesty doctrine applied to the UI, and it is the single most valuable
thing in the frontend tree. A UI that renders plausible output from a mock engine is exactly the class
of instrument that produces confident, wrong impressions — the same failure as a gate hardcoded to
`True`, one layer up. **The matrix carries over unchanged, and no surface may claim `LIVE` without a
backing capability in `src/aether/`.**

---

## 2. Transport

The bridge contract left the carrier open (SSE/NDJSON HTTP, Tauri IPC, or both) with one frame format
regardless. That separation is right; the carrier choice can now be made.

| Leg | Carrier | Why |
| :--- | :--- | :--- |
| **Interactive clients** (TUI, GUI, IDE) | **WebSocket**, JSON frames | Bidirectional. Required for the `ask` permission round-trip, interrupts, and mid-run steering — all of which are inputs, not just outputs |
| **Headless consumers** (CI, logs, piping) | **NDJSON over HTTP** — `POST /v1/runs`, `GET /v1/runs/{id}/events?since=` | Unidirectional is sufficient; trivially `curl`-able and `jq`-able |
| **Desktop** | Tauri IPC over the same frames | Optional shortcut; identical payloads |

One schema, three carriers. **TypeScript types are generated from the schema**, never hand-written —
`packages/protocol`'s Zod schemas become generated artifacts with a CI drift check, matching the
existing `gen_event_catalog.py --check` discipline on the Python side.

**Why bidirectional matters more here than in a chat product.** The permission model is three-valued —
`allow` / `ask` / `deny` (see [security §1.4](./rewrite_v300_seguranca_sandbox.md)). `ask` is the
state that makes an autonomous agent usable rather than merely safe, and it is a *blocking round
trip*: the engine pauses, the human decides, the engine resumes. A unidirectional event stream plus a
side-channel POST can express this, but the sequencing and reconnection semantics get fragile fast.
WebSocket makes it a message.

### Reconnection

Long-horizon runs outlive UI sessions by design — the whole point of
[hibernation](./rewrite_v300_autonomia_agi.md) is that a run survives its client. So the protocol
requires, from day one:

- Every event carries a monotonic id; `?since=` replays from any point.
- The event log is the durable record; the stream is a view over it.
- Reconnect = fetch history since the last seen id, dedupe by id, then tail live.
- The engine never blocks on a client. A disconnected UI is not a paused run.

---

## 3. The TUI

### Recommendation: Python, Textual, in-repo

| Option | Assessment |
| :--- | :--- |
| **Textual (Python)** | **Chosen.** No second toolchain in Phase 1, ships with the engine, one `uv run` to a working surface, and a rich widget set. Consistent with [A-002](./rewrite_v300_decisoes_adr.md) |
| Bubbletea (Go) | Excellent TUIs — OpenCode's is the reference — but adds a language and a build step to reach the first E2E comparison |
| Ink (TypeScript) | Reuses `frontend/`, but couples the primary developer surface to the Node toolchain |

The deciding factor is Phase-1 velocity toward measurement, not long-run TUI quality. The TUI exists
to make the engine drivable and comparable; whichever language reaches that first wins, and the
protocol boundary means replacing it later costs nothing structural.

### Progression

| Stage | Capability | Lands |
| :--- | :--- | :--- |
| **MVP** | Task input; scrolling event log; tool calls with args and results; final gate verdict; cost and token counters | M1a |
| **S1** | Token-level streaming; live thinking indicator; interrupt | M1a–M1b (streaming is required by [A-011](./rewrite_v300_decisoes_adr.md)) |
| **S2** | Syntax-highlighted diff review; **`ask` approval prompts**; per-tool permission display | M2 |
| **S3** | Parallel candidate view — N worktrees side by side with gate status; retrieval inspector (which files entered context, and why) | M2–M3 |
| **S4** | Session browser over the trajectory store; replay a past run frame by frame | M3 |
| **S5** | Mission dashboard — multiple concurrent runs, budget, hibernation state | M3–M4 |

**S3's retrieval inspector is the highest-value debugging surface in the list.** Per
[context & memory §0](./rewrite_v300_contexto_memoria.md), localization dominates resolve rate — an
agent that edits the wrong file perfectly scores zero. "Which five files did it pick, and why" is the
question most worth being able to answer in one keystroke, and it is nearly free given that retrieval
decisions are already events.

### Observability the TUI must surface

Because these are the numbers that catch silent regressions:

- **Cache hit rate**, live. A cache regression produces no test failure and no behavioral change —
  only cost. Visible in the header, floored in CI.
- **Cost and wall-clock**, running, per step and per run.
- **Trust provenance** on every tool result — trusted vs. untrusted content, visually distinct. If the
  human cannot see what the agent considers untrusted, they cannot review the taint decisions.
- **Gate state**, tri-state — `pass` / `fail` / **`not measured`**. `None` renders as its own state,
  never as a green check.

That last one is the honesty doctrine reaching the pixel layer. A UI that renders "not measured" as a
pass is the same bug as a gate hardcoded to `True`, and it is more persuasive because it is visual.

---

## 4. The GUI

Attaches later against the same frozen protocol, and adds only what a terminal genuinely cannot do:
multi-pane diff review, a rendered code-graph view, long-run timelines, artifact previews.

`frontend/apps/gui` (Tauri) is already scaffolded and stays. It ships when the protocol is ratified
and the TUI has proven the interaction model — not before, because a GUI built against an unratified
protocol becomes an argument for freezing the protocol early.

---

## 5. The CLI

Thin. A command layer over the engine API plus a frame renderer.

```
aether run <task>              # stream to terminal
aether run <task> --json       # NDJSON to stdout
aether bench --suite <id>      # measurement entry point
aether replay verify --cassette <path>
aether resume <run-id>         # thaw a frozen run
```

**The CLI is a client, not a privileged path.** Anything it can do, the protocol exposes. This is the
direct fix for SAGIHA's 805-line `cli.py`, and it is checked structurally: the CLI package may import
the engine API and the protocol, and nothing else.

---

## 6. Summary

| Decision | Choice | Reversal |
| :--- | :--- | :--- |
| Architecture | Headless engine; every surface a protocol client | — |
| Frame format | JSON objects, `event` discriminator, snake_case, ISO-8601 UTC, unknown events ignored | — |
| Interactive carrier | WebSocket (bidirectional — `ask`, interrupt, steering) | — |
| Headless carrier | NDJSON over HTTP with `?since=` replay | — |
| TS types | Generated from schema, CI drift check | — |
| Reconnection | Monotonic ids; durable log; dedupe-and-tail; engine never blocks on a client | — |
| TUI | **Textual (Python), in-repo** | A second toolchain becomes justified on its own merits |
| GUI | Tauri, after protocol ratification | Customer requirement for GUI-first |
| CLI | Thin client; no privileged path | — |
| LIVE/MOCK matrix | **Carried over.** No surface claims `LIVE` without a backing capability | — |
