# **Sprint FE-4: Golden Path Part B — Approvals, Diffs & Completion**

> **Status**: not started
> **Source**: [Frontend Roadmap — Phase 2](../frontend/roadmap.md#phase-2--golden-path) (second half)
> **Target**: finish Scenario 1 — the approval gate, diff viewer, `GateReport`, and `run.completed` —
> closing out the plan's Phase 2 exit criterion (Definition of Done items 1–3 in
> [`overview.md`](../frontend/overview.md)).
> **Reads first**: [`mock-data-and-flows.md` — Scenario 1](../frontend/mock-data-and-flows.md#scenario-1--golden-path-build-first)
> steps 13–17; [`ui-ux-guidelines.md`](../frontend/ui-ux-guidelines.md) §"GUI: Approval Gate" and
> §"Diff Viewer (Both)".

---

## A. Protocol growth

- [ ] **1.** Add: `ApprovalRequested`, `ApprovalResolved`, `EditApplied`, `CommandExecuted`,
  `GateEvaluated`, `RunCompleted` events; `EditResult`, `HunkResult`, `GateReport`,
  `CriterionResult`, `CommandResult` domain models — field-exact from `domain/work.py`,
  `domain/content.py`, `domain/events.py`.
- [ ] **2.** Extend `EventSource`'s `resolveApproval` to be exercised for real (previously just an
  interface member): `MockEventSource` must actually pause its internal timeline scheduler on an
  `awaits: 'approval'` step and resume only when called.
- [ ] **3.** Zod fixtures + round-trip tests for the new types.

## B. `RunClient` folding logic

- [ ] **4.** Track pending approvals as a keyed set (`Map<callId, ApprovalRequested>`); removed on
  matching `ApprovalResolved`. Snapshot exposes `pendingApprovals: ApprovalRequested[]`.
- [ ] **5.** Track latest `GateReport` and terminal run status (`completed`/`failed`/`canceled`) from
  `RunCompleted`/`RunFailed`/`RunCanceled`.
- [ ] **6.** Unit test: calling `resolveApproval` before any `ApprovalRequested` exists is a no-op /
  throws clearly (guards against a UI bug sending approvals for the wrong call).

## C. Mock engine: finish Scenario 1

- [ ] **7.** Extend `golden-path.ts` with the `run_command` approval gate (`awaits: 'approval'`),
  its resolution continuation (`command.executed` → `tool.call_completed`), `gate.evaluated`
  (`admitted: true`), and `run.completed`.
- [ ] **8.** Full 17-event JSON cassette fixture exported per
  [`mock-data-and-flows.md`](../frontend/mock-data-and-flows.md#cassette-format-for-scenario-authoring).

## D. `approvals` feature area

- [ ] **9.** GUI: `AlertDialog`-based approval modal (Radix), non-dismissible by click-outside,
  showing blast_radius → rationale → scope → Approve/Deny, per the guideline's fixed ordering.
  Wired to `resolveApproval` — **no optimistic UI**; button shows a pending spinner until
  `ApprovalResolved` actually arrives back through `RunClient`.
- [ ] **10.** CLI: blocking terminal prompt rendering the same information hierarchy, requiring
  explicit `y`/`n` (no bare `Enter`).
- [ ] **11.** Native OS notification (Tauri) fired when `ApprovalRequested` arrives and the window is
  unfocused.

## E. `diff-and-gates` feature area

- [ ] **12.** GUI: Monaco-based unified diff viewer (side-by-side toggle) rendering `EditResult`
  hunks, with hunk-level status badges (`ok`/`anchor_not_found`/etc.) matching `HunkResult.reason`
  exactly.
- [ ] **13.** CLI: terminal diff rendering (unified only) with syntax highlighting and the same
  hunk-status badges rendered inline.
- [ ] **14.** `GateReport` summary component (both apps): per-criterion pass/fail, the four coding
  gates, and the overall `admitted` verdict rendered prominently at run completion.
- [ ] **15.** Run-completion state (both apps): terminal "completed" banner with cost summary
  (`CostSummary`) and a link/action back to the full trajectory.

## F. Tests

- [ ] **16.** Component tests: approval modal keyboard-only flow (focus trap, `Enter` submits,
  `Escape` does not silently approve), diff viewer with the full hunk-status matrix, gate-report
  pass and fail renderings.
- [ ] **17.** Integration test (Playwright for GUI, Ink scripted-input harness for CLI): drive the
  full golden-path scenario from `submitTask` through `resolveApproval` to `run.completed` and assert
  the final on-screen state.

---

## ✅ Exit test

Matches [`overview.md`](../frontend/overview.md) Definition of Done items 1–3: a reviewer runs the
CLI against the golden-path scenario, is prompted for the approval, approves it, and sees the diff and
completion; the same flow works in the GUI including the modal and native notification. No part of
the approval flow updates its own UI ahead of the corresponding event actually arriving through
`RunClient`.

## 🚫 Non-goals

Denial/failure/steering/budget/multi-file-diff scenarios (FE-5). Persisted history, reconnect,
accessibility/perf hardening (FE-6).

## ⛓️ Dependency

FE-3 merged (shares the same scenario file and timeline components).
