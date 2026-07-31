---
status: rationale
retrieval: excluded
---
# **Sprint FE-5: Scenario Breadth — Denial, Failure, Steering, Budget, Multi-File Diffs**

> **Status**: not started
> **Source**: [Frontend Roadmap — Phase 3](../frontend/roadmap.md#phase-3--resilience--breadth)
> (first half)
> **Target**: implement Scenarios 2–6 from
> [`mock-data-and-flows.md`](../frontend/mock-data-and-flows.md) and the dev-mode scenario picker
> that makes them all reachable without editing code. This sprint is where the UI proves it
> distinguishes "the system refused" from "the system broke" from "the system succeeded" — the
> single most important trust signal in an agent product.

---

## A. Scenario picker (build first — everything else needs it)

- [ ] **1.** `packages/mock-engine/src/registry.ts` — a named registry of scenarios
  (`{ id, title, description, build(): Scenario }`).
- [ ] **2.** GUI: dev-mode command-palette entry / settings-page dropdown to switch active scenario
  and restart the run, visually marked as a dev affordance (per the "never lies about what's real"
  principle in [`ui-ux-guidelines.md`](../frontend/ui-ux-guidelines.md)).
- [ ] **3.** CLI: `sagiha-mock run --scenario <id>` accepts any registered id; `sagiha-mock
  scenarios list` prints the registry.

## B. Scenario 2 — Denial

- [ ] **4.** Protocol: add `ToolCallDenied` event (already partially covered by `Decision`; add the
  `requires_human` field usage).
- [ ] **5.** Mock engine scenario per spec.
- [ ] **6.** UI: denial rendering visually distinct from failure — a dedicated status icon/color
  (`--sg-danger` but with a "denied" glyph, not the "failed" glyph) in both cockpits' timeline and
  detail pane, showing `Decision.reason` verbatim.
- [ ] **7.** Test: denial does not stall the run (next step still proceeds), unlike a pending
  approval.

## C. Scenario 3 — Tool failure & disposition

- [ ] **8.** Protocol: add `ToolCallFailed`, `RunFailed`, `Disposition` union.
- [ ] **9.** Mock engine: both the retry-then-succeed branch and the retry-exhausted-then-abort
  branch (two invocations of the same scenario id with a seeded variant, or two scenario ids —
  team's call, document the choice).
- [ ] **10.** UI: retry badge on a timeline entry (visually "the same logical action, attempt 2"),
  and a hard terminal failure banner for `ABORT` distinct from both `completed` and `denied` styling.

## D. Scenario 4 — Mid-run steering

- [ ] **11.** Protocol: add `UserMessageReceived`, `TaskRevised`.
- [ ] **12.** `RunClient`: track `TaskSpec` revisions, exposing both "current/latest" and, per
  historical step, "which revision it was graded against" (requires each folded `TrajectoryStep` to
  carry or be joinable to the task revision active when it ran).
- [ ] **13.** UI: an inline timeline marker for the goal change (not a silent header mutation), and
  the run header always showing the latest revision's goal/acceptance.
- [ ] **14.** A way to actually **trigger** steering as a user action in this mock (a text input in
  both cockpits that calls a mock-only "inject `UserMessageReceived`" method) — this is explicitly a
  mock-phase affordance since real submission goes through `EventSource`, not a special method; keep
  it isolated so it's obvious what disappears in FE-7.

## E. Scenario 5 — Budget pressure

- [ ] **15.** Protocol: add `BudgetWarning`, `BudgetExhausted`.
- [ ] **16.** UI: a budget meter component (both apps) with three visual states — normal, warning
  (amber, per token table), exhausted (red, terminal) — driven by `RunContext.budget_remaining_usd`
  and the two new events.
- [ ] **17.** Confirm `RunFailed(disposition="SURFACE")` renders distinctly from `ABORT` (Scenario 3)
  and from a clean `denied` state — three different terminal-ish states must read as three different
  things at a glance.

## F. Scenario 6 — Multi-file diff review

- [ ] **18.** Extend the diff-and-gates feature area (built in FE-4) to a file list view when
  `EditResult` spans multiple files, with a per-file "fully applied / partially applied" indicator
  driven by whether every `HunkResult.applied` is true.
- [ ] **19.** Verify `nearest_match` renders as an inline hint on a failed hunk rather than an empty
  diff region.

## G. Tests

- [ ] **20.** One component/integration test per scenario (5 total) asserting the distinguishing
  visual state described above — these are the regression guards that keep "denied looks different
  from failed looks different from succeeded" true as the UI evolves.

---

## ✅ Exit test

All five scenarios are reachable via the picker in both cockpits without a code change. A reviewer
can run each in sequence and correctly name, from the UI alone with no narration, which of
{denied, failed-retrying, failed-aborted, steered, budget-exhausted} they're looking at.

## 🚫 Non-goals

Reconnect/resume (Scenario 8), sustained-streaming performance validation (Scenario 7),
accessibility audit, persisted run history — all FE-6.

## ⛓️ Dependency

FE-4 merged (reuses timeline, tool-call, and diff-and-gates components).
