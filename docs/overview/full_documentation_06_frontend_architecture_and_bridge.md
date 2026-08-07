---
status: historical
retrieval: excluded
updated: 2026-08-07
superseded: 2026-08-07
---

# AETHER Full Documentation — Part 6: Front-End Architecture, UI/UX & Bridge Contract

> [!WARNING]
> **Stale snapshot. Not authoritative, and not maintained.**
>
> This folder is a hand-written re-rendering of documents that already have an
> authoritative home, which `README.md` names as the one thing this tree forbids:
> *"if you find the same thing stated in two places, the second one is the bug."*
> It has already drifted — it cites `docs/development/`, `docs/fixes/` and
> `docs/future_improvements/`, none of which exist, and Part 2 covers only ADRs
> 0001–0018 of 21.
>
> For anything binding read [`spec.md`](../spec.md), [`measurement.md`](../measurement.md),
> [`PHASE-0-LOCK.md`](../PHASE-0-LOCK.md), [`decisions/`](../decisions/README.md) and
> [`STATUS.md`](../STATUS.md). Tagged `retrieval: excluded` so no retrieval surfaces it
> and the link gate does not check it; see `TASK-084`.


> **Original Source Documents:** [`docs_front/spec.md`](../../docs_front/spec.md), [`docs_front/BRIDGE_CONTRACT.md`](../../docs_front/BRIDGE_CONTRACT.md), [`docs_front/architecture.md`](../../docs_front/architecture.md), [`docs_front/vision.md`](../../docs_front/vision.md), [`docs_front/development/`](../../docs_front/development/), [`docs_front/decisions/`](../../docs_front/decisions/), [`docs_front/workflows/`](../../docs_front/workflows/), [`docs_front/agile/`](../../docs_front/agile/), and [`docs_front/fixes/`](../../docs_front/fixes/).

---

## 1. Front-End Invariants (FI1 – FI5)

All front-end applications (`apps/cli`, `apps/desktop`) adhere to 5 binding architectural rules:

| # | Invariant | Description & Architectural Requirement | Mechanical Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **FI1** | **Headless Decoupling** | Zero direct imports from `src/aether/` inside `src_front/`. Interaction occurs strictly via WebSocket / SSE JSON-RPC over `engine.py`. | ESLint path boundary rules |
| **FI2** | **Single Source of Truth** | All shared React hooks, Zustand state stores, WebSocket clients, and TypeScript types reside in `@aether/core`. | Turborepo package boundaries |
| **FI3** | **Dual Bridge Mode** | Every UI component must render seamlessly under both `MOCK` (in-memory fixtures) and `LIVE` (real WebSocket bridge) modes. | Automated Storybook / Cypress test matrix |
| **FI4** | **Lossless vs. Lossy Streams** | Display UI consumes the lossy event stream (drop-oldest under backpressure); Trajectory Store consumes the lossless event log. | Engine bus channel separation |
| **FI5** | **Zero Unprivileged Authority** | Client applications hold zero capability grants. All authorization requests route to `kernel/dispatch.py`. | Architecture verification test |

---

## 2. Monorepo Architecture & Directory Layout (`src_front/`)

Front-end components are structured as a clean TypeScript monorepo under `src_front/`:

```
src_front/
├── apps/
│   ├── cli/             # Ink React Terminal UI (TUI) application
│   └── desktop/         # Tauri v2 + React 18 + @xyflow/react Desktop GUI
├── packages/
│   ├── core/            # @aether/core — shared Zustand stores, hooks, bridge client, types
│   ├── ui/              # Shared Tailwind CSS UI component library
│   └── mock-bridge/     # Replay cassette mock WebSocket server for offline testing
├── docs/                # Front-end specific documentation
└── package.json         # pnpm workspace configuration
```

---

## 3. Terminal UI (TUI) & Desktop GUI Architecture

```mermaid
graph TD
    Engine[engine.py Headless API] -->|JSON-RPC over WS / SSE| BridgeClient[BridgeClient (@aether/core)]
    BridgeClient -->|Zustand Store| Store[useAetherStore]
    Store --> TUI[apps/cli (Ink React TUI)]
    Store --> GUI[apps/desktop (Tauri v2 + @xyflow/react)]
```

### 3.1 Ink React TUI (`apps/cli`)
* **Technology Stack**: React 18 + Ink (`ink-spinner`, `ink-text-input`, `ink-select-input`).
* **Role**: Lightweight, terminal-native user interface providing real-time progress bars, node execution states, streaming LLM completions, and interactive decision prompts (`ASK_OPERATOR`).

### 3.2 Tauri v2 Desktop GUI (`apps/desktop`)
* **Technology Stack**: Tauri v2 (Rust shell) + React 18 + Vite + `@xyflow/react` + Tailwind CSS.
* **Role**: Visual workbench displaying live Workflow DAG topology graphs, node execution metrics, interactive diff inspection views, and real-time telemetry charts.

---

## 4. Bi-Directional Bridge Contract (`BRIDGE_CONTRACT.md`)

Communication between front-end interfaces (`src_front/`) and the Python backend (`src/aether/engine.py`) follows a strict JSON-RPC 2.0 protocol over WebSockets or SSE.

### 4.1 Request Protocol (Client $\rightarrow$ Server)

```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "aether.start_run",
  "params": {
    "topology_file": "workflows/linear_repair_v1.yaml",
    "task_id": "django__django-11099",
    "run_config": {
      "model_name": "qwen2.5-coder-32b",
      "temperature": 0.0,
      "max_repair_iterations": 3
    }
  }
}
```

### 4.2 Stream Event Protocol (Server $\rightarrow$ Client)

```json
{
  "jsonrpc": "2.0",
  "method": "aether.event_emitted",
  "params": {
    "sequence_id": 42,
    "timestamp": "2026-08-07T17:20:00Z",
    "event_type": "StepCompleted",
    "payload": {
      "step_id": "evaluate",
      "status": "PASSED",
      "gate_report": {
        "status": "PASSED",
        "test_command": "pytest tests/validation",
        "duration_ms": 1240
      }
    }
  }
}
```

### 4.3 Supported JSON-RPC Methods
* `aether.start_run`: Initializes and launches a workflow run.
* `aether.cancel_run`: Cancels an active run and revokes governor leases.
* `aether.submit_operator_decision`: Responds to an `ASK_OPERATOR` policy prompt.
* `aether.get_run_status`: Fetches current run state and sequence telemetry.

---

## 5. Mock vs. Live Dual-Mode Operations

To enable rapid UI iteration and offline testing, `@aether/core` implements a dual-mode bridge architecture:

* **`MOCK` Mode**: Intercepts WebSocket connections and streams pre-recorded replay cassettes (`packages/mock-bridge/`). Used in Storybook components, unit tests, and offline UI development.
* **`LIVE` Mode**: Establishes live WebSocket connection to `engine.py`. Parses real SSE deltas, telemetry events, and gate reports.

```typescript
// @aether/core Bridge Provider Initializer
export const createBridgeClient = (config: BridgeConfig): IBridgeClient => {
  if (config.mode === 'MOCK') {
    return new MockCassetteBridgeClient(config.cassetteFixture);
  }
  return new WebSocketBridgeClient(config.wsEndpoint);
};
```

---

## 6. Upcoming Backend Alignment & UI Accessibility Proposals

As documented in [`docs_front/fixes/upcoming_backend_alignment.md`](../../docs_front/fixes/upcoming_backend_alignment.md):

1. **Schema Version 1.1.0 Topology Alignment**: Update `@xyflow/react` graph parser to visually render expanded Topology Fragments (`TASK-060`) with nested node boundaries.
2. **Taint Gate Visual Indicators**: Display security provenance tags (`trusted-system`, `untrusted-external`) directly on file diffs and tool output panels.
3. **Accessibility (a11y) Compliance**: Ensure Ink TUI components adhere to terminal high-contrast modes and screen reader standards.
