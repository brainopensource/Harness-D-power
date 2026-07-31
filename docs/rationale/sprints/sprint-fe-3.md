---
status: rationale
retrieval: excluded
---
# **Sprint FE-3: Golden Path Part A — Plan, Steps & Tool-Call Timeline**

> **Status**: not started
> **Source**: [Frontend Roadmap — Phase 2](../frontend/roadmap.md#phase-2--golden-path) (first half)
> **Target**: Scenario 1 (golden path) up through its first two steps — reasoning/plan streaming and
> an auto-approved tool call — rendered in both cockpits. Approval gates and diffs are deliberately
> deferred to FE-4 so this sprint stays reviewable and testable on its own.
> **Reads first**: [`mock-data-and-flows.md` — Scenario 1](../frontend/mock-data-and-flows.md#scenario-1--golden-path-build-first)
> steps 1–12 only (stop before the approval gate); [`architecture.md`](../frontend/architecture.md)
> §"Streaming Performance Considerations".

---

## A. Protocol growth

- [ ] **1.** Add to `packages/protocol`: `ToolCall`, `ToolResult`, `EffectClass`, `Decision`,
  `TrajectoryStep`, `ReasoningBlock`/`TextBlock`/`ToolUseBlock` content blocks, `TokenUsage`,
  `CostSummary`, and the `StreamEvent` union (`BlockStart`/`BlockDelta`/`BlockEnd`/`UsageReported`/
  `StreamEnd`) — all from `domain/content.py` and `domain/trajectory.py`, field-exact.
- [ ] **2.** Add events: `StepStarted`, `ModelCallStarted`, `ModelDelta`, `ModelCallCompleted`,
  `StepCompleted`, `ToolCallRequested`, `ToolCallAuthorized`, `ToolCallCompleted`.
- [ ] **3.** Zod round-trip tests for every new type against a hand-built fixture matching the
  Scenario 1 payloads in `mock-data-and-flows.md`.

## B. `RunClient` folding logic

- [ ] **4.** Extend `RunClient` to fold `StepStarted`→...→`StepCompleted` into an ordered
  `TrajectoryStep[]`, and to track "current in-flight step" separately (its reasoning/tool-call state
  before `StepCompleted` arrives) from the frozen completed list.
- [ ] **5.** `ModelDelta` coalescing: batch same-step deltas into one state notification per animation
  frame (`requestAnimationFrame` on GUI; an equivalent throttled scheduler on the Ink/CLI side —
  Node has no rAF, use a fixed ~16ms interval timer). Unit test: 200 rapid deltas produce far fewer
  than 200 subscriber notifications.
- [ ] **6.** Unit test: a full step's `ToolCallRequested`→`ToolCallAuthorized`→`ToolCallCompleted`
  sequence resolves into one timeline entry with the right final status, not three separate rows.

## C. Mock engine: Scenario 1, part 1

- [ ] **7.** `packages/mock-engine/src/scenarios/golden-path.ts` — steps 1 through 12 of Scenario 1
  (through the `apply_edit` auto-approval), using the `ScenarioStep`/`streamText` shape from
  [`mock-data-and-flows.md`](../frontend/mock-data-and-flows.md#engine-shape). Stop before the
  `run_command` approval gate — that continuation is FE-4's job, and the scenario file should be
  extended there, not rewritten.
- [ ] **8.** Exported JSON cassette fixture for this partial sequence, used by component tests below.

## D. `plan-and-steps` and `tool-calls` feature areas

- [ ] **9.** GUI: timeline component listing steps, each showing status icon + one-line summary;
  selecting a step reveals its reasoning text (streaming, with block cursor while in-flight) and its
  tool calls.
- [ ] **10.** GUI: tool-call detail pane — name, arguments (pretty-printed), effect-class badge,
  result content, duration — per the "Tool-Call Timeline Entry" pattern in
  [`ui-ux-guidelines.md`](../frontend/ui-ux-guidelines.md).
- [ ] **11.** CLI: equivalent Ink timeline (`j`/`k` navigation, `Enter` to expand/collapse) and
  tool-call detail rendering, reusing `@sagiha/ui` tokens for color/hierarchy.
- [ ] **12.** Design-token application check: run the FE-1 swatch comparison against the actual
  rendered timeline — this is the first real content this bar gets judged against, not swatches.

## E. Tests

- [ ] **13.** Component tests (`vitest` + Testing Library for GUI, `ink-testing-library` for CLI)
  snapshotting: empty state (before `RunStarted`), mid-step streaming state, and the fully-resolved
  12-event fixture from item 8.
- [ ] **14.** Performance smoke: replay the golden-path partial scenario at 1x speed under
  `vitest`'s fake timers or a real timer run, assert no unbounded re-render count (a regression guard
  for item 5).

---

## ✅ Exit test

Running the CLI against the `golden-path` scenario (truncated form) and opening the equivalent GUI
view show: the goal, two completed steps with correct reasoning text, a `read_file` tool call and an
`apply_edit` tool call both rendered with correct effect-class badges and results, and the timeline
navigable via keyboard in both apps. Visual review against Linear/Warp/Vercel bar passes (subjective
gate — a second person reviews before merge).

## 🚫 Non-goals

Approval gates, diff viewing, `GateReport`/`run.completed` rendering (FE-4). Denial/failure/steering/
budget scenarios (FE-5). Persisted history (FE-6).

## ⛓️ Dependency

FE-2 (walking skeleton) merged.
