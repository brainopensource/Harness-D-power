# **Sprint FE-7: Real Transport Integration**

> **Status**: blocked — do not start until its backend dependency below is met
> **Source**: [Frontend Roadmap — Phase 4](../frontend/roadmap.md#phase-4--real-transport-integration-depends-on-backend-sprint-3b-landing)
> **Target**: wire a real `EventSource` implementation against the actual `sagiha` backend, with the
> mocked-phase UI unchanged in visual/interaction contract. This sprint is the payoff of every
> decoupling decision made in FE-1 through FE-6 — if it requires touching feature components, the
> architecture was wrong somewhere upstream and that's a finding, not just a task.

---

## ⛓️ Dependency (blocking — check before opening this sprint)

Per [`STATUS.md`](../STATUS.md), this sprint needs, at minimum:

- [ ] A live/local `ModelProvider` adapter (backend Sprint 3a item B.12) — otherwise there is no real
  agent behavior to stream.
- [ ] `sagiha run`/`sagiha replay` CLI flags actually matching what's implemented (backend D28,
  closed in 3a) — already true as of 3a closure.
- [ ] The SSE/ndjson streaming contract from
  [Entry Points](../02-architecture/entry-points-and-piloting.md) implemented server-side (not
  scoped in 3a/3b as of this writing — confirm against current `STATUS.md` before starting, this
  sprint file will go stale relative to it).

If any of the above is unmet, do not start this sprint speculatively — extend FE-5/FE-6's scenario
breadth instead; there's no shortage of mocked-phase value to add while waiting.

---

## A. Real transport package

- [ ] **1.** `packages/transport-live` — `RealEventSource implements EventSource` over SSE/ndjson,
  parsing each line into a `@sagiha/protocol` event via the existing Zod schemas (this is where
  hand-ported-type drift, if any accumulated, surfaces immediately as validation failures — expect
  and budget time for this).
- [ ] **2.** Implement `subscribeSince` using the real `?since=<step_id>` resumability contract.
- [ ] **3.** Implement `submitTask` and `resolveApproval` against real backend endpoints/CLI
  invocation (exact mechanism depends on whether the backend exposes this over HTTP, a local socket,
  or subprocess stdio — resolve against current backend docs at sprint start, not against this file).
- [ ] **4.** Error handling for real-world transport failures the mock never modeled: malformed
  ndjson line, backend process crash mid-stream, auth/permission errors if any exist by this point.

## B. Runtime switch

- [ ] **5.** GUI: settings toggle (or env var at launch) between `MockEventSource` and
  `RealEventSource`; default determined by team preference (recommend defaulting to mock in dev
  builds, real in any build explicitly pointed at a backend).
- [ ] **6.** CLI: `--transport mock|real` flag (or equivalent), `mock` remaining the default for
  `sagiha-mock` while a separate real-mode entry point may eventually merge into the actual `sagiha`
  CLI per backend ownership — resolve naming/ownership with the backend team before merging, since at
  this point the CLI genuinely could fold into the backend's `sagiha` binary rather than staying a
  separate `sagiha-mock` tool.

## C. Reconciliation

- [ ] **7.** Run the full FE-3/FE-4/FE-5 scenario suite's *visual* assertions against a real backend
  run performing an equivalent task, diffing behavior against the mocked scenarios — any place the
  UI assumed something the real system doesn't guarantee (event ordering, timing, payload shape) gets
  logged as a finding and fixed here, not silently patched over.
- [ ] **8.** Real-world latency handling: verify the "pending" states built in FE-4 (approval,
  submit) actually cover real network/process latency, not just the mock's near-instant round-trip —
  add a minimum-visible-duration or explicit loading state if latency reveals a flash-of-pending-state
  problem.

## D. Retirement, not deletion

- [ ] **9.** `@sagiha/mock-engine` is kept and repurposed: componen t tests continue to use it as
  fixture data; add an explicit "demo mode" (mock transport, clearly labeled in the UI) for
  environments without a live backend.
- [ ] **10.** Update `docs/frontend/architecture.md` and this sprint file's own header once the real
  transport is live, so future readers don't mistake this sprint's plan for the current state.

---

## ✅ Exit test

A real `sagiha run --task "..."` process, driven from either cockpit via `RealEventSource`, renders
identically (modulo real vs. scripted timing) to how the equivalent mocked scenario renders as of
FE-6. No feature component required a code change to accept real data — only `packages/
transport-live` and the runtime switch were added.

## 🚫 Non-goals

Native installer packaging/signing, IDE/remote-pilot cockpits (roadmap Phase 5). Any backend feature
work — this sprint consumes the backend's contracts, it does not extend them.
