---
status: normative
updated: 2026-08-06
---

# Front-End Monorepo Architecture (`docs_front/architecture.md`)

This specification details the package design, directory layout, technology stack choices, and component trees for `src_front/`.

---

## 1. Monorepo Topology (`src_front`)

```
src_front/
├── pnpm-workspace.yaml
├── package.json
├── turbo.json
├── packages/
│   ├── core/                  # @aether/core (Zustand stores, hooks, WS client, event schemas)
│   │   ├── src/
│   │   │   ├── client/        # AetherWebsocketClient.ts, MockCassettePlayer.ts
│   │   │   ├── stores/        # useEngineStore.ts, useWorkflowStore.ts, useTaintStore.ts,
│   │   │   │                  # useBudgetStore.ts, usePatchStore.ts, useMetricsStore.ts
│   │   │   ├── hooks/         # useAetherStream.ts, useNodeTrace.ts, useBudget.ts
│   │   │   ├── types/         # events.ts, workflow.ts, budget.ts
│   │   │   └── index.ts
│   │   └── package.json
│   ├── ui-components/         # @aether/ui-components (Desktop-GUI-only Tailwind components)
│   │   ├── src/               # NOT consumed by apps/cli (Ink uses its own primitives)
│   │   │   ├── Button.tsx, Card.tsx, Badge.tsx, Modal.tsx, DiffViewer.tsx
│   │   │   └── index.ts
│   │   └── package.json
│   └── mock-server/           # @aether/mock-server (Pre-recorded event stream cassettes)
│       ├── cassettes/         # swe_bench_pass.json, repair_loop_ablation.json
│       └── index.ts
└── apps/
    ├── cli/                   # @aether/cli (React + Ink TUI)
    │   ├── src/
    │   │   ├── components/    # TurnLogStream.tsx, Header.tsx, StepProgress.tsx
    │   │   ├── index.tsx      # CLI Entry point
    │   │   └── App.tsx
    │   └── package.json
    └── desktop/               # @aether/desktop (Tauri v2 + React 19 + xyflow)
        ├── src-tauri/         # Tauri v2 Rust desktop shell
        │   ├── Cargo.toml
        │   └── src/main.rs
        ├── src/               # React 19 SPA
        │   ├── components/
        │   │   ├── canvas/    # WorkflowCanvas.tsx, CustomNode.tsx, SocketHandle.tsx
        │   │   ├── trace/     # LiveTraceInspector.tsx, SpanViewer.tsx
        │   │   ├── diff/      # MonacoDiffEditor.tsx
        │   │   └── metrics/   # McNemarChart.tsx, BudgetMeter.tsx
        │   ├── App.tsx
        │   └── main.tsx
        └── package.json
```

---

## 2. Technology Stack Selection Rationale

### 2.1 TUI CLI Stack: React 19 + Ink
* **Rationale**: Ink provides declarative, component-driven terminal UIs in React JSX. AI models possess extensive React component training data, resulting in faster iteration and lower code verbosity compared to native Rust TUI frameworks.
* **Layout Engine**: Yoga Flexbox layout engine (`<Box>`, `<Text>`).
* **Packaging**: Compiled via `tsup` into a clean Node.js executable script (`aether-cli`).

### 2.2 Desktop GUI Stack: Tauri v2 + React 19 + `xyflow` + Monaco Editor
* **Desktop Frame**: **Tauri v2 (Rust)**. Uses native OS webviews (Webview2 on Windows, WebKitGTK on Linux). Installer $< 15\text{ MB}$, RAM $< 40\text{ MB}$.
* **Canvas Engine**: **`xyflow` (React Flow)**. Standard for n8n/ComfyUI-style workflow builders. Provides drag-and-drop nodes, custom handles, sub-flows, and automatic graph layout.
* **Code Editor**: **Monaco Editor** (`@monaco-editor/react`) for side-by-side patch diffing and syntax highlighting.
* **Styling**: **Tailwind CSS v4** with glassmorphism, dark-mode themes, and dynamic micro-animations.

---

## 3. Zustand Store Architecture (`@aether/core`)

State management is partitioned into **six** decoupled Zustand stores, one per domain:

```typescript
// 1. Engine Store: connection lifecycle, active run, raw event stream log
export const useEngineStore = create<EngineState>((set) => ({
  status: "disconnected",
  activeRunId: null,
  events: [],
  // Actions...
}));

// 2. Workflow Store: DAG topology, nodes, edges, execution states
export const useWorkflowStore = create<WorkflowState>((set) => ({
  topologyId: "linear_repair_v1",
  nodes: [],              // xyflow Node[] with GateStatus per node
  edges: [],              // xyflow Edge[] with conditional routing metadata
  repairLoops: [],        // { fromNode, viaNodes, backTo, maxIterations, currentIteration }
  fanOutSites: [],        // { nodeId, n, cacheSequencing, candidateStatuses }
  selectedNodeId: null,
  // Actions...
}));

// 3. Budget Store: reserve/commit/release ledger (integer BudgetDims)
export const useBudgetStore = create<BudgetState>((set) => ({
  reserved: { usdMicros: 0, promptTokens: 0, completionTokens: 0, wallClockMs: 0, concurrencySlots: 0 },
  committed: { usdMicros: 0, promptTokens: 0, completionTokens: 0, wallClockMs: 0, concurrencySlots: 0 },
  remaining: { usdMicros: 0, promptTokens: 0, completionTokens: 0, wallClockMs: 0, concurrencySlots: 0 },
  overruns: [],
  // Actions...
}));

// 4. Patch Store: pending code diffs from agent nodes
export const usePatchStore = create<PatchState>((set) => ({
  pendingDiffs: [],       // { diffId, filePath, hunks, status: "pending" | "accepted" | "rejected" }
  // Actions: acceptDiff(diffId, hunks?), rejectDiff(diffId, reason?)
}));

// 5. Metrics Store: self-improvement scores and A/B test results
export const useMetricsStore = create<MetricsState>((set) => ({
  currentScores: {},      // { [metricName]: number }
  history: [],            // time-series for dashboard charts
  abResults: [],          // McNemar p-values, Holm–Bonferroni CIs
  // Actions...
}));

// 6. Taint Audit Store: context spans and TaintGate provenance labels
export const useTaintStore = create<TaintState>((set) => ({
  spans: [],              // TaintSpan[] with Provenance labels
  inspectSpanId: null,
  // Actions...
}));
```

---

## 4. DAG Topology Rendering Specification

The `useWorkflowStore` maps backend topology concepts to visual elements. These rendering rules apply to both Desktop GUI (xyflow) and CLI (simplified text representation).

### 4.1 Node Rendering

Each node displays its `nodeKind` (from `workflow_schema.yaml`) and its current `GateStatus`:

| GateStatus | Desktop Visual | CLI Visual |
| :--- | :--- | :--- |
| Idle (not yet executed) | Gray node, no border glow | `[ ]` prefix |
| Running | Animated blue pulse border | `[▶]` prefix, spinner |
| `PASSED` | Green border, checkmark icon | `[✓]` green |
| `FAILED` | Red border, cross icon | `[✗]` red |
| `NONE` (instrument error) | Amber border, warning icon + tooltip with `instrumentError` | `[⚠]` amber |

### 4.2 Edge Rendering (Conditional Routing)

Edges carry a `when` predicate from the topology schema:

| `when` value | Desktop Edge Style | CLI Representation |
| :--- | :--- | :--- |
| `always` | Solid gray line | `→` |
| `on_pass` | Solid green line | `→(pass)` |
| `on_fail` | Dashed red line | `→(fail)` |
| `on_instrument_error` | Dotted amber line (must terminate at flag node) | `→(err!)` |

### 4.3 Repair Loop Rendering

Repair loops (from `topology.repair` block) are rendered as:
- **Desktop**: Dashed bounding box around `viaNodes`, with a badge showing `iteration {current}/{maxIterations}`.
- **CLI**: Indented sub-section with iteration counter.

### 4.4 Fan-Out / Best-of-N Rendering

Fan-out sites (from `topology.fanOut`) are rendered as:
- **Desktop**: Fan-out node expands to show N candidate lanes with individual status indicators. `cacheSequencing` shown as tooltip.
- **CLI**: Numbered candidate list with pass/fail markers.
