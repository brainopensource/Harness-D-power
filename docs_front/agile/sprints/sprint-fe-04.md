---
status: rationale
updated: 2026-08-06
---

# Sprint FE-04: Advanced Views, Polish & Integration

- **Duration**: 2 weeks
- **Depends on**: FE-02, FE-03
- **Goal**: Monaco diff editor, self-improvement dashboard, live backend integration, testing, CI

## Tasks

### TASK-FE-401: Monaco Diff Editor Panel
- **Target Seam**: `src_front/apps/desktop/src/components/diff/MonacoDiffEditor.tsx`
- **Acceptance Criteria**:
  1. [ ] Render side-by-side diff view using `@monaco-editor/react`.
  2. [ ] Implement inline annotations linking hunks to plan nodes.
  3. [ ] Support accept/reject per hunk via `AcceptDiff`/`RejectDiff` commands.
- **Estimated complexity**: XL

### TASK-FE-402: Self-Improvement Dashboard
- **Target Seam**: `src_front/apps/desktop/src/components/metrics/Dashboard.tsx`
- **Acceptance Criteria**:
  1. [ ] Render McNemar chart and Holm-Bonferroni CI visualization.
  2. [ ] Display score timelines and cost delta charts using `useMetricsStore`.
- **Estimated complexity**: L

### TASK-FE-403: Live Backend WebSocket Integration
- **Target Seam**: `src_front/apps/desktop/src/App.tsx`, `@aether/core/client/AetherWebsocketClient`
- **Acceptance Criteria**:
  1. [ ] Execute full end-to-end live mode testing with running backend.
  2. [ ] Ensure reconnection resilience and robust error handling.
- **Estimated complexity**: L

### TASK-FE-404: CLI Screenshot Regression CI
- **Target Seam**: `.github/workflows/cli-regression.yml`
- **Acceptance Criteria**:
  1. [ ] Implement automated CLI screenshot tests against frozen cassettes.
  2. [ ] Integrate regression tests into GitHub Actions pipeline.
- **Estimated complexity**: M

### TASK-FE-405: Desktop E2E Testing
- **Target Seam**: `src_front/apps/desktop/e2e/`
- **Acceptance Criteria**:
  1. [ ] Implement Playwright tests for Desktop GUI critical paths.
  2. [ ] Cover start run, inspect node, and review diff flows.
- **Estimated complexity**: L

### TASK-FE-406: Cross-Platform Build & Packaging
- **Target Seam**: `src_front/apps/desktop/src-tauri/tauri.conf.json`, CI configurations
- **Acceptance Criteria**:
  1. [ ] Configure Windows `.msi` installer generation.
  2. [ ] Configure Linux `.deb` and `.AppImage` generation.
  3. [ ] Publish CLI as npm package.
  4. [ ] Setup cross-platform CI build matrix.
- **Estimated complexity**: L

### TASK-FE-407: Performance Optimization
- **Target Seam**: Webpack/Vite configs, React component profiling
- **Acceptance Criteria**:
  1. [ ] Pass bundle size audit (CLI < 2MB, Desktop < 20MB).
  2. [ ] Pass memory profiling (idle < targets).
  3. [ ] Ensure event rendering latency < 100ms.
- **Estimated complexity**: L

### TASK-FE-408: Documentation & README
- **Target Seam**: `src_front/README.md`, `docs_front/`
- **Acceptance Criteria**:
  1. [ ] Write user-facing `README.md` for `src_front/`.
  2. [ ] Provide comprehensive CLI usage guide.
  3. [ ] Provide Desktop installation guide.
- **Estimated complexity**: S
