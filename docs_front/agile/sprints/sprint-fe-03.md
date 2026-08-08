---
status: rationale
updated: 2026-08-06
---

# Sprint FE-03: Desktop GUI Canvas & Shell

- **Duration**: 3 weeks
- **Depends on**: FE-01
- **Goal**: Build the Tauri v2 desktop app with xyflow DAG canvas and basic panels

## Tasks

### TASK-FE-301: Tauri v2 App Shell
- **Target Seam**: `src_front/apps/desktop/src-tauri/`, `src_front/apps/desktop/src/main.tsx`
- **Acceptance Criteria**:
  1. [ ] Initialize Tauri v2 project and Rust `main.rs`.
  2. [ ] Configure window settings and capability permissions.
  3. [ ] Set up React webview entry point.
- **Estimated complexity**: M

### TASK-FE-302: Three-Panel Layout
- **Target Seam**: `src_front/apps/desktop/src/App.tsx`, `src_front/apps/desktop/src/components/`
- **Acceptance Criteria**:
  1. [ ] Implement Toolbar layout.
  2. [ ] Implement responsive TreePanel / CanvasPanel / EditorPanel layout using Tailwind CSS.
  3. [ ] Implement StatusBar.
- **Estimated complexity**: M

### TASK-FE-303: xyflow WorkflowCanvas
- **Target Seam**: `src_front/apps/desktop/src/components/canvas/WorkflowCanvas.tsx`
- **Acceptance Criteria**:
  1. [ ] Render DAG with custom node types using `xyflow`.
  2. [ ] Load topology from `useWorkflowStore`.
  3. [ ] Implement minimap and auto-layout features.
- **Estimated complexity**: L

### TASK-FE-304: CustomNode Component
- **Target Seam**: `src_front/apps/desktop/src/components/canvas/CustomNode.tsx`
- **Acceptance Criteria**:
  1. [ ] Render `GateStatus` visual states (idle/running/passed/failed/none).
  2. [ ] Display node kind label and budget annotations.
  3. [ ] Implement click-to-inspect functionality linking to `LiveTraceInspector`.
- **Estimated complexity**: M

### TASK-FE-305: ConditionalEdge Component
- **Target Seam**: `src_front/apps/desktop/src/components/canvas/ConditionalEdge.tsx`
- **Acceptance Criteria**:
  1. [ ] Style edge based on `when` predicate (always/on_pass/on_fail/on_instrument_error).
  2. [ ] Implement animated data flow along edges.
- **Estimated complexity**: S

### TASK-FE-306: RepairLoopOverlay
- **Target Seam**: `src_front/apps/desktop/src/components/canvas/RepairLoopOverlay.tsx`
- **Acceptance Criteria**:
  1. [ ] Render dashed bounding box around repair subgraph nodes.
  2. [ ] Display iteration badge ({current}/{max}).
  3. [ ] Add animation on active iteration.
- **Estimated complexity**: M

### TASK-FE-307: FanOutPanel
- **Target Seam**: `src_front/apps/desktop/src/components/canvas/FanOutPanel.tsx`
- **Acceptance Criteria**:
  1. [ ] Display candidate status for Best-of-N sites.
  2. [ ] Render cache sequencing indicator.
- **Estimated complexity**: S

### TASK-FE-308: LiveTraceInspector Panel
- **Target Seam**: `src_front/apps/desktop/src/components/trace/LiveTraceInspector.tsx`
- **Acceptance Criteria**:
  1. [ ] Display turn-by-turn execution log.
  2. [ ] Show prompt layer assembly display (L1-L5).
  3. [ ] Render raw LLM completion viewer.
- **Estimated complexity**: L

### TASK-FE-309: Event Log & Metrics StatusBar
- **Target Seam**: `src_front/apps/desktop/src/components/StatusBar.tsx`
- **Acceptance Criteria**:
  1. [ ] Display filterable event stream.
  2. [ ] Render compact budget meter.
  3. [ ] Show connection status indicator.
- **Estimated complexity**: S

### TASK-FE-310: Mock Cassette Desktop Testing
- **Target Seam**: `src_front/apps/desktop/tests/`
- **Acceptance Criteria**:
  1. [ ] Test full desktop rendering against bundled cassette fixtures.
- **Estimated complexity**: M
