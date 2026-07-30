---
status: draft
updated: 2026-07-30
---

# **SAGIHA Frontend — Overview**

> [!NOTE]
> This tree (`docs/frontend/`) specifies the **frontend only**: CLI, GUI, their shared design
> system, and the mock data layer that stands in for the real kernel until it exists. It contains
> zero backend implementation detail. Where it must reference a backend contract (an event shape,
> a domain model), it treats that contract as frozen input copied from
> [`docs/02-architecture/`](../02-architecture/) and [`docs/04-workflows-and-loops/event-catalog.md`](../04-workflows-and-loops/event-catalog.md) — never as something the frontend gets to redesign.

## **Why This Exists**

Per [`STATUS.md`](../STATUS.md), Sprint 3a closed the runnable loop against a cassette, but the only
real client today is `sagiha version`. Nobody has looked at what it feels like to *drive* SAGIHA —
watch a plan form, approve a tool call, review a diff, read a failure — because there is no interactive
surface at all. Building the real CLI/GUI against the real kernel, event bus, and adapters at the same
time as figuring out that UX means every UX iteration costs a backend round-trip, and every backend
delay blocks UX validation. The two are on the critical path to each other for no good reason.

This plan decouples them. We build the frontend against **hardcoded, scripted event streams that are
shaped exactly like the real ones**, get the interaction model right — planning, tool-call timelines,
approval gates, diff review, run status, logs, error/degrade states — and only then wire in the real
`Orchestrator.execute()` stream from [Entry Points & Piloting](../02-architecture/entry-points-and-piloting.md).

## **Goals**

1. **Validate the interaction model before it is expensive to change.** Approval gates, diff review,
   and mid-run steering are the highest-risk UX surfaces in an agent harness — get them wrong and users
   stop trusting the tool. Prototype them cheaply, with fake data, before they're load-bearing.
2. **Produce a build-ready spec**, not a moodboard. Every deliverable in this tree should be
   consumable by an engineer (or a coding agent) with zero follow-up questions about stack, structure,
   or data shape.
3. **Mirror the real event/data contracts from day one.** The mock data layer's types are the same
   types the real client will consume — `RunContext`, `TaskSpec`, `ToolCall`, `Decision`, `GateReport`,
   the full event taxonomy. Swapping the mock transport for a real SSE/A2A stream should touch a
   transport adapter and nothing else in the component tree.
4. **Hit a SOTA product bar.** The reference points are Linear, Warp, and Vercel's dashboard — not
   admin-template defaults. Fast, keyboard-first, legible under real information density (a long
   trajectory, a large diff, a stuck run).
5. **Keep CLI and GUI as two cockpits over one design language.** They render the same event stream and
   should feel like the same product, not two unrelated tools that happen to share a name.

## **Explicit Non-Goals**

* **No real backend calls.** No process spawning of a real `sagiha` binary, no real event bus, no real
  `PolicyEngine`, no real model provider. Every event in this phase originates from a scripted fixture
  or a local mock-engine timer, described in
  [`mock-data-and-flows.md`](./mock-data-and-flows.md).
* **No real file I/O against a real workspace.** Diffs, file trees, and command output shown in the
  GUI/CLI are fixture data. Nothing in this phase reads or writes an actual worktree.
* **No real authentication, authorization, or multi-user concerns.** Approval flows are simulated
  locally; there is no real operator identity system yet.
* **No production packaging/distribution pipeline.** Build tooling in
  [`tech-stack.md`](./tech-stack.md) targets local development and internal demos, not signed
  installers or a package registry release — that's a [`roadmap.md`](./roadmap.md) milestone, not a
  Phase 0 deliverable.
* **No IDE (MCP) or remote-pilot (Telegram/Slack) cockpits.** Per
  [Entry Points](../02-architecture/entry-points-and-piloting.md) those are separate, disposable
  services outside this repository. This plan covers the two **in-repo reference clients**: CLI and
  GUI.
* **No redesign of backend contracts.** If a mock flow reveals that an event or domain model is
  awkward for the UI, the finding gets written up for the backend team — the frontend does not fork or
  reinterpret the contract to make its own life easier.

## **Scope**

In scope for the mocked phase, built in the order given in [`roadmap.md`](./roadmap.md):

* A CLI (`sagiha-mock` binary, distinct from the real future `sagiha` CLI during this phase) that
  runs a scripted task end to end: prompt → plan → tool calls (mixed auto-approved and
  gated) → diff review → completion, plus `replay`-style trajectory inspection of a canned run.
* A GUI (desktop app) presenting the same run as a live timeline with a streaming log pane, a tool-call
  inspector, a diff viewer, and an approval modal — built for a run in progress, not just a completed
  one.
* A shared mock data layer (`@sagiha/protocol` + `@sagiha/mock-engine`, see
  [`architecture.md`](./architecture.md)) that both cockpits consume identically.
* A shared design system (`@sagiha/ui` design tokens, and component primitives where CLI/GUI can
  actually share them) so the two cockpits are visibly one product.

Out of scope until a real backend exists: anything in the Non-Goals section above.

## **Definition of Done for This Phase**

The mocked phase is complete when a reviewer can, without touching a terminal command SAGIHA doesn't
yet support:

1. Run the CLI against a scripted task and watch a realistic plan → tool-call → approval → diff →
   completion sequence render with the target visual quality.
2. Trigger an approval gate, see the blocked state communicated clearly, approve or deny it, and see
   the run resume or terminate accordingly.
3. Open the GUI, watch the same kind of run stream live (not a static screenshot), inspect a tool call's
   arguments and result, and review a diff with syntax highlighting and hunk-level detail.
4. Do all of the above with the app closed and reopened mid-run without losing state — because durable,
   resumable state is a first-class property of the real system
   ([Entry Points](../02-architecture/entry-points-and-piloting.md), "Session & Concurrency Model") and
   the mock should not lie about that by being memory-only.
5. Hand the six documents in this tree to a frontend engineer with no other context and have them
   correctly predict what "wire in the real backend" will require changing.
