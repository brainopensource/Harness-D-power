---
status: rationale
updated: 2026-08-06
---

# CORE_SKELETONS_AND_PROTOCOLS (Front-End) — Pre-Phase 1 Engineering Specification

**Owners**: Tech Leads (Front-End · Infrastructure)
**Standing**: pseudocode-grade skeletons. When these land in `src_front/packages/core/` and applications, **the code becomes the contract and this file stops being authoritative** (house rule: documents navigate, code defines).

> **Conformance note on Event schemas.** The schema rules enforced by the CI drift check ensure that front-end event types exactly match those generated from the backend `domain/events.py`. The front-end is an **unprivileged consumer** (FI-4) and strictly validates incoming payloads via Zod schemas (FI-5).

---

## 0. Package scaffolding

```text
src_front/packages/core/src/
├── client/
│   ├── AetherWebsocketClient.ts
│   ├── BridgeDriver.ts
│   ├── MockCassettePlayer.ts
│   └── SSEClient.ts
├── hooks/
│   ├── useAetherStream.ts
│   ├── useBridge.ts
│   ├── useBudget.ts
│   ├── useCurrentPhase.ts
│   ├── useDiffs.ts
│   ├── useNodeGraph.ts
│   ├── useNodeTrace.ts
│   └── useTaintAudit.ts
├── stores/
│   ├── useBudgetStore.ts
│   ├── useEngineStore.ts
│   ├── useMetricsStore.ts
│   ├── usePatchStore.ts
│   ├── useTaintStore.ts
│   └── useWorkflowStore.ts
├── types/
│   ├── budget.ts
│   ├── events.ts
│   ├── gate.ts
│   └── workflow.ts
└── index.ts
```

---

## 1. Domain Types (`types/`)

```typescript
// types/events.ts
import { z } from "zod";
import { BudgetDims } from "./budget";
import { GateReport, Provenance } from "./gate";

export interface BridgeEvent<T extends string = string, P = Record<string, unknown>> {
  seq: number;
  runId: string;
  eventType: T;
  at: string; // ISO 8601 UTC
  payload: P;
}

// Discriminator Union (Provisional - to be CI-generated from backend)
export type EventType =
  | "RunStarted" | "RunCompleted" | "RunFailed"
  | "NodeExecutionStarted" | "NodeExecutionFinished" | "NodeSkipped"
  | "ModelStreamDelta" | "EffectAuthorized" | "EffectDenied"
  | "TaintSpanEmitted" | "BudgetLeaseUpdated" | "BudgetOverrun";

export interface RunStartedPayload {
  taskId: string;
  manifestHash: string;
  topologyHash: string;
  budget: BudgetDims;
}

export interface NodeExecutionFinishedPayload {
  nodeId: string;
  gateReport: GateReport;
  costActuals: BudgetDims;
}

// ... other payload interfaces
```

```typescript
// types/gate.ts
export enum GateStatus {
  PASSED = "passed",
  FAILED = "failed",
  NONE = "none",
}

export interface GateReport {
  gate: string;
  status: GateStatus;
  detail: string;
  instrumentError: string | null;
}

export enum Provenance {
  TRUSTED_SYSTEM = "trusted-system",
  OPERATOR = "operator",
  AGENT = "agent",
  UNTRUSTED_EXTERNAL = "untrusted-external",
  UNTRUSTED_DERIVED = "untrusted-derived",
}
```

```typescript
// types/budget.ts
export interface BudgetDims {
  usdMicros: number;
  promptTokens: number;
  completionTokens: number;
  wallClockMs: number;
  concurrencySlots: number;
}

export interface Lease {
  leaseId: string;
  runId: string;
  reserved: BudgetDims;
  parent: string | null;
  issuedAt: string;
}
```

```typescript
// types/workflow.ts
import { GateStatus } from "./gate";

export interface WorkflowNode {
  id: string;
  kind: string;
  label: string;
  status: GateStatus | "idle" | "running";
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  when: "always" | "on_pass" | "on_fail" | "on_instrument_error";
}

export interface RepairLoop {
  fromNode: string;
  viaNodes: string[];
  backTo: string;
  maxIterations: number;
  currentIteration: number;
}

export interface FanOutSite {
  nodeId: string;
  n: number;
  cacheSequencing: boolean;
  candidateStatuses: Array<GateStatus | "running" | "idle">;
}

export interface TopologyState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  repairLoops: RepairLoop[];
  fanOutSites: FanOutSite[];
}
```

---

## 2. Bridge Driver Protocol

```typescript
// client/BridgeDriver.ts
import { BridgeEvent } from "../types/events";

export type ConnectionState = "disconnected" | "connecting" | "connected" | "reconnecting";

export interface BridgeDriver {
  /** Connect to the engine or mock stream */
  connect(): Promise<void>;
  
  /** Disconnect and cleanup */
  disconnect(): void;
  
  /** Subscribe to events. Returns an unsubscribe function. */
  subscribe(callback: (event: BridgeEvent) => void): () => void;
  
  /** Send a command to the engine */
  send(commandType: string, payload: Record<string, unknown>): Promise<void>;
  
  /** Get current connection status */
  get status(): ConnectionState;
}
```

```typescript
// client/AetherWebsocketClient.ts
export class AetherWebsocketClient implements BridgeDriver {
  private ws: WebSocket | null = null;
  private listeners: Set<(event: BridgeEvent) => void> = new Set();
  public status: ConnectionState = "disconnected";

  async connect(): Promise<void> {
    this.status = "connecting";
    // ... initialize WebSocket, attach onmessage, handle reconnects
  }

  disconnect(): void { /* ... */ }
  
  subscribe(cb: (event: BridgeEvent) => void): () => void {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  async send(commandType: string, payload: Record<string, unknown>): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ commandType, payload }));
    }
  }
}
```

```typescript
// client/SSEClient.ts
export class SSEClient implements BridgeDriver {
  // Read-only implementation for web fallback
  // send() throws "Not Supported in SSE"
}
```

```typescript
// client/MockCassettePlayer.ts
export class MockCassettePlayer implements BridgeDriver {
  public status: ConnectionState = "connected"; // instantly connected
  private position: number = 0;
  private timer: NodeJS.Timeout | null = null;

  async connect(): Promise<void> { /* Load cassette */ }
  disconnect(): void { /* Stop timer */ }
  subscribe(cb: (event: BridgeEvent) => void): () => void { /* ... */ }
  
  async send(commandType: string, payload: Record<string, unknown>): Promise<void> {
    // Commands in mock mode might mutate local store directly or be ignored
    console.log(`Mock command swallowed: ${commandType}`, payload);
  }

  // Mock specific APIs
  play(speedMultiplier: number = 1.0): void { /* ... */ }
  pause(): void { /* ... */ }
  stepForward(): void { /* Emit exactly one event */ }
}
```

---

## 3. Zustand Store Skeletons

```typescript
// stores/useEngineStore.ts
import { create } from "zustand";
import { BridgeEvent } from "../types/events";
import { ConnectionState } from "../client/BridgeDriver";

interface EngineState {
  status: ConnectionState;
  activeRunId: string | null;
  events: BridgeEvent[];
  
  setStatus: (status: ConnectionState) => void;
  setActiveRunId: (id: string | null) => void;
  appendEvent: (event: BridgeEvent) => void;
  clear: () => void;
}

export const useEngineStore = create<EngineState>((set) => ({
  status: "disconnected",
  activeRunId: null,
  events: [],
  setStatus: (status) => set({ status }),
  setActiveRunId: (id) => set({ activeRunId: id }),
  appendEvent: (event) => set((state) => ({ events: [...state.events, event] })),
  clear: () => set({ events: [], activeRunId: null }),
}));
```

```typescript
// stores/useWorkflowStore.ts
import { create } from "zustand";
import { TopologyState, WorkflowNode, WorkflowEdge, RepairLoop, FanOutSite } from "../types/workflow";
import { GateStatus } from "../types/gate";

interface WorkflowState extends TopologyState {
  selectedNodeId: string | null;
  
  updateNodeStatus: (nodeId: string, status: GateStatus | "running") => void;
  incrementRepairIteration: (nodeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  initializeTopology: (topo: TopologyState) => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  nodes: [],
  edges: [],
  repairLoops: [],
  fanOutSites: [],
  selectedNodeId: null,
  updateNodeStatus: (id, status) => set((s) => ({
    nodes: s.nodes.map(n => n.id === id ? { ...n, status } : n)
  })),
  // ...
}));
```

```typescript
// stores/useBudgetStore.ts
import { create } from "zustand";
import { BudgetDims } from "../types/budget";

interface BudgetState {
  reserved: BudgetDims;
  committed: BudgetDims;
  remaining: BudgetDims;
  overruns: { leaseId: string; reserved: BudgetDims; actuals: BudgetDims }[];
  
  updateLease: (reserved: BudgetDims, committed: BudgetDims, remaining: BudgetDims) => void;
  recordOverrun: (leaseId: string, reserved: BudgetDims, actuals: BudgetDims) => void;
}

export const useBudgetStore = create<BudgetState>((set) => ({
  // ... initial state and actions
}));
```

```typescript
// stores/usePatchStore.ts
import { create } from "zustand";

interface PatchState {
  pendingDiffs: { diffId: string; filePath: string; hunks: string; status: "pending" | "accepted" | "rejected" }[];
  acceptDiff: (diffId: string, hunks?: number[]) => void;
  rejectDiff: (diffId: string, reason?: string) => void;
}
export const usePatchStore = create<PatchState>(/* ... */);

// stores/useMetricsStore.ts
import { create } from "zustand";

interface MetricsState {
  currentScores: Record<string, number>;
  history: { timestamp: string; metrics: Record<string, number> }[];
  abResults: { pValue: number; ci: [number, number]; significant: boolean }[];
}
export const useMetricsStore = create<MetricsState>(/* ... */);

// stores/useTaintStore.ts
import { create } from "zustand";
import { TaintSpan } from "../types/gate";

interface TaintState {
  spans: TaintSpan[];
  inspectSpanId: string | null;
  addSpan: (span: TaintSpan) => void;
}
export const useTaintStore = create<TaintState>(/* ... */);
```

---

## 4. React Hook Skeletons

```typescript
// hooks/useAetherStream.ts
import { useEffect } from "react";
import { useEngineStore } from "../stores/useEngineStore";
import { BridgeEvent, EventType } from "../types/events";

/**
 * Subscribes to the event stream, optionally filtering by event type.
 */
export function useAetherStream(filter?: EventType | EventType[]): BridgeEvent[] {
  const events = useEngineStore((s) => s.events);
  if (!filter) return events;
  
  const filterSet = new Set(Array.isArray(filter) ? filter : [filter]);
  return events.filter(e => filterSet.has(e.eventType as EventType));
}

// hooks/useTaintAudit.ts
export function useTaintAudit(spanId?: string) {
  // Returns specific span details or all spans
}

// hooks/useNodeTrace.ts
export function useNodeTrace(nodeId: string) {
  // Aggregates ModelStreamDelta and NodeExecutionFinished for a specific node
}

// hooks/useBudget.ts
export function useBudget() {
  // Exposes current budget metrics and overrun alerts
}

// hooks/useBridge.ts
export function useBridge() {
  // Exposes connection status and send() command function
}

// hooks/useCurrentPhase.ts
export function useCurrentPhase() {
  // Infers the active phase (e.g. running, planning, finished) from latest events
}

// hooks/useNodeGraph.ts
export function useNodeGraph() {
  // Exposes nodes and edges for rendering in UI
}

// hooks/useDiffs.ts
export function useDiffs() {
  // Exposes pending and historical diffs
}
```

---

## 5. CLI Component Skeletons (`apps/cli`)

```tsx
// App.tsx
import React from 'react';
import { Box } from 'ink';

export const App = () => {
  return (
    <Box flexDirection="column" width="100%">
      <TaskProgressHeader />
      <Box flexDirection="row">
        <Box width="30%"><WorkflowOutline /></Box>
        <Box width="70%"><TurnLogStream /></Box>
      </Box>
      <BudgetMeter />
      <KeyboardNavigator />
    </Box>
  );
};

// TurnLogStream.tsx
export const TurnLogStream = () => {
  // Subscribes to ModelStreamDelta and prints text deltas
};

// TaskProgressHeader.tsx
export const TaskProgressHeader = () => {
  // Displays activeRunId and current execution phase
};

// GateStatusIndicator.tsx
export const GateStatusIndicator = ({ status, error }: { status: GateStatus, error?: string }) => {
  // Renders green check, red X, or amber warning
};

// TaintAuditBadge.tsx
export const TaintAuditBadge = ({ label }: { label: Provenance }) => {
  // Renders colored tags based on trust level
};

// DiffViewer.tsx
export const DiffViewer = ({ diffId }: { diffId: string }) => {
  // Renders unified diff chunks using chalk
};

// BudgetMeter.tsx
export const BudgetMeter = () => {
  // Renders a text progress bar for budget consumption
};

// KeyboardNavigator.tsx
export const KeyboardNavigator = () => {
  // Uses ink's useInput for global hotkeys (e.g., abort, toggle trace)
};
```

---

## 6. Desktop Component Skeletons (`apps/desktop`)

```tsx
// App.tsx
import React from 'react';

export const App = () => {
  return (
    <div className="flex h-screen w-full bg-slate-900 text-slate-100">
      <div className="w-2/3 border-r border-slate-700">
        <WorkflowCanvas />
      </div>
      <div className="w-1/3 flex flex-col">
        <LiveTraceInspector />
        <MonacoDiffEditor />
      </div>
      <FanOutPanel />
      <MetricsOverlay />
    </div>
  );
};

// WorkflowCanvas.tsx
export const WorkflowCanvas = () => {
  // Wraps xyflow <ReactFlow> component. Maps useNodeGraph() to React Flow nodes/edges
};

// CustomNode.tsx
export const CustomNode = ({ data }) => {
  // xyflow node that displays nodeKind and GateStatus. Pulse animation if running.
  // Contains SocketHandle.
};

// ConditionalEdge.tsx
export const ConditionalEdge = ({ data }) => {
  // Custom SVG path styling based on `when` condition (e.g. dashed red for on_fail)
};

// RepairLoopOverlay.tsx
export const RepairLoopOverlay = ({ loop }: { loop: RepairLoop }) => {
  // Bounding box (xyflow group node) containing iteration state
};

// FanOutPanel.tsx
export const FanOutPanel = () => {
  // Floating panel for best-of-N candidate inspection
};

// LiveTraceInspector.tsx
export const LiveTraceInspector = () => {
  // Detailed log viewer for selected node, showing spans, model deltas
};

// MonacoDiffEditor.tsx
export const MonacoDiffEditor = () => {
  // Mounts @monaco-editor/react side-by-side view with Accept/Reject actions
};

// McNemarChart.tsx / BudgetMeter.tsx
export const MetricsComponents = () => {
  // Recharts wrapper for statistical reporting
};

// SocketHandle.tsx
export const SocketHandle = ({ type }: { type: 'source' | 'target' }) => {
  // Type-checked xyflow Handle component
};
```

---

## 7. Event Dispatch Pipeline

1. **Wire Delivery**: A transport message arrives via `AetherWebsocketClient` or `MockCassettePlayer.stepForward()`.
2. **Schema Validation**: The raw JSON string is parsed. The bridge driver validates it against the Zod schema for `BridgeEvent` (FI-5). Invalid structures log a warning and drop.
3. **Payload Transformation**: The backend emits payload fields in `snake_case` (e.g. `cost_actuals`). The driver performs a recursive `camelCase` transformation on the payload to meet front-end TypeScript conventions (e.g. `costActuals`).
4. **Store Dispatch**: The transformed event is fed into a central `eventRouter`. 
   - *All* events are pushed to `useEngineStore.events` for the raw log.
   - Domain-specific stores react:
     - `NodeExecutionFinished` → `useWorkflowStore` updates node status; `useBudgetStore` commits cost actuals.
     - `ModelStreamDelta` → handled directly by trace hooks/components for rendering.
5. **React Re-render**: Zustand store mutations trigger localized React re-renders in components subscribed via hooks like `useAetherStream` or `useNodeGraph`.
