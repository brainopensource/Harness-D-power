---
status: rationale
retrieval: excluded
updated: 2026-08-01
---
# SAGIHA & AETHER — Senior Frontend Architecture Prompt & Master Development Plan

> **System Prompt for Senior Frontend Engineer / AI Agent**  
> You are tasked with engineering a **world-class, high-performance, SOTA 2026 frontend infrastructure** for **SAGIHA** (the autonomous AI coding harness) and **AETHER** (the AGI multi-agent orchestrator and self-improvement system).  
>
> You will build **two distinct frontend applications**—a **Linux Desktop GUI** (Tauri v2 + Rust shell + React) and an **Interactive Terminal CLI/TUI** (Node + React Ink)—powered by a **shared, atomic, composable React component library** inside the existing pnpm Turborepo monorepo.

---

## 1. Executive Summary & Architectural Invariants

### 1.1 Architecture & Code Location
- **Workspace Monorepo Root:** [`frontend/`](../../frontend)
- **Desktop GUI App (`@sagiha/gui`):** [`frontend/apps/gui`](../../frontend/apps/gui) — Tauri v2 (Rust window host) + React 18+ / Vite / Tailwind CSS.
- **Terminal CLI App (`@sagiha/cli`):** [`frontend/apps/cli`](../../frontend/apps/cli) — Node ESM + React Ink (`ink`) for rich, interactive TUI directly inside terminal emulators.
- **Shared UI Library (`@sagiha/ui`):** [`frontend/packages/ui`](../../frontend/packages/ui) — Pure, reusable React component primitives, design tokens, charts, and layout components shared 100% between GUI and TUI adapters.
- **Shared Protocol & Client (`@sagiha/protocol`):** [`frontend/packages/protocol`](../../frontend/packages/protocol) — TypeScript schemas generated from Pydantic models in [`src/sagiha/domain/`](../../src/sagiha/domain), WebSocket client, REST client, and state hooks.
- **Mock Engine (`@sagiha/mock-engine`):** [`frontend/packages/mock-engine`](../../frontend/packages/mock-engine) — High-fidelity mock engine simulating real-time WebSocket event streams, step execution, and gate reports for features planned in future backend sprints.

### 1.2 Backend Reference & Ground Truth
- Backend microkernel and contracts are located in [`src/sagiha/`](../../src/sagiha).
- Reference specifications:
  - Roadmap & Sprint Plan: [`docs/implementation/development_plan_v2.md`](../implementation/development_plan_v2.md)
  - Refactoring & Contract Invariants: [`refactor_sagiha_v2_guidelines.md`](../implementation/refactor_sagiha_v2_guidelines.md)
  - Next-Gen Architecture Spec: [`docs/rationale/reviews/next_gen_architecture_specs.md`](../rationale/reviews/next_gen_architecture_specs.md)
  - AETHER AGI Evolution: [`docs/rationale/reviews/agi_evolution_path.md`](../rationale/reviews/agi_evolution_path.md)

---

## 2. Technical Stack & Design System (SOTA 2026)

### 2.1 Technology Stack
1. **Core UI Engine:** React 18+ with TypeScript (Strict mode enabled).
2. **State Management & Data Fetching:** Zustand for local/UI state; TanStack Query (`@tanstack/react-query`) for WebSocket event buffering and REST API sync.
3. **GUI Desktop Shell:** **Tauri v2** (Rust host) providing native Linux GTK container, low RAM footprint, native file dialogs, system tray integration, and hardware acceleration.
4. **CLI/TUI Shell:** **Ink 5+** (`react-ink`) utilizing custom terminal render primitives to share React state, custom hooks, and event handlers with the GUI.
5. **Styling & Aesthetics:** Modern Dark Mode, Tailwind CSS v4, custom HSL design tokens, subtle glassmorphism, micro-animations, monospace code viewers, and responsive grid layouts.

### 2.2 Atomic & Composable Component Hierarchy
All components must be written as **atomic, highly reusable blocks** inside `@sagiha/ui`:
- **Atoms:** Badges, Status Indicators (Idle, Running, Paused, Frozen, Tainted, Error), Metric Counters, Button Primitives, Input Fields, Monospace Labels.
- **Molecules:** Step Logs, Token Spend Gauges, Gate Compliance Cards, Taint Warnings, Code Diff Viewers, Context Layer Chips.
- **Organisms:** Workflow DAG Editors, Context Stack Visualizers, Memory & Tree-Sitter Graph Viewers, Benchmark Performance Comparison Tables.
- **Templates / Screens:** Agent Cockpit, Story Board, System Governor Dashboard, Trace Exporter & Dataset Inspector, AETHER Swarm Overview.

---

## 3. Harness & AETHER Capability Control Surface

The frontend cockpit must give the user total visibility and granular control over all harness features:

### 3.1 Agent Execution & Steering Control
- **State Controls:** Run, Pause (`FrozenRunState`), Resume, Stop, and Step-by-Step Execution.
- **Interrupt & Steer:** Exchange-boundary steering by appending instructions to the tail prompt (preserving prompt cache Layers 1–7).
- **TaintGate & Safety Approval:** Visual indicator when untrusted external content (`<untrusted-data>`) triggers `requires_human=True` for mutation tools (`apply_edit`, `write_file`, `run_command`); one-click approval/rejection.

### 3.2 Context & Memory Inspector
- **Prompt Stack Visualizer:** Live breakdown of Layers 1–7 (System Prompt, System Policy, Memory, Repository Context, User Spec, Anchored State, Trajectory History).
- **Token Budget & Governor Gauge:** Real-time token spend tracking ($/1M tokens, step limits, wall-clock timer, governor ceiling).
- **Exchange Compactor View:** Visual indicator showing exchange-granular compaction, token headroom (20%), and summary turns.

### 3.3 Workflow & Story-DAG Graph
- **Visual DAG Graph:** Interactive node-graph showing macro stories, subtasks, dependency edges, and inner-loop coding steps.
- **Integration & Conflict Resolution:** Visualization of `IntegrationStep` rebase checks, gate reports, and `ResolveConflictTask` hunk-confined repairs.

### 3.4 Code Intelligence & Data Exporter
- **Tree-Sitter Code Graph:** Interactive symbol tree (`find_symbols`), file skeletons (`get_skeleton`), and impact analysis (`impacted_by`).
- **Trace Exporter:** Inspector for bench cassettes and run traces, exporting schema-valid SFT and DPO JSONL datasets for LLM fine-tuning.

---

## 4. Master Development Plan & TODO Checklist

Execute the following development plan sequentially. Mark tasks as done (`- [x]`) only after implementation, typecheck (`pnpm typecheck`), linting (`pnpm lint`), and unit testing (`pnpm test`) pass completely.

---

### Sprint FE-0 — Audit, Task Wave Mapping & Master TODO Ledger Setup

- [x] **Task FE-0.1 — Codebase & Protocol Contract Audit**
  - Conduct a complete audit of `frontend/` monorepo structure, `@sagiha/protocol` types, and `src/sagiha/domain/` Pydantic models.
  - Verify alignment with [`refactor_sagiha_v2_guidelines.md`](../implementation/refactor_sagiha_v2_guidelines.md) and [`development_plan_v2.md`](../implementation/development_plan_v2.md).

- [x] **Task FE-0.2 — Task Wave Mapping & Execution Briefing**
  - Map out the execution waves and dependencies across all packages:
    - **Wave 1:** Shared UI Tokens & Domain Protocol Schemas (`@sagiha/ui`, `@sagiha/protocol`)
    - **Wave 2:** High-Fidelity Mock Engine & Event Transport (`@sagiha/mock-engine`)
    - **Wave 3:** Interactive Terminal TUI Cockpit (`@sagiha/cli` with React Ink)
    - **Wave 4:** Native Linux Desktop GUI Shell (`@sagiha/gui` with Tauri v2 + React)
    - **Wave 5:** Advanced Cockpit Visualizers (Story-DAG, Context Inspector, Taint Gate Approval)
    - **Wave 6:** AETHER Swarm Overview, Optimization & Final Verification
  - Document risk factors, component reusability targets (≥ 80% shared primitives), and bundle size ceilings.

- [x] **Task FE-0.3 — Master TODO Ledger Initialization**
  - Verify that every sprint task across Sprint FE-0 to FE-6 has an explicit checkbox (`- [ ]`).
  - Establish the rule that tasks must be updated to `- [x]` immediately upon full completion and test verification.

---

### Sprint FE-1 — Shared Design System & Protocol Primitives (`@sagiha/ui` & `@sagiha/protocol`)

- [x] **Task FE-1.1 — Design Tokens & HSL Theme System**
  - Path: `frontend/packages/ui/src/tokens/`
  - Implement color tokens (Cyber Dark `#0A0D14`, Neon Violet `#8B5CF6`, Taint Emerald `#10B981`, Warning Amber `#F59E0B`, Danger Crimson `#EF4444`).
  - Configure Tailwind CSS v4 in `@sagiha/ui`.

- [x] **Task FE-1.2 — Domain Protocol Schemas & TypeScript Types**
  - Path: `frontend/packages/protocol/src/schemas/`
  - Re-export Pydantic domain models from `src/sagiha/domain/`: `RunContext`, `GateReport`, `TokenUsage`, `CostSummary`, `FrozenRunState`, `TrajectoryStep`, `TaskSpec`, `StoryBoard`.

- [x] **Task FE-1.3 — Core UI Atomic Components**
  - Path: `frontend/packages/ui/src/components/atoms/`
  - Build `StatusBadge` (Idle/Running/Frozen/Tainted), `TokenGauge`, `MetricCard`, `CodeSnippet`, `Button`, `IconButton`.

- [x] **Task FE-1.4 — Unit Test Suite for Shared Components**
  - Path: `frontend/packages/ui/src/__tests__/`
  - Verify rendering and props using `@testing-library/react` and `vitest`.

---

### Sprint FE-2 — `@sagiha/mock-engine` & WebSocket Transport

- [x] **Task FE-2.1 — Mock Event Stream Generator**
  - Path: `frontend/packages/mock-engine/src/simulator.ts`
  - Simulate real-time backend WebSocket events (`StepCompleted`, `CompactionApplied`, `TaintIntroduced`, `GateEvaluated`, `ProviderFailover`).

- [x] **Task FE-2.2 — Unified Client & Zustand State Store**
  - Path: `frontend/packages/protocol/src/client/` & `frontend/packages/protocol/src/store/`
  - Build `SagihaClient` supporting WebSocket streaming and REST fallback.
  - Implement Zustand store (`useHarnessStore`) for run control, step history, memory inspection, and gate status.

- [x] **Task FE-2.3 — Integration Tests for Protocol Store**
  - Path: `frontend/packages/protocol/src/__tests__/`
  - Verify state updates under high-throughput simulated event streams.

---

### Sprint FE-3 — Terminal TUI Cockpit (`@sagiha/cli` with React Ink)

- [x] **Task FE-3.1 — TUI Primitives Adapter**
  - Path: `frontend/apps/cli/src/components/`
  - Wrap Ink components (`<Box>`, `<Text>`, `<Spinner>`) to consume `@sagiha/ui` design tokens and state models.

- [x] **Task FE-3.2 — Interactive Agent Cockpit TUI**
  - Path: `frontend/apps/cli/src/views/CockpitView.tsx`
  - Display live execution step log, token spend counter, active tools, and gate status.

- [x] **Task FE-3.3 — Keyboard Navigation & Steering Input**
  - Path: `frontend/apps/cli/src/views/SteerInput.tsx`
  - Implement keyboard shortcuts (`[P]` Pause/Freeze, `[R]` Resume, `[S]` Steer/Interrupt, `[A]` Approve Taint Mutation, `[Q]` Quit).

- [x] **Task FE-3.4 — CLI Build & Smoke Tests**
  - Path: `frontend/apps/cli/src/__tests__/`
  - Verify CLI build (`pnpm --filter @sagiha/cli build`) and execution under `ink-testing-library`.

---

### Sprint FE-4 — Linux Desktop GUI Shell (`@sagiha/gui` with Tauri v2 + React)

- [x] **Task FE-4.1 — Tauri v2 Shell Configuration**
  - Path: `frontend/apps/gui/src-tauri/`
  - Configure native Linux window settings, titlebar styling, system tray, and Rust IPC handlers.

- [x] **Task FE-4.2 — Main Navigation Layout & Sidebar**
  - Path: `frontend/apps/gui/src/layouts/MainLayout.tsx`
  - Build collapsible sidebar with navigation: Cockpit, Story-DAG, Context & Memory, Code Intelligence, Governor & Benchmarks, AETHER Swarm.

- [x] **Task FE-4.3 — Real-Time Agent Control Dashboard**
  - Path: `frontend/apps/gui/src/views/CockpitDashboard.tsx`
  - Implement control panel: Run/Pause/Resume buttons, live event stream feed, spend ledger, step timeline, and tool call breakdown.

- [x] **Task FE-4.4 — GUI Build & Vitest Verification**
  - Path: `frontend/apps/gui/src/__tests__/`
  - Run `pnpm --filter @sagiha/gui build` and verify green build output.

---

### Sprint FE-5 — Advanced Cockpit Visualizers

- [x] **Task FE-5.1 — Story-DAG & Workflow Node Editor**
  - Path: `frontend/apps/gui/src/views/DagVisualizer.tsx`
  - Render interactive node-graph of stories, subtasks, disjoint code closures, and gate checkpoints using TanStack Flow / SVG graph engine.

- [x] **Task FE-5.2 — Prompt Layer & Exchange Compactor Inspector**
  - Path: `frontend/apps/gui/src/views/ContextInspector.tsx`
  - Visual breakdown of Layers 1–7, token headroom gauge (20%), prefix digest cache hits, and summary turns.

- [x] **Task FE-5.3 — Safety & Monotonic Taint Approval UI**
  - Path: `frontend/apps/gui/src/views/TaintApprovalModal.tsx`
  - Display untrusted data source envelope (`<untrusted-data>`) and pending mutation requests (`apply_edit`, `write_file`) requiring human approval.

- [x] **Task FE-5.4 — Code Intelligence & Tree-Sitter Viewer**
  - Path: `frontend/apps/gui/src/views/CodeIntelView.tsx`
  - Render symbol tree, file skeletons, and AST call/import edges with search filter.

- [x] **Task FE-5.5 — Benchmark & Dataset Exporter View**
  - Path: `frontend/apps/gui/src/views/ExporterView.tsx`
  - Display A/A floor metrics, BoN pass rates, cassette player, and export options for SFT/DPO JSONL datasets.

---

### Sprint FE-6 — AETHER Swarm Orchestrator & Final Polish

- [x] **Task FE-6.1 — AETHER Swarm & Self-Improvement Overview**
  - Path: `frontend/apps/gui/src/views/AetherSwarmView.tsx`
  - Multi-agent swarm topology monitor, memory exchange graph, and Conductor self-evolution stats.

- [x] **Task FE-6.2 — Performance Tuning & Bundle Optimization**
  - Code splitting, dynamic imports for heavy visualizers, asset optimization, zero-lag WebSocket rendering.

- [x] **Task FE-6.3 — Comprehensive Monorepo Verification**
  - Run `pnpm typecheck && pnpm lint && pnpm test` across all packages (`@sagiha/ui`, `@sagiha/protocol`, `@sagiha/mock-engine`, `@sagiha/cli`, `@sagiha/gui`).

---

## 5. Verification Protocol & Definition of Done

Each sprint task MUST meet the following criteria before being marked as done (`- [x]`):
1. **Zero Type Errors:** `pnpm typecheck` passes cleanly across the monorepo.
2. **Zero Linter Warnings:** `pnpm lint` (Biome / ESLint) passes with zero errors.
3. **Tests Passing:** `pnpm test` passes all unit and integration tests.
4. **Build Verification:** `pnpm build` succeeds for both `@sagiha/cli` and `@sagiha/gui`.
