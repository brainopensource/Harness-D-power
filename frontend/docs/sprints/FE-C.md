---
status: rationale
updated: 2026-07-31
---

# Sprint FE-C — Cockpit + Dual CLI over Mock

**Goal:** Usable coding chat UX (GUI + CLI) on mock transport, patterned after Grok Build / Claude Code flows without forking them.

**Depends on:** FE-B.  
**Unblocks:** FE-D polish surfaces; Wave 1 live swap.

## Tasks

- [ ] **FE-C.1 — GUI Cockpit on RunClient**
  - Rewrite `CockpitDashboard` to use `createEventSource` + `RunClient` + store.
  - Chat composer submits `TaskSpec` (profile `coding`).
  - Controls: run/pause/resume/stop/steer call EventSource verbs.
  - Mount `TaintApprovalModal` on `pendingApproval`.
  - Step/tool/gate/cost feed from folded events.
  - Footer: MOCK/LIVE from transport + health.
  - **Verify:** GUI tests for submit + pause + approval path (mock).

- [ ] **FE-C.2 — CLI binary rename + Commander surface**
  - Primary bin: `sagiha-fe`; keep `sagiha-mock` alias.
  - Commands (headless / Claude-Code-like):
    - `sagiha-fe chat|run [prompt]` — submit + stream summary to stdout
    - `sagiha-fe resume [runId]` / `--continue`
    - `sagiha-fe status` / `history`
    - `sagiha-fe pause|steer|export` (export may print mock path)
  - Shared flags: `--cwd`, `--model` (mock), `--transport`, `--json` / stream-json-ish NDJSON of events.
  - **Verify:** cli tests for `--help`, `run`, `status` under mock.

- [ ] **FE-C.3 — Ink cockpit**
  - `sagiha-fe cockpit` (default interactive): same RunClient as GUI.
  - Keys: P/R pause-resume, S steer prompt, A approve, Q quit (wire to EventSource).
  - Turn status line (tool + timer + tokens) — emulate Grok status bar conceptually.
  - Optional slash stubs: `/pause` `/cost` `/approve`.
  - **Verify:** ink-testing-library smoke for status + key pause.

- [ ] **FE-C.4 — History list (mock)**
  - GUI + CLI `history` show `listRuns()` fixtures; select to re-subscribe.
  - **Verify:** store holds selected runId; subscribeSince smoke test.

- [ ] **FE-C.5 — README refresh**
  - Update `apps/cli/README.md` and `apps/gui/README.md` — remove “FE-1 blank shell” claims; document mock-first + env var.

## Definition of done

- [ ] End-to-end mock: submit goal → steps → taint approval → resume → complete (GUI and CLI).
- [ ] `pnpm --filter @sagiha/gui test` && `pnpm --filter @sagiha/cli test`
- [ ] No YOLO / bypass permission flags introduced
