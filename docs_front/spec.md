---
status: normative
updated: 2026-08-06
---

# Front-End Normative Specification (`docs_front/spec.md`)

This document states the binding invariants and structural rules governing the AETHER front-end applications.

---

## 1. System Invariants

| # | Invariant | Enforcement |
| :--- | :--- | :--- |
| **FI1** | **Headless Decoupling.** Zero direct imports from `src/aether/` inside `src_front/`. All interaction occurs via WebSocket / SSE messages over `engine.py`. | Monorepo import linter (`@typescript-eslint` path boundaries) |
| **FI2** | **Single Source of Truth.** All shared React hooks, state stores, WebSocket protocol clients, and data models reside in `src_front/packages/core/`. | Turborepo package boundaries |
| **FI3** | **Dual-Mode Mock Compatibility.** Every UI component must operate seamlessly in `Live` mode or `Mock` (cassette replay) mode without conditional code inside views. | Mock Provider Dependency Injection |
| **FI4** | **Unprivileged Consumer.** The front-end possesses zero capability authorization bypasses; actions requested by the user pass through `kernel/dispatch.py` grants. | Engine Event Bus Protocol |
| **FI5** | **Strict Event Schema Validation.** Incoming events are validated against TypeScript types generated from `domain/events.py`. | Zod schema validation at bridge boundary |

---

## 2. Shared Engine Package (`packages/core`)

All front-end applications (`apps/cli` and `apps/desktop`) import foundational state and hooks from `@aether/core`:

```typescript
// packages/core export structure

// Stores — one per state domain
export * from "./stores/useEngineStore";      // connection, active run, raw event log
export * from "./stores/useWorkflowStore";    // DAG nodes, edges, node execution states
export * from "./stores/useTaintStore";       // context spans and TaintGate provenance labels
export * from "./stores/useBudgetStore";      // budget ledger (reserved/committed/remaining)
export * from "./stores/usePatchStore";       // pending code diffs from agent nodes
export * from "./stores/useMetricsStore";     // self-improvement scores, A/B test results

// Hooks
export * from "./hooks/useAetherStream";      // event stream subscription (live + mock)
export * from "./hooks/useTaintAudit";        // taint provenance inspection
export * from "./hooks/useNodeTrace";         // per-node execution trace
export * from "./hooks/useBudget";            // budget consumption helpers

// Clients
export * from "./client/AetherWebsocketClient";
export * from "./client/MockCassettePlayer";

// Types (CI-generated from domain/events.py)
export * from "./types/events";
export * from "./types/workflow";
export * from "./types/budget";
export * from "./types/gate";                 // GateStatus, GateReport, Provenance
```

---

## 3. UI Application Requirements

### 3.1 TUI CLI (`src_front/apps/cli`)
* **Technology Stack**: React 19 + Ink + `@aether/core`.
* **Execution Surface**: Runs inside standard terminal emulators (Windows PowerShell/CMD, Linux bash/zsh, xterm-256color).
* **Key Components**:
  * `<TurnLogStream />`: Live streaming view of model messages, tool calls, and execution outputs.
  * `<TaskProgressHeader />`: Active run ID, budget meter (micro-USD, prompt/completion tokens, wall-clock ms), and active step indicator.
  * `<TaintAuditBadge />`: Visual label indicating context span provenance.
  * `<GateStatusIndicator />`: Tri-state rendering — `PASSED` (green ✓), `FAILED` (red ✗), `NONE` (amber ⚠ with instrument error detail).

### 3.2 Desktop GUI (`src_front/apps/desktop`)
* **Technology Stack**: Tauri v2 + React 19 + `xyflow` (React Flow) + Monaco Editor + Tailwind CSS + `@aether/core`.
* **Platform Target**: Windows 11 / 10 (`x86_64-pc-windows-msvc`) and Linux (`x86_64-unknown-linux-gnu`).
* **Key Views**:
  1. **Workflow Canvas View**: Full n8n/ComfyUI-style node graph editor with interactive connection handles, socket type checks, and mini-map. Custom edge rendering for conditional routing (`on_pass` green, `on_fail` red, `on_instrument_error` amber). Repair loop subgraphs rendered with bounded iteration badge. Fan-out sites rendered with candidate count and sequencing indicator.
  2. **Live Execution Trace Panel**: Embedded turn-by-turn inspector showing prompt prefix layers (L1–L5), raw LLM completions, and tool executions. Node gate reports rendered with tri-state `GateStatus` (Passed/Failed/None with instrument error detail).
  3. **Code Diff Drawer**: Monaco Editor side-by-side patch reviewer with `AcceptDiff` / `RejectDiff` command integration.
  4. **Self-Improvement Dashboard**: Statistical charts rendering A/B McNemar test results, Holm–Bonferroni adjusted p-values, and cost deltas.
