---
status: rationale
updated: 2026-07-31
---

# Sprint FE-A — Protocol Truth

**Goal:** Make `@sagiha/protocol` field-compatible with `src/sagiha/domain/` so mock and live share one Zod bus.

**Depends on:** Design approved.  
**Unblocks:** FE-B.

## Tasks

- [ ] **FE-A.1 — Event union parity**
  - Mirror all event discriminators from `src/sagiha/domain/events.py` in `packages/protocol/src/events.ts`.
  - Minimum for tests: lifecycle, step/model/tool, compaction, gate, taint, budget, approval, user.
  - Delete / stop using PascalCase `HarnessEvent` names in protocol.
  - **Verify:** `pnpm --filter @sagiha/protocol test` — parse fixtures for each v1 event.

- [ ] **FE-A.2 — Domain field parity**
  - Align `RunContext`, `TaskSpec`, `GateReport`, `TokenUsage`, `CostSummary`, `FrozenRunState`, `TrajectoryStep` with Python (snake_case JSON).
  - Fix known drifts (`base_commit`, token field names).
  - **Verify:** golden JSON fixtures copied from Python `model_dump(mode="json")` round-trip.

- [ ] **FE-A.3 — Extend EventSource types**
  - Add `pause`, `resume`, `steer`, `cancel`, optional `listRuns` to `transport.ts`.
  - Document in JSDoc pointing at `frontend/docs/BRIDGE_CONTRACT.md`.
  - **Verify:** typecheck passes; no app compiles against old simulator types.

- [ ] **FE-A.4 — RunClient fold skeleton**
  - Expand `run-client.ts` to fold v1 events into store-facing snapshots (status, steps, gates, cost, pendingApproval, tainted).
  - Unit tests with synthetic event sequences.
  - **Verify:** `pnpm --filter @sagiha/protocol test`.

- [ ] **FE-A.5 — Docs sync**
  - Ensure `LIVE_VS_MOCK.md` / design link from `packages/protocol` README if present.
  - Note FE-A completion in `frontend/docs/README.md` status column.

## Definition of done

- [ ] `pnpm --filter @sagiha/protocol typecheck`
- [ ] `pnpm --filter @sagiha/protocol test`
- [ ] No remaining app dependency on PascalCase mock event types in protocol exports
