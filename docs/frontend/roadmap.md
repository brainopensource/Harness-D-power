---
status: draft
updated: 2026-07-30
---

# **SAGIHA Frontend — Roadmap**

Milestones are ordered by dependency, not by calendar. Each has an explicit exit criterion so "done" is
checkable, not a feeling. Phases 0–2 are the mocked phase this plan covers in detail; Phase 3 onward
depends on backend work tracked in [`STATUS.md`](../STATUS.md) and is sketched here only to show where
the seams built in Phases 0–2 get used.

## **Phase 0 — Scaffold**

Set up the monorepo so every later phase is additive, not restructuring.

* pnpm + Turborepo workspace; `packages/protocol`, `packages/mock-engine`, `packages/ui`,
  `packages/config`, `apps/cli`, `apps/gui` created per [`architecture.md`](./architecture.md)'s
  folder layout.
* `@sagiha/protocol`: hand-port the domain models actually needed for Scenario 1
  (`TaskSpec`, `RunContext`, `Decision`, `ToolCall`, `ToolResult`, `GateReport`, `TrajectoryStep`, and
  the `Event` union subset it uses) into TS + Zod. Not the full model surface yet — grow it
  scenario-by-scenario so nothing is speculative.
* `@sagiha/ui`: token file (`tokens.css`, `tokens.ts`) from [`ui-ux-guidelines.md`](./ui-ux-guidelines.md),
  no components yet.
* CI: lint + typecheck + `vitest` wired via Turborepo, green on an empty scaffold.

**Exit:** `pnpm install && pnpm build && pnpm test` succeeds with placeholder apps that render "hello."

## **Phase 1 — Walking Skeleton**

Get one event, from mock engine to pixels, in both cockpits — proves the transport seam before
building any real feature surface on top of it.

* `EventSource` interface + `MockEventSource` implementing it against a single hardcoded event.
* `RunClient` folding logic for `run.started` only.
* GUI: renders the run header (goal, autonomy badge) from that one event.
* CLI: `sagiha-mock run --scenario hello` prints the equivalent via Ink.

**Exit:** both apps show the same `TaskSpec.goal` sourced from the same mock event, proving the shared
package boundary works end to end.

## **Phase 2 — Golden Path**

The core deliverable of this entire plan.

* Full Scenario 1 (golden path) implemented in `@sagiha/mock-engine`.
* `plan-and-steps`, `tool-calls`, `approvals`, `diff-and-gates` feature areas built for both apps per
  [`architecture.md`](./architecture.md).
* Streaming text rendering with the coalescing/backpressure handling specified there.
* Approval modal (GUI) and blocking prompt (CLI) fully interactive — real `resolveApproval()`
  round-trip, no optimistic UI.
* Diff viewer (Monaco for GUI, terminal syntax highlighting for CLI) rendering `EditResult` hunks.
* Design tokens fully applied — this is the first milestone that should visually pass the "does this
  look like Linear/Warp/Vercel, not an admin template" bar, not just function correctly.

**Exit:** [`overview.md`](./overview.md)'s "Definition of Done for This Phase" items 1–3 are met, using
Scenario 1.

## **Phase 3 — Resilience & Breadth**

Everything in [`mock-data-and-flows.md`](./mock-data-and-flows.md) beyond the golden path, plus the
durability property called out in the overview's Definition of Done item 4.

* Scenarios 2–6 (denial, failure/disposition, steering, budget, multi-file diff) implemented and
  reachable via a dev-mode scenario picker.
* Local persisted run history (client/app state per [`architecture.md`](./architecture.md)) so closing
  and reopening either app mid-run resumes from the last known state via `subscribeSince`.
* Scenario 8 (reconnect/resume) validated against real app restarts, not just the mock engine's
  simulated drop.
* Accessibility pass against [`ui-ux-guidelines.md`](./ui-ux-guidelines.md) (keyboard nav audit,
  screen-reader smoke test on the GUI, `NO_COLOR`/ASCII-fallback verification on the CLI).
* Performance validation via Scenario 7 — no dropped frames, bounded memory, at sustained
  `model.delta` volume over a long run.

**Exit:** [`overview.md`](./overview.md)'s full Definition of Done is met. This is the "hand it to a
reviewer" milestone — the mocked phase is feature-complete and demo-ready.

## **Phase 4 — Real Transport Integration (depends on backend Sprint 3b+ landing)**

This is where the decoupling this plan insisted on gets cashed in. Per [`STATUS.md`](../STATUS.md),
the backend needs a live/local model provider adapter, `sagiha run`/`replay` CLI flags actually wired,
and the SSE/A2A streaming contract implemented before this phase can start — none of that is frontend
work, and this phase should not start speculatively ahead of it.

* `packages/transport-live`: `RealEventSource implements EventSource` over SSE/ndjson, matching the
  "Streaming Contract" in [Entry Points](../02-architecture/entry-points-and-piloting.md) (resumable
  via `?since=`, redacted at the boundary already handled server-side, backpressure-safe).
* Runtime toggle between `MockEventSource` and `RealEventSource` (env var for CLI, settings toggle for
  GUI) — both apps keep working with mock data throughout this phase; the real transport is additive.
* Reconcile any event/type drift discovered between `@sagiha/protocol`'s hand-ported types and the
  actual wire payloads — expected to be small if [`mock-data-and-flows.md`](./mock-data-and-flows.md)
  was followed faithfully, but this is explicitly budgeted time, not assumed to be zero.
* Wire `submitTask`/`resolveApproval` to real backend calls; remove the mock-only assumption that
  approval resolution is instantaneous — add real network-latency handling (the pending-state UI from
  Phase 2 already exists for exactly this reason).
* `@sagiha/mock-engine` is **not removed** — demoted to the fixture/test/offline-demo role described in
  [`architecture.md`](./architecture.md).

**Exit:** a real `sagiha run --task "..."` process, driven from either cockpit, renders identically to
how the equivalent mock scenario renders today — the visual/interaction contract does not change
between mock and real data.

## **Phase 5 — Additional Cockpits & Packaging**

Only once Phase 4 is stable:

* CLI: real dependency-free binary packaging (`pkg`/`nexe` or a Bun-compiled binary) for distribution
  outside the monorepo's dev environment.
* GUI: signed installers (macOS notarization, Windows code signing) via `tauri-apps/tauri-action` CI
  pipeline.
* IDE (MCP) and remote-pilot cockpits remain explicitly out of this repository's frontend scope per
  [Entry Points](../02-architecture/entry-points-and-piloting.md) — if/when built, they are separate
  projects that also implement `EventSource`-equivalent logic against the same backend contracts, not
  something added to `apps/`.

**Exit:** not blocking for this plan — tracked here only so Phase 4's seam is known to generalize
before it's relied on.

## **Explicit Non-Milestones**

Not planned at any phase as part of this frontend track — call these out if anyone asks "when do we
get X":

* Multi-tenant/multi-user auth UI — no operator identity system exists yet on the backend to build
  against.
* A plugin/extension UI for the [Extension Model](../02-architecture/extension-model.md) — extensions
  are registered via `pyproject.toml` entry points on the backend, not a GUI concern in the current
  design.
* Mobile apps — no cockpit for SAGIHA is planned to be a phone-first surface; remote piloting (Telegram/
  Slack/etc.) already covers "check on a run from my phone" without needing a native mobile app.
