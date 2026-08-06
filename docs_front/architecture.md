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
│   │   │   ├── stores/        # useEngineStore.ts, useWorkflowStore.ts, useTaintStore.ts
│   │   │   ├── hooks/         # useAetherStream.ts, useNodeTrace.ts, useBudget.ts
│   │   │   ├── types/         # events.ts, workflow.ts, budget.ts
│   │   │   └── index.ts
│   │   └── package.json
│   ├── ui-components/         # @aether/ui-components (Tailwind components)
│   │   ├── src/
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

State management is partitioned into three decoupled Zustand stores:

```typescript
// 1. Engine Store: Manages connection, active run ID, and raw event stream log
export const useEngineStore = create<EngineState>((set) => ({
  status: "disconnected",
  activeRunId: null,
  events: [],
  budget: { usdMicros: 0, promptTokens: 0, completionTokens: 0, wallClockMs: 0 },
  // Actions...
}));

// 2. Workflow Store: Manages active DAG nodes, edges, and node execution states
export const useWorkflowStore = create<WorkflowState>((set) => ({
  topologyId: "linear_repair_v1",
  nodes: [], // xyflow Node[] format
  edges: [], // xyflow Edge[] format
  selectedNodeId: null,
  // Actions...
}));

// 3. Taint Audit Store: Manages context spans and TaintGate labels
export const useTaintStore = create<TaintState>((set) => ({
  spans: [],
  inspectSpanId: null,
  // Actions...
}));
```
