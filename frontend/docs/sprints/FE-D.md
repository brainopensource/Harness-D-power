---
status: rationale
updated: 2026-07-31
---

# Sprint FE-D — Advanced Mock Surfaces (DAG, Memory, Skills, Models)

**Goal:** Full management chrome for planned AETHER / harness features, clearly mocked, interactive enough to demo workflows.

**Depends on:** FE-C (cockpit live on mock).  
**Unblocks:** FE-E; product demos of AGI roadmap.

## Tasks

- [ ] **FE-D.1 — Story-DAG editor**
  - Replace static SVG with interactive graph (TanStack Flow or equivalent already chosen).
  - Create/edit/delete nodes & edges; save mock Mission/Story JSON in memory.
  - “Run DAG” triggers mock multi-run scenario via EventSource (or local mock orchestrator).
  - Badge: MOCK — Story-DAG backend ADR-0018 only.
  - **Verify:** unit test graph model serialize/deserialize.

- [ ] **FE-D.2 — Context & AGENTS.md**
  - ContextInspector: bind compaction events when present; otherwise fixture layers 1–7.
  - AGENTS.md tab: load mock file / textarea; “apply” is mock-only.
  - **Verify:** renders MOCK badge; compaction event updates headroom when fed.

- [ ] **FE-D.3 — Memory short / long**
  - New Memory view (or split Context): episodic list + long-term graph fixtures.
  - Actions remember/recall are mock EventSource extensions or local only — document as MOCK.
  - **Verify:** navigation + fixture render tests.

- [ ] **FE-D.4 — Skills & Behaviours**
  - Skills list (progressive disclosure cards); Behaviours/profiles picker.
  - Selecting profile updates next `TaskSpec.profile` in cockpit.
  - **Verify:** profile change reflected in subsequent submitTask payload.

- [ ] **FE-D.5 — Models / Prompts / Harness params**
  - Editors for tier bindings, spend caps, loop limits — persist to local mock config.
  - Read-only note: live config later from Python composition.
  - **Verify:** config round-trip in store tests.

- [ ] **FE-D.6 — Code Intel / Exporter / AETHER**
  - Keep views; wire exporter buttons to mock download or CLI message.
  - AETHER swarm: interactive mock topology (select agent → fake metrics).
  - All MOCK-labeled.
  - **Verify:** no empty `onClick={() => {}}` left without user-visible feedback.

## Definition of done

- [ ] Sidebar covers: Cockpit, Story-DAG, Context, Memory, Skills, Models/Harness, Code Intel, Exporter, AETHER
- [ ] Every non-event-driven view shows MOCK badge
- [ ] `pnpm --filter @sagiha/gui test` green
