---
status: normative
updated: 2026-08-06
---

# AETHER Front-End Client Suite — Master Agile Development Tracking List

This tracking list serves as the central living document for monitoring the development, task execution, and sprint evolution of the **AETHER Front-End Client Suite** (`src_front/`).

---

## 📊 Sprint Overview & Progress Dashboard

| Sprint | Scope / Focus | Total Tasks | Completed | In Progress | Pending | Progress (%) | Target Milestone |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Sprint FE-01** | Monorepo Setup, `@aether/core` Stores & Mock Replay Engine | 6 | 6 | 0 | 0 | `100%` | FE-01 Foundation |
| **Sprint FE-02** | TUI CLI Development (`apps/cli` - React + Ink) | 5 | 5 | 0 | 0 | `100%` | FE-02 Terminal CLI |
| **Sprint FE-03** | GUI Canvas (`apps/desktop` - Tauri v2 + `xyflow`) | 5 | 5 | 0 | 0 | `100%` | FE-03 Desktop GUI |
| **Sprint FE-04** | Monaco Diff Reviewer, McNemar Dashboard & Live WS | 4 | 4 | 0 | 0 | `100%` | FE-04 Integration |
| **TOTAL** | **Full Front-End Client Suite** | **20** | **20** | **0** | **0** | `100%` | **V1.0 Release** |

---

## 🏗️ Core Architectural Invariants (FI Rules)

1. **FI1 — Headless Decoupling**: Front-end applications inside `src_front/` MUST NEVER directly import modules from backend `src/aether/`. All communication occurs via JSON RPC and event messages over WebSocket / SSE.
2. **FI2 — Single Source of Truth**: All shared React hooks, Zustand stores, WebSocket client drivers, and domain types reside strictly in `@aether/core` (`src_front/packages/core/`).
3. **FI3 — Dual-Mode Mock Transparency**: Every UI component MUST function identically whether driven by live backend events or pre-recorded cassette playback via `@aether/mock-server`.
4. **FI4 — Unprivileged Consumer**: Front-end applications possess zero capability authorization bypasses. All operator actions pass through `PolicyEngine` evaluation in `kernel/dispatch.py`.
5. **FI5 — Strict Schema Validation**: Inbound events are validated at the bridge boundary via Zod schemas generated from backend `domain/events.py` models.

---

## 🏃 Sprint FE-01: Monorepo Foundation & Mock Engine (`@aether/core` & `@aether/mock-server`)

> **Goal**: Scaffold `src_front/` pnpm monorepo, implement Zustand core stores, Zod event schema validators, `AetherWebsocketClient`, and `MockCassettePlayer` replay engine with pre-recorded cassettes.

- [x] **TASK-FE-000**: Monorepo Workspace & Turborepo Build Pipeline Setup
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/pnpm-workspace.yaml`, `src_front/package.json`, `src_front/turbo.json`, `src_front/.eslintrc.js`
  - **Dependencies**: None
  - **Acceptance Criteria**:
    1. `src_front/` workspace initialized with `packages/core`, `packages/ui-components`, `packages/mock-server`, `apps/cli`, `apps/desktop`.
    2. `pnpm install` and `pnpm build` execute cleanly across all packages via Turborepo.
    3. Import linter rule blocks any cross-import pointing directly to backend `src/aether/`.

- [x] **TASK-FE-001**: Domain Event Types, Zod Schemas & Shared Contracts
  - **Complexity**: 🟢 Easy | **Role**: Junior Developer
  - **Target Files**: `src_front/packages/core/src/types/events.ts`, `src_front/packages/core/src/types/gate.ts`, `src_front/packages/core/src/types/budget.ts`
  - **Dependencies**: `TASK-FE-000`
  - **Acceptance Criteria**:
    1. TypeScript interfaces and Zod schemas defined for tri-state `GateStatus` (`PASSED`, `FAILED`, `NONE` instrument error), `GateReport`, `Provenance` labels, integer `BudgetDims`, `BridgeEvent` envelope, and wire payloads.
    2. Zod validation functions parse raw wire JSON into validated domain event objects.

- [x] **TASK-FE-002**: Partitioned Zustand Core Domain Stores
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/packages/core/src/stores/useEngineStore.ts`, `useWorkflowStore.ts`, `useBudgetStore.ts`, `usePatchStore.ts`, `useMetricsStore.ts`, `useTaintStore.ts`
  - **Dependencies**: `TASK-FE-001`
  - **Acceptance Criteria**:
    1. Six domain-partitioned Zustand stores implemented (`useEngineStore`, `useWorkflowStore`, `useBudgetStore`, `usePatchStore`, `useMetricsStore`, `useTaintStore`).
    2. Unit tests verify independent state updates without cross-store re-render pollution.

- [x] **TASK-FE-003**: WebSocket Protocol Client & SSE Transport Driver
  - **Complexity**: 🔴 Hard | **Role**: Senior Developer
  - **Target Files**: `src_front/packages/core/src/client/AetherWebsocketClient.ts`
  - **Dependencies**: `TASK-FE-001`, `TASK-FE-002`
  - **Acceptance Criteria**:
    1. `AetherWebsocketClient` manages bi-directional WebSocket connection, auto-reconnect, and SSE read-only fallback.
    2. Validates incoming wire events using Zod schemas and dispatches to Zustand stores.

- [x] **TASK-FE-004**: Deterministic Mock Cassette Replay Engine & Bundled Fixtures
  - **Complexity**: 🔴 Hard | **Role**: Senior Developer
  - **Target Files**: `src_front/packages/mock-server/src/MockCassettePlayer.ts`, `src_front/packages/mock-server/cassettes/swe_bench_pass.json`, `repair_loop_ablation.json`
  - **Dependencies**: `TASK-FE-001`
  - **Acceptance Criteria**:
    1. `MockCassettePlayer` supports `loadCassette()`, `play(speedMultiplier)`, `pause()`, `resume()`, `stepForward()`.
    2. Cassette JSON files (`swe_bench_pass.json`, `repair_loop_ablation.json`) committed and verified for sequential replay.

- [x] **TASK-FE-005**: Shared Custom React Stream & Audit Hooks
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/packages/core/src/hooks/useAetherStream.ts`, `useNodeTrace.ts`, `useBudget.ts`, `useTaintAudit.ts`
  - **Dependencies**: `TASK-FE-002`, `TASK-FE-003`, `TASK-FE-004`
  - **Acceptance Criteria**:
    1. `useAetherStream` connects seamlessly to either `AetherWebsocketClient` or `MockCassettePlayer`.
    2. React views update reactively upon receiving event deltas.

---

## 🖥️ Sprint FE-02: TUI CLI Application (`apps/cli` - React + Ink)

> **Goal**: Implement terminal-based dashboard using React 19 + Ink with streaming log viewer, budget meters, gate status indicators, and interactive keybindings.

- [x] **TASK-FE-010**: React 19 + Ink TUI Application Shell & Executable Bundler
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/apps/cli/src/App.tsx`, `src_front/apps/cli/src/index.tsx`, `src_front/apps/cli/package.json`
  - **Dependencies**: Sprint FE-01
  - **Acceptance Criteria**:
    1. `@aether/cli` boots an interactive terminal UI using Ink and Yoga flexbox layout.
    2. `tsup` compiles app into a standalone executable script (`aether-cli`).

- [x] **TASK-FE-011**: Terminal Header & Real-time Budget Meter Component
  - **Complexity**: 🟢 Easy | **Role**: Junior Developer
  - **Target Files**: `src_front/apps/cli/src/components/Header.tsx`, `src_front/apps/cli/src/components/BudgetMeter.tsx`
  - **Dependencies**: `TASK-FE-010`
  - **Acceptance Criteria**:
    1. Displays active run ID, topology name, step progress, and integer budget indicators (USD micros, prompt/completion tokens, wall-clock ms).
    2. Updates live upon receiving `BudgetLeaseUpdated` events.

- [x] **TASK-FE-012**: Terminal Turn Log Stream & LLM Delta Parser
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/apps/cli/src/components/TurnLogStream.tsx`
  - **Dependencies**: `TASK-FE-010`
  - **Acceptance Criteria**:
    1. Parses `ModelStreamDelta` events and streams text output and tool calls smoothly without terminal screen flickering.

- [x] **TASK-FE-013**: Terminal Tri-state Gate Indicator & Taint Audit Badges
  - **Complexity**: 🟢 Easy | **Role**: Junior Developer
  - **Target Files**: `src_front/apps/cli/src/components/GateStatusIndicator.tsx`, `src_front/apps/cli/src/components/TaintAuditBadge.tsx`
  - **Dependencies**: `TASK-FE-010`
  - **Acceptance Criteria**:
    1. Renders `PASSED` (✓ green), `FAILED` (✗ red), and `NONE` (⚠ amber with instrument error detail). `NONE` is never rendered as passed.

- [x] **TASK-FE-014**: CLI Interactive Keybindings & Command Runner
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/apps/cli/src/components/CommandRunner.tsx`
  - **Dependencies**: `TASK-FE-010`
  - **Acceptance Criteria**:
    1. Terminal keybindings allow operators to trigger `StartRun`, `CancelRun`, and toggle mock cassette replay speed (`1x`, `2x`, `5x`).

---

## 🎨 Sprint FE-03: Desktop GUI Canvas & Node Engine (`apps/desktop` - Tauri v2 + `xyflow`)

> **Goal**: Build Tauri v2 Rust desktop application shell with dark glassmorphism styling, `xyflow` workflow DAG canvas, custom node/edge renderers, and live trace inspection panel.

- [x] **TASK-FE-020**: Tauri v2 Desktop Shell & Native Window Integration
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/apps/desktop/src-tauri/Cargo.toml`, `src_front/apps/desktop/src-tauri/src/main.rs`, `src_front/apps/desktop/vite.config.ts`
  - **Dependencies**: Sprint FE-01
  - **Acceptance Criteria**:
    1. Tauri v2 app launches window on Windows/Linux rendering React 19 SPA.
    2. Installer bundle size $< 15\text{ MB}$, idle memory $< 40\text{ MB}$.

- [x] **TASK-FE-021**: Design System & Tailwind CSS v4 Glassmorphism Theme
  - **Complexity**: 🟢 Easy | **Role**: Junior Developer
  - **Target Files**: `src_front/packages/ui-components/src/Button.tsx`, `Card.tsx`, `Badge.tsx`, `Modal.tsx`
  - **Dependencies**: `TASK-FE-020`
  - **Acceptance Criteria**:
    1. High-aesthetic dark-mode glassmorphism component library using Tailwind CSS v4.

- [x] **TASK-FE-022**: `xyflow` Workflow DAG Canvas Core Engine
  - **Complexity**: 🔴 Hard | **Role**: Senior Developer
  - **Target Files**: `src_front/apps/desktop/src/components/canvas/WorkflowCanvas.tsx`
  - **Dependencies**: `TASK-FE-020`
  - **Acceptance Criteria**:
    1. Integrates `xyflow` (React Flow) with drag-and-drop nodes, zoom/pan controls, mini-map, and automatic graph layout algorithms.

- [x] **TASK-FE-023**: Custom DAG Node & Conditional Edge Renderers
  - **Complexity**: 🔥 Very Hard | **Role**: Senior Specialist (Canvas/Graph)
  - **Target Files**: `src_front/apps/desktop/src/components/canvas/CustomNode.tsx`, `ConditionalEdge.tsx`, `RepairLoopGroup.tsx`
  - **Dependencies**: `TASK-FE-022`
  - **Acceptance Criteria**:
    1. Custom SVG edges render conditional routing (`on_pass` green, `on_fail` red, `on_instrument_error` amber dotted line).
    2. Bounding box groups render repair loop iterations and Best-of-N candidate lane expansion.

- [x] **TASK-FE-024**: Live Trace Inspector Side-Panel
  - **Complexity**: 🔴 Hard | **Role**: Senior Developer
  - **Target Files**: `src_front/apps/desktop/src/components/trace/LiveTraceInspector.tsx`, `SpanViewer.tsx`
  - **Dependencies**: `TASK-FE-022`
  - **Acceptance Criteria**:
    1. Selecting any node on the canvas displays prompt prefix layers (L1–L5), raw model completion history, tool outputs, and tri-state gate reports.

---

## ⚡ Sprint FE-04: Advanced Inspectors, Monaco Diffing & Integration

> **Goal**: Implement Monaco side-by-side patch diff reviewer, McNemar statistical self-improvement dashboard, taint audit panel, and end-to-end live backend / mock cassette switching.

- [x] **TASK-FE-030**: Monaco Side-by-Side Patch Diff Reviewer Component
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/apps/desktop/src/components/diff/MonacoDiffEditor.tsx`
  - **Dependencies**: Sprint FE-03
  - **Acceptance Criteria**:
    1. Integrated Monaco Diff Editor displays unified git patches side-by-side with interactive Accept/Reject diff triggers.

- [x] **TASK-FE-031**: Self-Improvement & McNemar Statistical Dashboard
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/apps/desktop/src/components/metrics/McNemarChart.tsx`, `MetricsDashboard.tsx`
  - **Dependencies**: Sprint FE-03
  - **Acceptance Criteria**:
    1. Renders statistical A/B test results, Holm–Bonferroni adjusted p-values, cost deltas, and benchmark time-series charts.

- [x] **TASK-FE-032**: Taint Gate Provenance Audit Panel
  - **Complexity**: 🟡 Medium | **Role**: Normal Developer
  - **Target Files**: `src_front/apps/desktop/src/components/trace/TaintAuditPanel.tsx`
  - **Dependencies**: Sprint FE-03
  - **Acceptance Criteria**:
    1. Context span inspector displays provenance tags (`TRUSTED_SYSTEM`, `OPERATOR`, `AGENT`, `UNTRUSTED_EXTERNAL`, `UNTRUSTED_DERIVED`) with visual risk highlights.

- [x] **TASK-FE-033**: Live Engine WS Integration & Dual-Mode Cassette Replay Switch
  - **Complexity**: 🔴 Hard | **Role**: Senior Developer
  - **Target Files**: `src_front/apps/desktop/src/App.tsx`, `src_front/apps/cli/src/App.tsx`
  - **Dependencies**: `TASK-FE-003`, `TASK-FE-004`, `TASK-FE-014`, `TASK-FE-024`
  - **Acceptance Criteria**:
    1. Seamless UI mode toggle between live backend WebSocket connection and pre-recorded mock cassette playback in both CLI and Desktop applications.

---

## 📈 Evolution & Maintenance Instructions

1. **Updating Task Status**: When starting a task, update status to `[~]` (In Progress) and record developer assignment. When completed, check `[x]` (Completed).
2. **Adding New Tasks**: Any new story or technical task must be appended under the corresponding Sprint section with explicit Acceptance Criteria, Target Files, and FI invariant mapping.
3. **CI Conformance**: Every pull request updating `src_front/` must verify that `pnpm build` and `pnpm test` pass across all workspace packages.
