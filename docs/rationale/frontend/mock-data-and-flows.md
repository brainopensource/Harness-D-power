---
status: rationale
retrieval: excluded
updated: 2026-07-30
---
# **SAGIHA Frontend — Mock Data & Flows**

This is the concrete build list for `@sagiha/mock-engine`: which scenarios ship, in what order, and
exactly what events each emits. Every payload below uses the real field names from
`src/sagiha/domain/*.py` and `src/sagiha/domain/events.py` — this document is the bridge between the
backend's actual contracts and fixture JSON, so there is no ambiguity for whoever implements the
engine.

## **Engine Shape**

```ts
// packages/mock-engine/src/types.ts
export type ScenarioStep =
  | { at: number; event: SagihaEvent }                 // fixed-delay scripted event
  | { at: number; event: SagihaEvent; awaits: 'approval' } // pauses the timeline until resolveApproval() is called
  | { at: number; streamText: { stepId: string; text: string; tokenDelayMs: [number, number] } }; // expands into BlockStart/BlockDelta*/BlockEnd + ModelDelta events

export interface Scenario {
  id: string;
  title: string;
  description: string;
  seedTask: TaskSpec;
  runContext: RunContext;
  steps: ScenarioStep[];
}
```

`at` is milliseconds from scenario start, purely for pacing realism (default engine speed: 1x real
time; a `--speed` flag/env var multiplies it for demos and for fast test runs). `awaits: 'approval'`
is how the engine models the real system's blocking `approval.requested` semantics — the timeline
genuinely stalls until `EventSource.resolveApproval()` is called, exactly like a real run parked in
`input-required`.

## **Scenario 1 — Golden Path (build first)**

**Goal:** the exact sequence from [`overview.md`](./overview.md)'s Definition of Done: prompt → plan →
tool calls → one gated approval → diff → completion. This is the scenario every other deliverable in
this tree is validated against, and the first thing wired into both CLI and GUI.

Fixture task:

```json
{
  "task_id": "task-001",
  "revision": 0,
  "goal": "Fix the failing test in tests/test_parser.py",
  "acceptance": [
    { "description": "tests/test_parser.py passes", "check": "pytest tests/test_parser.py", "required": true }
  ],
  "profile": "coding",
  "status": "submitted"
}
```

Event sequence (abbreviated; full payloads follow the shapes in `domain/events.py` exactly):

1. `run.started` — `task` (above), `run_context: { run_id, autonomy_level: "hybrid", workspace_root: "mock://repo", budget_remaining_usd: 5.00 }`, `profile: "coding"`, `extension_manifest: []`.
2. `step.started`
3. `model.call_started` — `model: "mock-workhorse-v1"`, simulated `request_digest`.
4. Streamed reasoning + plan text via `streamText` → emits `BlockStart(reasoning)` → `BlockDelta*` (the
   agent's plan, e.g. "I'll look at the failing test, find the parser bug, patch it, and re-run.") →
   `BlockEnd`, each wrapped in `model.delta`.
5. Streamed `tool_use` block: `read_file(path="tests/test_parser.py")` → `BlockEnd(tool_use)`.
6. `model.call_completed` — usage/cost.
7. `tool.call_requested` — `call: { call_id: "call-1", tool_name: "read_file", arguments: {"path": "tests/test_parser.py"}, effect: "pure" }`.
8. `tool.call_authorized` — `decision: { allowed: true, reason: "read-only, within workspace scope", requires_human: false, grant_id: "grant-1" }`.
9. `tool.call_completed` — `call_id: "call-1"`, `result` containing a `TextBlock` with fixture file
   content, `duration_ms: 42`.
10. `step.completed` — assembled `TrajectoryStep`.
11. `step.started` (step 2) → model call → tool call `apply_edit` on `src/parser.py`:
    `effect: "idempotent"`.
12. `tool.call_requested` → `tool.call_authorized` (auto-approved: idempotent + in-scope) →
    `edit.applied` (`EditResult` with one `HunkResult(applied=true, index=0, reason="ok")`) →
    `tool.call_completed`.
13. `step.started` (step 3) → tool call `run_command(argv=["pytest", "tests/test_parser.py"])`,
    `effect: "idempotent"` but classified as **requiring approval** in this scenario specifically to
    exercise the gate (rationale below) → `tool.call_requested` → **`approval.requested`**
    (`action: "run_command"`, `scope: ["tests/test_parser.py"]`, `rationale: "Executing a shell command
    against the workspace"`, `blast_radius: "low — read-only test run, no network"`) → **engine pauses**.
14. User resolves via UI → `EventSource.resolveApproval(runId, "call-3", true)` → `approval.resolved`
    (`approved: true, resolved_by: "operator"`) → `tool.call_authorized` → `command.executed`
    (`argv`, `exit_code: 0`, `output: "1 passed"`) → `tool.call_completed`.
15. `step.completed`.
16. `gate.evaluated` — `GateReport` with the one criterion `passed: true`,
    `no_new_suppressions: true, tests_unmodified: true, coverage_not_decreased: true,
    diff_within_bounds: true` → `admitted: true`.
17. `run.completed` — `gate_report` (above), `cost: { usd: 0.014, input_tokens: 1820, output_tokens: 340, wall_clock_s: 6.2, model_calls: 3 }`.

**Why an idempotent command still gates in this fixture:** it's a deliberate authoring choice to make
sure the golden path exercises the approval UI at least once — real policy configuration is out of
scope for the mock, but the UX for "the agent wants to do something and needs a yes" must not only be
testable via a rare failure scenario.

## **Scenario 2 — Denial**

Same setup, but the `apply_edit` call targets a path outside `scope_paths` (simulating a traversal
attempt or a misconfigured tool). Sequence: `tool.call_requested` → **`tool.call_denied`**
(`decision: { allowed: false, reason: "path outside granted scope", requires_human: false }`,
`reason: "path outside granted scope"`, `requires_human: false`) → the agent's next `step.started`
shows it adapting (re-reasoning text acknowledging the denial) → eventually `run.completed` with a
**partial** `GateReport` (`admitted: false`, one criterion `passed: false`). Validates: denial styling
distinct from failure styling (see [`ui-ux-guidelines.md`](./ui-ux-guidelines.md)), and that a denied
tool call doesn't stall the whole run the way an unresolved approval does.

## **Scenario 3 — Tool Failure & Disposition**

`run_command` executes but exits non-zero and the toolchain adapter raises → `tool.call_failed`
(`error_kind: "subprocess_nonzero_exit"`, `disposition: "RETRY"`) → engine replays a second
`tool.call_requested` for the same logical action (visually: a retry badge on the timeline entry, not a
duplicate entry) → succeeds on retry → continues to completion. A second run of this scenario ends in
`disposition: "ABORT"` after retries are exhausted → `run.failed` (`error_kind`, `disposition: "ABORT"`,
`message`). Validates: `RETRY` renders as transient/recovering, `ABORT` renders as a hard terminal
failure, both visually distinct from a policy `denied` state (Scenario 2) and from a clean `completed`.

## **Scenario 4 — Mid-Run Steering**

After step 1 completes, inject `user.message_received` (`text: "Actually also add a regression test
for this"`, `provenance: "operator"`) → `task.revised` (`task`: new `TaskSpec` with `revision: 1`,
updated `acceptance` tuple with a second criterion, `supersedes: 0`) → the plan/steps view shows the
goal update inline in the timeline (not a silent mutation of the header) and subsequent steps work
against the new acceptance criteria. Validates: the UI's `TaskSpec` display always shows the *latest*
revision, but the trajectory view can still show what each *earlier* step was graded against — this is
the concrete UI test of "the trajectory records what the agent was graded against at each step"
([Event Bus & Hooks](../../02-architecture/event-bus-and-hooks.md)).

## **Scenario 5 — Budget Pressure**

A long-running scenario (many steps, deliberately low `budget_remaining_usd: 0.05` at `run.started`) —
`budget.warning` fires once (`spent_usd`, `remaining_usd`, `projected_usd` showing the trend), then
`budget.exhausted` (`limit_kind: "usd"`) → `run.failed` with `disposition: "SURFACE"` (the budget
governor's failure is not retryable and not silently degraded — it must reach the operator). Validates
the budget meter's escalating visual states end-to-end, not just its static rendering.

## **Scenario 6 — Multi-File Diff Review**

A step whose `apply_edit` spans 4 files, one of which has a `HunkResult(applied=false,
reason="ambiguous_anchor", nearest_match: "...")`. Validates: the file-list-level "not fully applied"
indicator, and that the diff viewer surfaces `nearest_match` as a hint rather than silently showing
nothing for the failed hunk.

## **Scenario 7 — Live Streaming Feel (GUI-focused, performance validation)**

Not a new narrative — replays Scenario 1's model-call text at realistic token cadence
(15-40ms/token, per [`architecture.md`](./architecture.md)) specifically to validate the
`RunClient` batching/coalescing behavior and Ink/React re-render cost under sustained `model.delta`
volume. Used as a manual perf check and as the basis for a Playwright/`ink-testing-library` test that
asserts no dropped frames / no unbounded state growth.

## **Scenario 8 — Reconnect / Resume**

Engine simulates a transport drop mid-run (stops emitting for 3s), then resumes via
`subscribeSince(runId, lastKnownStepId, ...)`, replaying only events after that step. Validates the
"gap, resuming from step N" GUI affordance and the CLI's equivalent status line, matching the real SSE
resumability contract in [Entry Points](../../02-architecture/entry-points-and-piloting.md).

## **Cassette Format for Scenario Authoring**

Scenarios are authored as TypeScript (for `awaits`/branching logic) but each ships a companion
**exported JSON cassette** (`packages/mock-engine/fixtures/*.json`) of the fully-resolved event
sequence for the default (no-branching) path — this doubles as:

* Golden-file fixtures for component/visual tests (render a static, known event list, snapshot the
  output).
* A close visual/structural analogue of the real backend's own cassette format
  ("Digest-keyed cassette replay," per [`STATUS.md`](../../STATUS.md)) — not byte-compatible with it (the
  backend's cassette is a model-response fixture, not a UI event fixture), but similar enough in spirit
  that engineers moving between the two codebases aren't learning a second unrelated fixture idiom.

## **Data Realism Requirements**

* File contents, diffs, and command output in fixtures are **real-looking, non-trivial samples**
  (actual multi-line Python with a genuine off-by-one bug, not `foo()`/`bar()` placeholders) — the UI
  must be validated against content with real line-length and structure variance, not toy strings that
  hide layout problems.
* Timestamps in fixtures are relative to scenario start and rendered as relative time ("2s ago," "just
  now") consistently with how the real system's aware-UTC timestamps would be presented.
* IDs (`run_id`, `step_id`, `call_id`, `grant_id`) follow the real system's apparent format
  conventions (opaque strings, not sequential integers) so nothing in the UI accidentally depends on an
  ID being human-sequential.

## **Build Order**

Scenario 1 ships with the first walking-skeleton milestone in [`roadmap.md`](./roadmap.md). Scenarios
2–4 ship alongside the approval/diff/steering feature work. Scenarios 5–6 validate hardening
(budget, multi-file diffs) once the core loop is solid. Scenarios 7–8 are explicitly performance/
resilience validation, not new feature surface, and are the exit criteria for calling the mocked phase
"done" per [`overview.md`](./overview.md).
