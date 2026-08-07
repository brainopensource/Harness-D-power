---
status: rationale
updated: 2026-08-07
---

# Advisory Notice: Upcoming Front-End Alignment with Backend AETHER Evolution

## 1. Executive Summary & Purpose

This advisory document informs the front-end engineering team that **AETHER**’s backend architecture ([`src/aether/`](file:///home/rocha/Coding/Harness-D-power/src/aether/)) and normative specifications ([`docs/spec.md`](file:///home/rocha/Coding/Harness-D-power/docs/spec.md)) are undergoing enhancements to support **Composite Workflow Nodes**, **Multi-Model Provider Routing**, and **Enhanced Inner/Outer Loop Telemetry**.

> [!IMPORTANT]
> **Pre-Sprint Action Required**: Before commencing future front-end feature sprints (`src_front/apps/desktop`, `src_front/apps/cli`), front-end teams **must review** the updated backend contracts and event catalogs once backend design decisions are ratified.

---

## 2. High-Level Backend Evolution Areas

The backend improvements focus on three major structural areas:

1. **Standardized & Composite Workflow Nodes**:
   * Transitioning from flat node step maps to a hierarchy of **Primitive Nodes** (`Retrieve`, `Generate`, `Apply`, `Evaluate`) and **Composite Nodes** (sub-DAGs like `ArchitectPlanner` or `BoundedRepairLoop`).
2. **Multi-Model Provider Routing**:
   * Implementing `RoutingModelProvider` to allow individual workflow nodes to select distinct model endpoints (e.g. cheap local models for code generation, frontier APIs for high-reasoning planning).
3. **Inner & Outer Loop Telemetry**:
   * Emitting fine-grained event telemetry for inner-loop repair iterations ($k \le 3$), per-node memoization skip signals, and structured budget actuals.

---

## 3. Anticipated Front-End Impact Areas (High-Level Summary)

When front-end development resumes, the primary areas requiring alignment will be:

```
+-----------------------------------------------------------------------------------+
|                        FRONT-END ADAPTATION PANELS                                |
+-------------------------+-------------------------+-------------------------------+
|  1. Event Bridge        |  2. React Flow Canvas   |  3. Mock Server Fixtures      |
|  (@aether/core)         |  (apps/desktop)         |  (@aether/mock-server)        |
+-------------------------+-------------------------+-------------------------------+
| Synchronize Zod event   | Support rendering sub-  | Update mock JSON cassettes to |
| schemas with backend    | graph composite nodes   | mirror composite events and   |
| domain/events.py catalog| & per-node model config | multi-model streaming deltas. |
| updates.                | panels.                 |                               |
+-------------------------+-------------------------+-------------------------------+
```

### 3.1 Shared Types & Bridge Protocol (`packages/core`)
* Update TypeScript discriminators and Zod validation schemas in `@aether/core/types/events.ts` to match the backend event catalog emitted by `kernel/bus.py`.

### 3.2 Desktop GUI Views (`apps/desktop`)
* **Workflow Canvas (`xyflow`)**: Extend React Flow node renderers to support composite/group node unrolling and rendering nested repair loop sub-graphs.
* **Node Inspector**: Add UI controls for inspecting and configuring per-node model routing parameters (`model`, `base_url`, `max_tokens`, `edit_format`).

### 3.3 Mock Cassette Engine (`packages/mock-server`)
* Update cassette JSON fixtures (`swe_bench_pass.json`, `repair_loop_ablation.json`) to include composite step lifecycle events and repair iteration deltas.

---

## 4. Front-End Team Pre-Sprint Checklist

Before starting work on next-phase front-end tasks, team leads should complete the following verification steps:

- [ ] Confirm backend contracts in [`docs/spec.md`](file:///home/rocha/Coding/Harness-D-power/docs/spec.md) and [`docs_front/BRIDGE_CONTRACT.md`](file:///home/rocha/Coding/Harness-D-power/docs_front/BRIDGE_CONTRACT.md) are locked.
- [ ] Verify event type discriminators match backend `src/aether/domain/events.py`.
- [ ] Run `pnpm check-types` and `pnpm build` across monorepo packages.
