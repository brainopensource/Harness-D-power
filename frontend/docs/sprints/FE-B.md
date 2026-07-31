---
status: rationale
updated: 2026-07-31
---

# Sprint FE-B — Mock EventSource + transport-live stubs

**Goal:** One factory, two implementations; apps never import simulators directly.

**Depends on:** FE-A.  
**Unblocks:** FE-C.

## Tasks

- [ ] **FE-B.1 — MockEventSource implements EventSource**
  - Refactor `packages/mock-engine` so `MockEventSource` is the public API.
  - Emit real `SagihaEvent` names (`step.completed`, …).
  - Implement `submitTask`, subscribe, subscribeSince, pause/resume/steer/cancel, resolveApproval, listRuns (fixtures).
  - Scripted scenarios: `coding-happy`, `taint-approval`, `budget-freeze`, `gate-fail`.
  - **Verify:** mock-engine tests drive EventSource, not raw ticker helpers alone.

- [ ] **FE-B.2 — Wire mock → RunClient → store**
  - Ensure store updates only via RunClient (or documented single path).
  - Pause stops emission; resume continues; steer appends `user.message_received`; approval unblocks scenario.
  - **Verify:** integration test mock → client → store.

- [ ] **FE-B.3 — Scaffold `@sagiha/transport-live`**
  - New package: `LiveEventSource` stub throwing clear bridge-not-configured error.
  - Optional `health()` → `{ ok: false }`.
  - Add to pnpm workspace + turbo pipeline.
  - **Verify:** package typechecks; import from factory works.

- [ ] **FE-B.4 — `createEventSource()` factory**
  - Env `SAGIHA_TRANSPORT=mock|live` (default mock).
  - Export from protocol or `@sagiha/transport` re-exporting both impls without apps knowing packages.
  - Ban direct `@sagiha/mock-engine` imports in `apps/*` (lint rule or codemod + CI grep).
  - **Verify:** grep apps for mock-engine imports = empty.

- [ ] **FE-B.5 — Bridge checklist doc**
  - Confirm `BRIDGE_CONTRACT.md` matches implemented interface.
  - Add “Wave 1 bridge TODO” section linking STATUS / v2-S7.

## Definition of done

- [ ] `pnpm --filter @sagiha/mock-engine test`
- [ ] `pnpm --filter @sagiha/transport-live typecheck`
- [ ] Apps compile using factory only
