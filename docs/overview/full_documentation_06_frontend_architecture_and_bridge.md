# AETHER Full Documentation — Part 6: Front-End Architecture, UI/UX & Bridge Contract

> **Original Source Documents:** [`docs_front/spec.md`](../../docs_front/spec.md), [`docs_front/BRIDGE_CONTRACT.md`](../../docs_front/BRIDGE_CONTRACT.md), [`docs_front/fixes/upcoming_backend_alignment.md`](../../docs_front/fixes/upcoming_backend_alignment.md), and [`docs_front/decisions/`](../../docs_front/decisions/).  
> **Purpose:** A complete, condensed reference specification for AETHER's front-end system architecture, `@aether/core` shared packages, Ink TUI CLI, Tauri v2 Desktop GUI, and bi-directional WebSocket/SSE bridge protocols.

---

## 1. Front-End Invariants (FI1 – FI5)

All front-end applications (`apps/cli`, `apps/desktop`) adhere to 5 binding architectural rules:

| # | Invariant | Description & Enforcement |
| :--- | :--- | :--- |
| **FI1** | **Headless Decoupling** | Zero direct imports from `src/aether/` inside `src_front/`. All interaction occurs via WebSocket / SSE over `engine.py`. Enforced by ESLint path boundaries. |
| **FI2** | **Single Source of Truth** | All shared React hooks, Zustand state stores, WebSocket clients, and TypeScript types reside in `@aether/core`. Enforced by Turborepo boundaries. |
| **FI3** | **Dual-Mode Mock Compatibility** | UI components operate seamlessly in `Live` mode or `Mock` (cassette replay) mode with zero conditional code in views. Enforced by Dependency Injection. |
| **FI4** | **Unprivileged Consumer** | The front-end has zero capability authorization bypasses. All user-requested actions pass through `kernel/dispatch.py` grants. |
| **FI5** | **Strict Event Schema Validation** | Inbound bridge events are validated against TypeScript types generated from `domain/events.py` using Zod schemas at the transport layer. |

---

## 2. Core Shared Package (`@aether/core`)

Located at `src_front/packages/core/`, this package provides all domain logic, state management, and stream drivers:

```
@aether/core
├── stores/
│   ├── useEngineStore     # WebSocket connection state, active run ID, raw event logs
│   ├── useWorkflowStore   # DAG nodes, edges, node execution states, active step
│   ├── useTaintStore      # Context spans and TaintGate provenance labels
│   ├── useBudgetStore     # Budget ledger (reserved, committed, remaining micro-USD)
│   ├── usePatchStore      # Pending code diffs from agent nodes
│   └── useMetricsStore    # Self-improvement scores and McNemar test results
├── hooks/
│   ├── useAetherStream    # Event stream subscription (live WS/SSE + mock replay)
│   ├── useTaintAudit      # TaintGate provenance inspection
│   ├── useNodeTrace       # Per-node execution trace and prompt inspection
│   └── useBudget          # Budget consumption and meter helpers
└── client/
    ├── AetherWebsocketClient  # Full-duplex WebSocket driver
    └── MockCassettePlayer     # Deterministic cassette replay player
```

---

## 3. UI Applications

### 3.1 TUI CLI (`src_front/apps/cli`)
* **Tech Stack**: React 19 + Ink + `@aether/core`.
* **Execution Environment**: Cross-platform terminal emulators (xterm-256color, PowerShell, bash).
* **Key Components**:
  * `<TurnLogStream />`: Live streaming view of LLM messages, tool calls, and outputs.
  * `<TaskProgressHeader />`: Active run ID, step indicator, and budget meters.
  * `<TaintAuditBadge />`: Visual context span provenance indicator (`trusted-system`, `untrusted-external`).
  * `<GateStatusIndicator />`: Tri-state verdict display (Passed ✓, Failed ✗, None ⚠ with instrument error detail).

### 3.2 Desktop GUI (`src_front/apps/desktop`)
* **Tech Stack**: Tauri v2 + React 19 + `xyflow` (React Flow) + Monaco Editor + Tailwind CSS + `@aether/core`.
* **Platform Support**: Windows 11/10 and Linux.
* **Key Views**:
  1. **Workflow Canvas View**: Interactive DAG node graph editor showing real-time step execution, repair loop unrolls ($k \le 3$), and socket connection compatibility.
  2. **Live Execution Trace Panel**: Embedded inspector showing prompt prefix layers (L1–L5), raw model completions, and tool execution outputs.
  3. **Code Diff Drawer**: Monaco Editor side-by-side patch reviewer with `AcceptDiff` and `RejectDiff` commands.
  4. **Self-Improvement Dashboard**: Statistical charts rendering exact McNemar paired test results, Holm–Bonferroni adjusted p-values, and cost deltas.

---

## 4. Bi-Directional Bridge Contract (`docs_front/BRIDGE_CONTRACT.md`)

Communication between the backend engine (`engine.py`) and front-end clients flows over a bi-directional WebSocket connection.

### 4.1 Canonical Bridge Event Envelope
```typescript
interface BridgeEvent {
  seq: number;                        // Monotonic sequence number within the run
  runId: string;                      // RunId UUID
  eventType: string;                  // Event type string matching domain/events.py
  at: string;                         // ISO 8601 UTC timestamp
  payload: Record<string, unknown>;   // Deserialized JSON payload
}
```

### 4.2 Key Core Event Types (Engine $\rightarrow$ Client)
* **Lifecycle**: `RunStarted`, `RunCompleted`, `RunFailed`.
* **Node Execution**: `NodeExecutionStarted`, `NodeExecutionFinished` (with `GateReport`), `NodeSkipped` (M2 memoization hit).
* **Streaming**: `ModelStreamDelta` (text, tool call deltas, usage stats).
* **Security & Taint Audit**: `EffectAuthorized`, `EffectDenied`, `TaintSpanEmitted`.
* **Budget Ledger**: `BudgetLeaseUpdated` (reserved, committed, remaining micro-USD), `BudgetOverrun`.

### 4.3 Outbound Commands (Client $\rightarrow$ Engine)
* `StartRun`: Enqueues run execution with specified topology hash, task ID, and `BudgetDims`.
* `CancelRun`: Immediately releases active leases and halts node execution.
* `AcceptDiff` / `RejectDiff`: Surfacing operator intent for code patches (applied through `dispatch.py` with `operator` provenance).

---

## 5. Deterministic Mock Cassette Engine (`@aether/mock-server`)

To enable front-end development independent of backend state, `MockCassettePlayer` replays recorded JSON cassette files (`.json`) byte-for-byte:
* Replays events in strict `offsetMs` chronological sequence.
* Implements the exact same stream interface as `AetherWebsocketClient`.
* Allows single-step forward debugging (`stepForward()`) and custom playback speed multipliers (`play(2.0)`).
* UI components consume live and mock streams identically via `useAetherStream()` with **zero view code modifications** (FI3).
