---
status: rationale
updated: 2026-08-06
---

# AETHER Front-End Client Suite — Product & Technical Backlog

This backlog catalogs all Epics, User Stories, and Technical Tasks for building the AETHER Front-End Client Suite across `src_front/`. All tasks map directly to normative rules in [`docs_front/spec.md`](../spec.md), [`docs_front/architecture.md`](../architecture.md), [`docs_front/BRIDGE_CONTRACT.md`](../BRIDGE_CONTRACT.md), and [`docs_front/agile/roadmap.md`](./roadmap.md).

---

## System Invariants & Rules

1. **FI1 — Headless Decoupling**: Zero direct imports from `src/aether/` inside `src_front/`. All interaction occurs via WebSocket / SSE messages over `engine.py`.
2. **FI2 — Single Source of Truth**: All shared React hooks, state stores, WebSocket protocol clients, and data models reside in `src_front/packages/core/`.
3. **FI3 — Dual-Mode Mock Compatibility**: Every UI component must operate seamlessly in `Live` mode or `Mock` (cassette replay) mode without conditional code inside views.
4. **FI4 — Unprivileged Consumer**: The front-end possesses zero capability authorization bypasses; actions requested by the user pass through `kernel/dispatch.py` grants.
5. **FI5 — Strict Event Schema Validation**: Incoming events are validated against TypeScript types generated from `domain/events.py` using Zod schemas at the bridge boundary.

---

## Epic 1: Monorepo Foundation & Shared Core (`packages/core`) — Sprint FE-01

### TASK-FE-000: Monorepo Workspace & Build Pipeline Setup
* **Description**: Initialize `src_front/` pnpm workspace, `turbo.json` task graph, TypeScript configurations, and ESLint path boundaries enforcing FI1 (no backend imports) and FI2 (core package boundaries).
* **Target Files**: `src_front/pnpm-workspace.yaml`, `src_front/package.json`, `src_front/turbo.json`, `src_front/.eslintrc.js`
* **Normative Specs**: [`spec.md` §1 (FI1, FI2)](../spec.md#1-system-invariants), [`architecture.md` §1](../architecture.md#1-monorepo-topology-src_front)
* **Exit Criteria**: `pnpm build` builds all packages via Turborepo; import linter blocks any import referencing `src/aether/`.

### TASK-FE-001: Domain Event Types & Zod Schemas
* **Description**: Create TypeScript interfaces and Zod schemas for all inbound events (`BridgeEvent`, `RunStarted`, `NodeExecutionFinished`, `GateReport`, `ModelStreamDelta`, etc.) and outbound commands (`StartRun`, `AcceptDiff`, `RejectDiff`).
* **Target Files**: `src_front/packages/core/src/types/events.ts`, `src_front/packages/core/src/types/gate.ts`, `src_front/packages/core/src/types/budget.ts`
* **Normative Specs**: [`BRIDGE_CONTRACT.md` §2–4](../BRIDGE_CONTRACT.md), [`spec.md` §1 (FI5)](../spec.md#1-system-invariants)
* **Exit Criteria**: Zod validation functions parse raw JSON wire payloads into typed domain events. Malformed events are safely rejected.

### TASK-FE-002: Partitioned Zustand Core Stores
* **Description**: Implement six domain-partitioned Zustand stores in `@aether/core`: `useEngineStore`, `useWorkflowStore`, `useBudgetStore`, `usePatchStore`, `useMetricsStore`, and `useTaintStore`.
* **Target Files**: `src_front/packages/core/src/stores/*.ts`
* **Normative Specs**: [`architecture.md` §3](../architecture.md#3-zustand-store-architecture-aethercore), [`spec.md` §2](../spec.md#2-shared-engine-package-packagescore)
* **Exit Criteria**: Unit tests prove each store manages state independently with zero cross-store re-render pollution.

### TASK-003-FE: WebSocket Protocol Client & Transport Driver
* **Description**: Build `AetherWebsocketClient` for live bidirectional engine communication over WebSocket with HTTP SSE fallback for read-only events.
* **Target Files**: `src_front/packages/core/src/client/AetherWebsocketClient.ts`
* **Normative Specs**: [`BRIDGE_CONTRACT.md` §1](../BRIDGE_CONTRACT.md#1-protocol-architecture), [`spec.md` §1 (FI1)](../spec.md#1-system-invariants)
* **Exit Criteria**: Handles auto-reconnect, deserializes inbound events, validates payloads via Zod, and dispatches to Zustand stores.

### TASK-FE-004: Mock Cassette Replay Engine & Bundled Fixtures
* **Description**: Implement `MockCassettePlayer` in `@aether/mock-server` supporting cassette loading, play/pause, step-forward, and playback speed control (`0.5x` to `5.0x`). Include `swe_bench_pass.json` and `repair_loop_ablation.json` fixtures.
* **Target Files**: `src_front/packages/mock-server/src/MockCassettePlayer.ts`, `src_front/packages/mock-server/cassettes/*.json`
* **Normative Specs**: [`BRIDGE_CONTRACT.md` §5](../BRIDGE_CONTRACT.md#5-deterministic-mock-cassette-engine-packagesmock-server), [`spec.md` §1 (FI3)](../spec.md#1-system-invariants)
* **Exit Criteria**: `MockCassettePlayer` implements the exact same stream interface as `AetherWebsocketClient` allowing seamless component testing without a running backend.

### TASK-FE-005: Shared React Stream & Audit Hooks
* **Description**: Implement `useAetherStream` (mode-agnostic stream connector), `useNodeTrace`, `useBudget`, and `useTaintAudit` hooks.
* **Target Files**: `src_front/packages/core/src/hooks/*.ts`
* **Normative Specs**: [`spec.md` §2](../spec.md#2-shared-engine-package-packagescore), [`architecture.md` §3](../architecture.md#3-zustand-store-architecture-aethercore)
* **Exit Criteria**: Hooks provide reactive UI access to streaming event deltas, node gate status, and budget consumption.

---

## Epic 2: CLI Terminal UI Application (`apps/cli`) — Sprint FE-02

### TASK-FE-010: React + Ink Application Shell & Entry Point
* **Description**: Set up `@aether/cli` app structure using React 19 and Ink. Configure `tsup` build target to compile a standalone executable script (`aether-cli`).
* **Target Files**: `src_front/apps/cli/src/App.tsx`, `src_front/apps/cli/src/index.tsx`, `src_front/apps/cli/package.json`
* **Normative Specs**: [`spec.md` §3.1](../spec.md#31-tui-cli-src_frontappscli), [`architecture.md` §2.1](../architecture.md#21-tui-cli-stack-react-19--ink)
* **Exit Criteria**: Running `aether-cli` opens an interactive terminal interface with responsive Yoga Flexbox layout.

### TASK-FE-011: Terminal Header & Budget Meter Component
* **Description**: Build `<TaskProgressHeader />` and `<BudgetMeter />` in Ink rendering active run ID, topology, step progress, and real-time integer budget meters (micro-USD, tokens, wall-clock ms).
* **Target Files**: `src_front/apps/cli/src/components/Header.tsx`, `src_front/apps/cli/src/components/BudgetMeter.tsx`
* **Normative Specs**: [`spec.md` §3.1](../spec.md#31-tui-cli-src_frontappscli), [`BRIDGE_CONTRACT.md` §2.3](../BRIDGE_CONTRACT.md#23-budgetdims)
* **Exit Criteria**: Budget meter updates live upon receiving `BudgetLeaseUpdated` events.

### TASK-FE-012: Terminal Turn Log Stream & LLM Delta Parser
* **Description**: Build `<TurnLogStream />` in Ink to render streaming text deltas, tool calls, and execution outputs in real-time.
* **Target Files**: `src_front/apps/cli/src/components/TurnLogStream.tsx`
* **Normative Specs**: [`spec.md` §3.1](../spec.md#31-tui-cli-src_frontappscli), [`BRIDGE_CONTRACT.md` §3.2](../BRIDGE_CONTRACT.md#32-event-type-registry)
* **Exit Criteria**: Parses `ModelStreamDelta` events and streams model output smoothly without terminal flickering.

### TASK-FE-013: Terminal Gate Status Indicator & Taint Badges
* **Description**: Build `<GateStatusIndicator />` and `<TaintAuditBadge />` rendering tri-state gate statuses (`PASSED` ✓, `FAILED` ✗, `NONE` ⚠ amber warning with instrument error detail) and context span provenance labels.
* **Target Files**: `src_front/apps/cli/src/components/GateStatusIndicator.tsx`, `src_front/apps/cli/src/components/TaintAuditBadge.tsx`
* **Normative Specs**: [`spec.md` §3.1](../spec.md#31-tui-cli-src_frontappscli), [`BRIDGE_CONTRACT.md` §2.1](../BRIDGE_CONTRACT.md#21-gatestatus-tri-state)
* **Exit Criteria**: `NONE` gate reports display amber warnings with instrument error details; never rendered as passed.

### TASK-FE-014: CLI Interactive Command Runner
* **Description**: Implement terminal keybindings and prompt input controls for enqueuing runs (`StartRun`) and cancelling runs (`CancelRun`).
* **Target Files**: `src_front/apps/cli/src/components/CommandRunner.tsx`
* **Normative Specs**: [`BRIDGE_CONTRACT.md` §4](../BRIDGE_CONTRACT.md#4-outbound-command-schemas-client--engine)
* **Exit Criteria**: Pressing key shortcuts sends structured JSON commands over WebSocket/Mock stream.

---

## Epic 3: Desktop GUI Canvas & Node Engine (`apps/desktop`) — Sprint FE-03

### TASK-FE-020: Tauri v2 Desktop Shell & Window Setup
* **Description**: Configure Tauri v2 Rust desktop shell (`src-tauri/`) with native OS webview setup, multi-platform window management, and Vite build pipeline.
* **Target Files**: `src_front/apps/desktop/src-tauri/Cargo.toml`, `src_front/apps/desktop/src-tauri/src/main.rs`, `src_front/apps/desktop/vite.config.ts`
* **Normative Specs**: [`spec.md` §3.2](../spec.md#32-desktop-gui-src_frontappsdesktop), [`architecture.md` §2.2](../architecture.md#22-desktop-gui-stack-tauri-v2--react-19--xyflow--monaco-editor)
* **Exit Criteria**: Desktop app compiles to a lightweight native binary ($<15\text{ MB}$ installer, $<40\text{ MB}$ RAM).

### TASK-FE-021: Design System & Tailwind CSS v4 Theme
* **Description**: Implement Tailwind CSS v4 design system in `@aether/ui-components` featuring dark-mode themes, glassmorphism, custom scrollbars, and reusable UI components (Button, Card, Badge, Modal).
* **Target Files**: `src_front/packages/ui-components/src/*`
* **Normative Specs**: [`architecture.md` §2.2](../architecture.md#22-desktop-gui-stack-tauri-v2--react-19--xyflow--monaco-editor)
* **Exit Criteria**: Consistent, high-aesthetic dark glassmorphism theme across all Desktop GUI panels.

### TASK-FE-022: `xyflow` Workflow Canvas Core
* **Description**: Integrate `xyflow` (React Flow) in `WorkflowCanvas.tsx` with drag-and-drop nodes, custom handles, pan/zoom, mini-map, and automatic graph layout algorithms.
* **Target Files**: `src_front/apps/desktop/src/components/canvas/WorkflowCanvas.tsx`
* **Normative Specs**: [`spec.md` §3.2](../spec.md#32-desktop-gui-src_frontappsdesktop), [`architecture.md` §4](../architecture.md#4-dag-topology-rendering-specification)
* **Exit Criteria**: Renders workflow topologies dynamically from `useWorkflowStore`; supports node selection and inspection.

### TASK-FE-023: Custom DAG Node & Conditional Edge Renderers
* **Description**: Implement custom `xyflow` node and edge components rendering conditional routing (`on_pass` green, `on_fail` red, `on_instrument_error` amber dotted line), repair loop subgraphs with iteration badges, and Best-of-N fan-out lane expansion.
* **Target Files**: `src_front/apps/desktop/src/components/canvas/CustomNode.tsx`, `src_front/apps/desktop/src/components/canvas/ConditionalEdge.tsx`, `src_front/apps/desktop/src/components/canvas/RepairLoopGroup.tsx`
* **Normative Specs**: [`architecture.md` §4.1–4.4](../architecture.md#4-dag-topology-rendering-specification)
* **Exit Criteria**: Complex topology structures (repair loops, fan-out sites, conditional edges) render visually distinct states based on active execution.

### TASK-FE-024: Live Trace Inspector Panel
* **Description**: Build `LiveTraceInspector.tsx` side-panel displaying prompt prefix layers (L1–L5), raw LLM completions, tool execution outputs, and node `GateReport` details.
* **Target Files**: `src_front/apps/desktop/src/components/trace/LiveTraceInspector.tsx`, `src_front/apps/desktop/src/components/trace/SpanViewer.tsx`
* **Normative Specs**: [`spec.md` §3.2](../spec.md#32-desktop-gui-src_frontappsdesktop)
* **Exit Criteria**: Clicking any node on the canvas populates the trace inspector with its full prompt, model stream history, and gate results.

---

## Epic 4: Advanced Inspectors, Monaco Diffing & Integration — Sprint FE-04

### TASK-FE-030: Monaco Side-by-Side Patch Diff Reviewer
* **Description**: Integrate `@monaco-editor/react` in `MonacoDiffEditor.tsx` providing side-by-side patch diffing, syntax highlighting, hunk selection, and `AcceptDiff` / `RejectDiff` command triggers.
* **Target Files**: `src_front/apps/desktop/src/components/diff/MonacoDiffEditor.tsx`
* **Normative Specs**: [`spec.md` §3.2](../spec.md#32-desktop-gui-src_frontappsdesktop), [`BRIDGE_CONTRACT.md` §4.1](../BRIDGE_CONTRACT.md#41-command-registry)
* **Exit Criteria**: Displays proposed git unified diffs side-by-side with interactive Accept/Reject actions sending commands to backend.

### TASK-FE-031: Self-Improvement & McNemar Statistical Dashboard
* **Description**: Build `McNemarChart.tsx` and statistical dashboard displaying A/B test results, Holm–Bonferroni adjusted p-values ($\alpha = 0.05$), cost deltas, and time-series benchmark performance charts.
* **Target Files**: `src_front/apps/desktop/src/components/metrics/McNemarChart.tsx`, `src_front/apps/desktop/src/components/metrics/MetricsDashboard.tsx`
* **Normative Specs**: [`spec.md` §3.2](../spec.md#32-desktop-gui-src_frontappsdesktop), [`architecture.md` §3 (Store 5)](../architecture.md#3-zustand-store-architecture-aethercore)
* **Exit Criteria**: Visualizes statistical admission results and statistical confidence intervals for ablation runs.

### TASK-FE-032: Taint Gate Provenance Audit Panel
* **Description**: Build `TaintAuditPanel.tsx` inspecting context span provenance (`TRUSTED_SYSTEM`, `OPERATOR`, `AGENT`, `UNTRUSTED_EXTERNAL`, `UNTRUSTED_DERIVED`) with visual highlight badges for untrusted external content.
* **Target Files**: `src_front/apps/desktop/src/components/trace/TaintAuditPanel.tsx`
* **Normative Specs**: [`BRIDGE_CONTRACT.md` §2.2](../BRIDGE_CONTRACT.md#22-provenance-taintgate-labels), [`architecture.md` §3 (Store 6)](../architecture.md#3-zustand-store-architecture-aethercore)
* **Exit Criteria**: Displays security audit trail for all context spans used during LLM prompt assembly.

### TASK-FE-033: Live Engine Integration & Cassette Replay Switch
* **Description**: Wire live engine WebSocket/SSE connections and mock cassette replay switch across both CLI and Desktop applications. Ensure seamless toggling between live backend execution and pre-recorded cassette replay.
* **Target Files**: `src_front/apps/desktop/src/App.tsx`, `src_front/apps/cli/src/App.tsx`
* **Normative Specs**: [`spec.md` §1 (FI3)](../spec.md#1-system-invariants), [`BRIDGE_CONTRACT.md` §5.3](../BRIDGE_CONTRACT.md#53-replay-semantics)
* **Exit Criteria**: End-to-end integration verified against live backend and mock cassettes; UI operates identically in both modes.

---

## Frontend Roadmap Complexity & Developer Assignment

| Task ID | Feature / Component | Milestone / Sprint | Complexity | Assigned Developer Role | Technical Complexity & Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-FE-001` | Domain Event Types & Zod Schemas | Sprint FE-01 | 🟢 Easy | **Junior Developer** | Creating TypeScript interfaces and Zod validators matching backend event models. Clear contracts, straightforward schema definitions. |
| `TASK-FE-011` | Terminal Header & Budget Meter | Sprint FE-02 | 🟢 Easy | **Junior Developer** | Ink terminal flexbox header displaying active run info and budget numbers (USD micros, tokens, ms). Pure presentation component. |
| `TASK-013-FE` | Terminal Gate Status & Taint Badges | Sprint FE-02 | 🟢 Easy | **Junior Developer** | Ink badge components rendering tri-state status (`PASSED`, `FAILED`, `NONE` amber) and taint labels. Straightforward conditional rendering. |
| `TASK-FE-021` | Design System & Tailwind CSS v4 Theme | Sprint FE-03 | 🟢 Easy | **Junior Developer** | Dark mode glassmorphism UI component library (Button, Card, Badge, Modal) in Tailwind CSS v4. UI design & styling focus. |
| `TASK-FE-000` | Monorepo Setup & Build Pipeline | Sprint FE-01 | 🟡 Medium | **Normal Developer** | pnpm workspace, Turborepo setup, ESLint import linter boundaries enforcing FI1 & FI2 across monorepo packages. |
| `TASK-FE-002` | Partitioned Zustand Core Stores | Sprint FE-01 | 🟡 Medium | **Normal Developer** | Implementing six decoupled Zustand domain stores in `@aether/core`. State management patterns, selective subscription selectors. |
| `TASK-FE-005` | Shared React Stream & Audit Hooks | Sprint FE-01 | 🟡 Medium | **Normal Developer** | Custom React hooks (`useAetherStream`, `useNodeTrace`, `useBudget`, `useTaintAudit`) bridging Zustand stores to UI views. |
| `TASK-FE-010` | React + Ink App Shell & Build | Sprint FE-02 | 🟡 Medium | **Normal Developer** | Setting up Ink CLI application structure, input handlers, and `tsup` bundling into a standalone executable script. |
| `TASK-FE-012` | Terminal Turn Log Stream | Sprint FE-02 | 🟡 Medium | **Normal Developer** | Real-time streaming LLM delta parser in terminal. Smooth text rendering without screen flickering using Ink flexbox. |
| `TASK-FE-014` | CLI Interactive Command Runner | Sprint FE-02 | 🟡 Medium | **Normal Developer** | Terminal input prompt and keybinding handlers for sending structured JSON commands (`StartRun`, `CancelRun`) over WebSocket. |
| `TASK-FE-020` | Tauri v2 Desktop Shell Setup | Sprint FE-03 | 🟡 Medium | **Normal Developer** | Native desktop wrapper setup using Tauri v2 (Rust), window configuration, multi-platform build setup (Windows/Linux). |
| `TASK-FE-030` | Monaco Side-by-Side Patch Diff Reviewer | Sprint FE-04 | 🟡 Medium | **Normal Developer** | Monaco Editor integration (`@monaco-editor/react`) for side-by-side patch diffing, hunk selection, and Accept/Reject triggers. |
| `TASK-FE-031` | Self-Improvement & McNemar Dashboard | Sprint FE-04 | 🟡 Medium | **Normal Developer** | Charting dashboard rendering statistical A/B test results, Holm–Bonferroni p-values, and time-series benchmark metrics. |
| `TASK-FE-032` | Taint Gate Provenance Audit Panel | Sprint FE-04 | 🟡 Medium | **Normal Developer** | Context span provenance inspector rendering security audit trails and highlighting untrusted external inputs. |
| `TASK-FE-003` | WebSocket Protocol Client & Transport | Sprint FE-01 | 🔴 Hard | **Senior Developer** | `AetherWebsocketClient` featuring auto-reconnect, SSE fallback, Zod wire deserialization, and state synchronization with Zustand. |
| `TASK-FE-004` | Mock Cassette Replay Engine | Sprint FE-01 | 🔴 Hard | **Senior Developer** | `MockCassettePlayer` in `@aether/mock-server` implementing full playback control (speed multiplier, step-forward, play/pause) for FI3 dual-mode DI. |
| `TASK-FE-022` | `xyflow` Workflow Canvas Core | Sprint FE-03 | 🔴 Hard | **Senior Developer** | Interactive ComfyUI/n8n-style workflow editor using `xyflow`. Custom node handling, socket type verification, auto layout graph algorithms. |
| `TASK-FE-024` | Live Trace Inspector Panel | Sprint FE-03 | 🔴 Hard | **Senior Developer** | Complex execution trace inspector showing L1–L5 prompt layers, raw stream history, and tri-state gate details synchronized with selected DAG node. |
| `TASK-FE-033` | Live Engine WS Integration & Replay Switch | Sprint FE-04 | 🔴 Hard | **Senior Developer** | E2E integration connecting frontend stores with live backend WebSocket streams and cassette replay switch across both CLI & Desktop apps. |
| `TASK-FE-023` | Custom DAG Node & Edge Renderers | Sprint FE-03 | 🔥 Very Hard | **Senior Specialist** *(Canvas / Graph Rendering)* | Custom SVG edge routing for conditional edges (`on_pass` green, `on_fail` red, `on_instrument_error` amber), repair loop sub-graph bounding boxes, and Best-of-N fan-out candidate lane expansion. Requires deep `xyflow` / React Flow SVG rendering expertise. |

---

## Summary by Developer Tier

| Tier | Count | Tasks |
| :--- | :--- | :--- |
| 🟢 **Junior Developer** | 4 | `TASK-FE-001`, `TASK-FE-011`, `TASK-013-FE`, `TASK-FE-021` |
| 🟡 **Normal Developer** | 10 | `TASK-FE-000`, `TASK-FE-002`, `TASK-FE-005`, `TASK-FE-010`, `TASK-FE-012`, `TASK-FE-014`, `TASK-FE-020`, `TASK-FE-030`, `TASK-FE-031`, `TASK-FE-032` |
| 🔴 **Senior Developer** | 5 | `TASK-FE-003`, `TASK-FE-004`, `TASK-FE-022`, `TASK-FE-024`, `TASK-FE-033` |
| 🔥 **Senior Specialist** | 1 | `TASK-FE-023` *(Canvas & Graph Rendering Specialist — `xyflow` custom SVG routing, repair sub-graphs & fan-out lanes)* |

---

## Suggested Sprint Phasing & Parallelization Plan

> [!TIP]
> Frontend sprints follow the dependency DAG from [`roadmap.md`](./roadmap.md). Parallelize tasks across developers within each sprint.

1. **Sprint FE-01** (Foundation & `@aether/core`): 
   - `TASK-FE-000` 🟡 (Monorepo Setup)
   - `TASK-FE-001` 🟢 (Zod Event Schemas)
   - `TASK-FE-002` 🟡 (Zustand Core Stores)
   - `TASK-FE-003` 🔴 (WebSocket Protocol Client)
   - `TASK-FE-004` 🔴 (Mock Cassette Replay Engine)
   - `TASK-FE-005` 🟡 (Shared Custom Hooks)
2. **Sprint FE-02** (CLI TUI Application — `apps/cli`):
   - `TASK-FE-010` 🟡 (Ink App Shell & `tsup`)
   - `TASK-FE-011` 🟢 (Terminal Progress & Budget Meter)
   - `TASK-FE-012` 🟡 (Terminal Turn Log Stream)
   - `TASK-013-FE` 🟢 (Terminal Gate Status & Taint Badges)
   - `TASK-014-FE` 🟡 (CLI Interactive Command Runner)
3. **Sprint FE-03** (Desktop GUI Canvas — `apps/desktop`):
   - `TASK-FE-020` 🟡 (Tauri v2 Desktop Shell)
   - `TASK-FE-021` 🟢 (Tailwind CSS v4 Design System)
   - `TASK-FE-022` 🔴 (`xyflow` Workflow Canvas Core)
   - `TASK-FE-023` 🔥 (Custom DAG Node & Edge Renderers — *Senior Specialist*)
   - `TASK-FE-024` 🔴 (Live Trace Inspector Panel)
4. **Sprint FE-04** (Advanced Views & Full Integration):
   - `TASK-FE-030` 🟡 (Monaco Side-by-Side Patch Diff Reviewer)
   - `TASK-FE-031` 🟡 (Self-Improvement & McNemar Dashboard)
   - `TASK-FE-032` 🟡 (Taint Gate Provenance Audit Panel)
   - `TASK-FE-033` 🔴 (Live Engine Integration & Replay Switch)
