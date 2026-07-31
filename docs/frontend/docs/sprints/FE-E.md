---
status: rationale
updated: 2026-07-31
---

# Sprint FE-E — Polish, Verification, Bridge Readiness

**Goal:** Monorepo green; honest labeling; Wave 1 bridge can plug without view rewrites.

**Depends on:** FE-A…D.  
**Unblocks:** Wave 1 backend SSE/IPC implementation.

## Tasks

- [ ] **FE-E.1 — LIVE/MOCK chrome everywhere**
  - MainLayout footer driven by transport mode + `health()`.
  - Per-view badges match `LIVE_VS_MOCK.md`.
  - CLI status prefix `[mock]` / `[live]`.
  - **Verify:** snapshot/unit on footer states.

- [ ] **FE-E.2 — Performance pass**
  - Code-split heavy DAG / swarm views.
  - Cap event buffer in store; virtualize long step lists if needed.
  - **Verify:** build size note in gui README (no hard ceiling yet).

- [ ] **FE-E.3 — Tauri shell hygiene**
  - Window title, basic IPC stub for future live path (`invoke` placeholder documented).
  - Icons/README accurate.
  - **Verify:** `cargo check` in `apps/gui/src-tauri` if toolchain present.

- [ ] **FE-E.4 — Full monorepo verification**
  - `pnpm typecheck && pnpm lint && pnpm test && pnpm build`
  - Fix all failures.
  - Update sprint index statuses to done.

- [ ] **FE-E.5 — Wave 1 bridge checklist (docs only)**
  - In `BRIDGE_CONTRACT.md`, mark acceptance items still open.
  - File backend follow-up note under `docs/implementation/` or link STATUS: “FE EventSource ready; need SSE/IPC pilot”.
  - Confirm `frontend_prompt_detailed_todo.md` points at FE-A…E as active ledger.

- [ ] **FE-E.6 — Reference UX audit**
  - Checklist vs Grok/Claude patterns we chose to emulate:
    - [ ] resume/continue
    - [ ] stream/status line
    - [ ] approval sticky flow
    - [ ] dual surface (REPL + print)
    - [ ] no permission bypass
  - Document gaps as FE-F+ backlog (optional file `frontend/docs/sprints/BACKLOG.md`).

## Definition of done

- [ ] All FE-A…E task boxes checked
- [ ] `LIVE_VS_MOCK.md` matches shipped UI
- [ ] Selecting `SAGIHA_TRANSPORT=live` fails loudly and safely
- [ ] Selecting `mock` runs full demo path GUI + CLI
