---
status: rationale
retrieval: excluded
---
# **Sprint FE-6: Durability, Reconnect, Performance & Accessibility**

> **Status**: not started
> **Source**: [Frontend Roadmap — Phase 3](../frontend/roadmap.md#phase-3--resilience--breadth)
> (second half)
> **Target**: close out the mocked phase entirely. This is the "hand it to a reviewer" sprint —
> after this lands, [`overview.md`](../frontend/overview.md)'s full Definition of Done is met and
> the frontend is demo-ready without a real backend.

---

## A. Persisted run history (client/app state)

- [ ] **1.** GUI: local persisted store (Tauri store plugin) recording each mock run's id, scenario,
  goal, terminal status, and timestamp; a history list view (sidebar or dedicated route).
- [ ] **2.** CLI: equivalent local history file under `~/.config/sagiha-mock/history.json` (or
  platform-appropriate config dir via a small helper — do not hand-roll XDG logic if a maintained
  tiny package exists).
- [ ] **3.** Reopening either app shows prior runs' terminal state without re-running the scenario.

## B. Scenario 8 — Reconnect / resume

- [ ] **4.** Mock engine: simulate a transport drop (stop emitting for N seconds mid-scenario), then
  support `subscribeSince(runId, lastStepId, ...)` replaying only subsequent events.
- [ ] **5.** `RunClient`: on detecting a gap (an `onError`/disconnect signal from `EventSource`),
  expose a `connectionStatus: 'reconnecting'` state; on resume, expose the resumed-from step id.
- [ ] **6.** UI: a visible "reconnecting… resuming from step N" affordance in both cockpits — not a
  silent freeze, not a full-page error.
- [ ] **7.** Test: closing and relaunching either app mid-run (real app restart, not just the mock's
  simulated drop) resumes from persisted history + `subscribeSince`, per Definition of Done item 4.

## C. Scenario 7 — Streaming performance validation

- [ ] **8.** Automated perf check: replay the golden-path scenario's streamed text at realistic
  token cadence under a profiling harness; assert bounded re-render count and no unbounded memory
  growth over a run with a few hundred trajectory steps (synthetic long scenario, not just Scenario 1's
  short one — extend the mock engine with a generator-based "long run" scenario for this purpose).
- [ ] **9.** Fix any drops/perf regressions found — this item is explicitly allowed to grow scope; do
  not merge a perf finding without addressing it.

## D. Accessibility pass

- [ ] **10.** Keyboard-navigation audit (GUI): every interactive element reachable via `Tab`, visible
  focus ring, approval modal focus-trap verified with an automated test (`@testing-library/user-event`
  tab-order assertions), not just manual QA.
- [ ] **11.** Screen-reader smoke test (GUI): `aria-live="polite"` regions for streaming/status,
  `aria-live="assertive"` for `ApprovalRequested`/`RunFailed` only — verify with a screen-reader
  testing tool or manual VoiceOver/NVDA pass, documented in the PR.
- [ ] **12.** Contrast audit: automated check (e.g. `axe-core` in the Playwright suite) against both
  themes, gating on WCAG AA.
- [ ] **13.** `prefers-reduced-motion` respected: automated test forcing the media query and asserting
  animation durations collapse per the guideline.
- [ ] **14.** CLI: verify `NO_COLOR` env var and non-UTF8-locale ASCII fallback both actually work
  (not just documented) — a scripted test forcing `TERM=dumb`/`NO_COLOR=1` and asserting readable
  plain output.

## E. Command palette & keyboard shortcuts polish

- [ ] **15.** GUI: `Cmd/Ctrl+K` command palette wired to run switching, scenario switching (dev),
  theme toggle, approval-queue focus — per [`ui-ux-guidelines.md`](../frontend/ui-ux-guidelines.md)
  §"Interaction Patterns".
- [ ] **16.** Both apps: a `?`-triggered (CLI) / palette-listed (GUI) help overlay documenting the
  full keybinding set.

---

## ✅ Exit test

[`overview.md`](../frontend/overview.md)'s full Definition of Done, items 1–5, all pass:
golden-path run, approval gate, live GUI streaming with diff review, restart-mid-run durability, and
a fresh reviewer (or agent) correctly predicting the real-transport integration surface from reading
this doc tree alone. This sprint's completion is the "mocked phase done" milestone — tag it as such.

## 🚫 Non-goals

Any real transport code (FE-7). Native packaging/installers/signing (post-FE-7, per roadmap Phase 5).

## ⛓️ Dependency

FE-5 merged.
