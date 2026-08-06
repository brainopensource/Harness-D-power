---
status: rationale
updated: 2026-08-06
---

# Sprint FE-01 Plan — Monorepo Scaffolding & Mock Engine

* **Goal**: Establish the `src_front/` pnpm monorepo structure, `@aether/core` shared Zustand stores and hooks, `@aether/mock-server` cassette player, and initial app shells for CLI and Desktop.
* **Target Milestone**: Front-End Foundation (FE-01)
* **Tripwire Window**: 5 Business Days

---

## Backlog Breakdown

### Task FE-101: Monorepo & Workspace Scaffolding (`TASK-FE-101`)
* **Target Seam**: `src_front/package.json`, `pnpm-workspace.yaml`, `turbo.json`
* **Acceptance Criteria**:
  1. Monorepo configured with packages `@aether/core`, `@aether/ui-components`, `@aether/mock-server`, and apps `@aether/cli`, `@aether/desktop`.
  2. `pnpm install` and `pnpm build` execute cleanly across all workspaces.

### Task FE-102: Shared Core Package (`TASK-FE-102`)
* **Target Seam**: `src_front/packages/core/`
* **Acceptance Criteria**:
  1. Zustand stores (`useEngineStore`, `useWorkflowStore`, `useTaintStore`) implemented with TypeScript types.
  2. `useAetherStream` custom hook defined for event stream ingestion.

### Task FE-103: Mock Cassette Engine (`TASK-FE-103`)
* **Target Seam**: `src_front/packages/mock-server/`
* **Acceptance Criteria**:
  1. Pre-recorded event stream cassettes (`swe_bench_pass.json`, `repair_loop_ablation.json`) committed.
  2. `MockCassettePlayer` correctly replays events sequentially via `useAetherStream`.

### Task FE-104: CLI Shell Prototype (`TASK-FE-104`)
* **Target Seam**: `src_front/apps/cli/`
* **Acceptance Criteria**:
  1. React + Ink CLI app boots and renders header and turn streaming log via `MockCassettePlayer`.

### Task FE-105: Desktop Shell Prototype (`TASK-FE-105`)
* **Target Seam**: `src_front/apps/desktop/`
* **Acceptance Criteria**:
  1. Tauri v2 app launches window on Windows and Linux rendering React 19 app shell.
