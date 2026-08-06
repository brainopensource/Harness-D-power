---
status: rationale
updated: 2026-08-06
---

# Sprint FE-02: CLI TUI Development

- **Duration**: 2 weeks
- **Depends on**: FE-01
- **Goal**: Build the React + Ink TUI client with full event stream consumption

## Tasks

### TASK-FE-201: CLI App Shell & Keyboard Navigation
- **Target Seam**: `src_front/apps/cli/src/index.tsx`, `App.tsx`
- **Acceptance Criteria**:
  1. [ ] Create Ink app entry point.
  2. [ ] Implement screen layout (header/main/footer).
  3. [ ] Implement Tab navigation between panels.
  4. [ ] Implement 'q' keybinding to quit the application.
- **Estimated complexity**: M

### TASK-FE-202: TurnLogStream Component
- **Target Seam**: `src_front/apps/cli/src/components/TurnLogStream.tsx`
- **Acceptance Criteria**:
  1. [ ] Render scrollable event log with severity coloring.
  2. [ ] Implement JSON pretty-print toggle.
  3. [ ] Implement event filtering by type.
- **Estimated complexity**: M

### TASK-FE-203: TaskProgressHeader & BudgetMeter
- **Target Seam**: `src_front/apps/cli/src/components/Header.tsx`, `BudgetMeter.tsx`
- **Acceptance Criteria**:
  1. [ ] Display active run ID and phase indicator.
  2. [ ] Render real-time `BudgetDims` (usd_micros, tokens, wall-clock) using `useBudgetStore`.
- **Estimated complexity**: S

### TASK-FE-204: GateStatusIndicator & TaintAuditBadge
- **Target Seam**: `src_front/apps/cli/src/components/GateStatusIndicator.tsx`, `TaintAuditBadge.tsx`
- **Acceptance Criteria**:
  1. [ ] Implement tri-state gate status rendering (PASSED/FAILED/NONE).
  2. [ ] Display provenance label using `useTaintStore`.
- **Estimated complexity**: S

### TASK-FE-205: Unified Diff Viewer
- **Target Seam**: `src_front/apps/cli/src/components/UnifiedDiffViewer.tsx`
- **Acceptance Criteria**:
  1. [ ] Display ANSI-colored unified diff for pending patches.
  2. [ ] Implement accept/reject keyboard shortcuts triggering `AcceptDiff` / `RejectDiff` commands.
- **Estimated complexity**: L

### TASK-FE-206: Live Bridge Integration
- **Target Seam**: `src_front/apps/cli/src/App.tsx`, `@aether/core/client/AetherWebsocketClient`
- **Acceptance Criteria**:
  1. [ ] Connect CLI to `AetherWebsocketClient` in live mode.
  2. [ ] Implement reconnection handling and connection status indicator.
- **Estimated complexity**: M

### TASK-FE-207: Mock Cassette Playback Testing
- **Target Seam**: `src_front/apps/cli/tests/`
- **Acceptance Criteria**:
  1. [ ] Test full CLI rendering against all bundled cassette fixtures (`swe_bench_pass.json`, `repair_loop_ablation.json`).
  2. [ ] Establish screenshot regression baseline.
- **Estimated complexity**: L
