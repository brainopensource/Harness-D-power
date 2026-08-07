---
status: normative
---

# AETHER Frontend Architecture & Performance Audit Report

## 1. Executive Summary
This report outlines critical architecture and performance defects identified within the AETHER frontend ecosystem. The audit covers the React 19 application, Tauri desktop client, Ink-based CLI, and core `@aether/core` packages. The findings highlight significant coupling between networking and state management, memory leaks due to unbounded event arrays, and severe performance bottlenecks caused by unmemoized derived state and forced re-renders. Immediate remediation of the critical issues is required to ensure stability, maintainability, and scalability.

## 2. Severity Distribution Table

| Category     | Critical | High | Medium | Low | Total |
|--------------|----------|------|--------|-----|-------|
| Architecture | 3        | 4    | 3      | 0   | 10    |
| Performance  | 1        | 2    | 4      | 1   | 8     |
| **Total**    | **4**    | **6**  | **7**  | **1** | **18**  |

## 3. Architecture Defects

### A1. WebSocket Client Tightly Coupled to Zustand Stores
- **Severity:** Critical
- **File:** [`src_front/packages/core/src/client/AetherWebsocketClient.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/client/AetherWebsocketClient.ts)
- **Description:** The networking client imports and mutates Zustand stores directly (`useEngineStore.getState()...`). This violates headless decoupling, preventing the instantiation of multiple disconnected clients, testing in isolation, or using the client outside of React.
- **Fix Recommendation:** Inject an event handler/callback interface. The client should emit typed events, and a separate bridge layer should wire them to stores.

### A2. No Formal BridgeClient Interface
- **Severity:** Critical
- **Description:** The documentation promises `MockCassettePlayer` implements the identical stream interface as `AetherWebsocketClient`, but there is NO formal TypeScript `interface` enforcing this parity.
- **Fix Recommendation:** Define a formal interface in `@aether/core`.
  ```typescript
  export interface BridgeClient { 
    connect(): void; 
    disconnect(): void; 
    sendCommand(cmd: OutboundCommand): void; 
    onEvent(handler: (event: BridgeEvent) => void): () => void;
  }
  ```

### A3. Event Array Unbounded Growth / Memory Leak
- **Severity:** Critical
- **File:** [`src_front/packages/core/src/stores/useEngineStore.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/stores/useEngineStore.ts)
- **Description:** `events: [...state.events, event]` grows unbounded. In a streaming app processing hundreds of events per task, this causes progressive memory bloat and slowdown of all array operations.
- **Fix Recommendation:** Implement a ring buffer with a configurable max size (e.g., 500) or use an `EventEmitter` pattern where stores subscribe to typed events instead of accumulating a master array.

### A4. Missing React Error Boundaries
- **Severity:** High
- **Files:** CLI `App.tsx`, Desktop `App.tsx`
- **Description:** Missing error boundaries. An error in any child component crashes the entire application.
- **Fix Recommendation:** Wrap tab panels and the CLI root in `<ErrorBoundary>` components with graceful fallback UIs.

### A5. No Global Error/Exception Handler for CLI Process
- **Severity:** Medium
- **File:** [`src_front/apps/cli/src/index.tsx`](file:///F:/Coding/Harness-D-power/src_front/apps/cli/src/index.tsx)
- **Description:** Missing global `process.on('uncaughtException')` or `process.on('unhandledRejection')` handler.
- **Fix Recommendation:** Add global handlers to gracefully log and exit.

### A6. WebSocket Reconnection Leak
- **Severity:** High
- **File:** [`src_front/packages/core/src/client/AetherWebsocketClient.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/client/AetherWebsocketClient.ts)
- **Description:** `disconnect()` does not clear the pending reconnection timeout, causing a "zombie" client to reconnect after disposal.
- **Fix Recommendation:** Store the timeout ID and clear it in `disconnect()`.

### A7. No Message Queuing for Outbound Commands
- **Severity:** Medium
- **Description:** `sendCommand()` drops messages if the socket is not `OPEN`.
- **Fix Recommendation:** Queue commands while in the `CONNECTING` state and flush upon successful connection.

### A8. Inline Styles Creating New Object References Every Render
- **Severity:** High
- **Files:** Desktop `App.tsx`, `HeaderControls.tsx`, `MetricsDashboard.tsx`, `LiveTraceInspector.tsx`
- **Description:** Pervasive `style={{ display: 'flex', ... }}` creates new objects every render, defeating React's reconciliation and causing unnecessary child re-renders.
- **Fix Recommendation:** Extract to CSS modules, a Tailwind layer, or at minimum use `useMemo`/constants.

### A9. CSP Disabled in Tauri
- **Severity:** High (Security)
- **File:** [`src_front/apps/desktop/src-tauri/tauri.conf.json`](file:///F:/Coding/Harness-D-power/src_front/apps/desktop/src-tauri/tauri.conf.json)
- **Description:** `"csp": null` opens the desktop app to XSS vulnerabilities via compromised Monaco editor content or malicious mock data.
- **Fix Recommendation:** Set a strict CSP allowing only local resources and the required WebSocket endpoint.

### A10. Store Coupling — Monolithic Exports from @aether/core
- **Severity:** Medium
- **Description:** All stores are re-exported as a flat namespace from `index.ts`, making tree-shaking harder and increasing the chance of importing unused stores.
- **Fix Recommendation:** Export stores from individual files or group exports logically to support better tree-shaking.

## 4. Performance Defects

### P1. Unmemoized Array Derivations in Hooks
- **Severity:** Critical
- **File:** [`src_front/packages/core/src/hooks/useNodeTrace.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/hooks/useNodeTrace.ts)
- **Description:** `useEngineStore(state => state.events.filter(...))` creates a new array on EVERY store update (even unrelated ones), triggering infinite re-render cascades.
- **Fix Recommendation:** Use Zustand's `useShallow` or implement a proper equality function in the selector.

### P2. setTick Anti-Pattern for Force Re-renders
- **Severity:** High
- **Files:** CLI `App.tsx`, Desktop `App.tsx`
- **Description:** `setTick(t => t + 1)` on every player event forces full tree re-renders instead of letting Zustand's selective subscriptions manage updates efficiently.
- **Fix Recommendation:** Remove the tick counter. Components should subscribe to relevant store slices directly.

### P3. Multiple Store Subscriptions Per Hook
- **Severity:** Medium
- **Files:** `useBudget.ts`, `useTaintAudit.ts`
- **Description:** Each hook calls the store hook multiple separate times instead of using a single selector with `useShallow`.
- **Fix Recommendation:** Combine subscriptions using a single selector returning an object with `useShallow`.

### P4. No List Virtualization for Event Streams
- **Severity:** High
- **File:** Desktop `LiveTraceInspector.tsx`
- **Description:** Event list renders ALL events in the DOM. For nodes with thousands of delta events, this causes lag.
- **Fix Recommendation:** Use `react-window` or `@tanstack/virtual` for virtualized rendering.

### P5. WorkflowStore Deep Nested Updates
- **Severity:** Medium
- **File:** [`src_front/packages/core/src/stores/useWorkflowStore.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/stores/useWorkflowStore.ts)
- **Description:** Nested `Map` state updates on large topologies could become sluggish with immutable spreads.
- **Fix Recommendation:** Consider incorporating `immer` middleware for Zustand to simplify and optimize deep updates.

### P6. No Debouncing on Rapid Event Processing
- **Severity:** Medium
- **Description:** The mock player and WS client process events synchronously with no batching. Rapid bursts of events cause render storms.
- **Fix Recommendation:** Use `queueMicrotask` or `requestAnimationFrame` batching to throttle state updates.

### P7. Monaco Editor Not Lazy Loaded
- **Severity:** Medium
- **File:** Desktop `MonacoDiffEditor.tsx`
- **Description:** Monaco is imported eagerly, adding ~2MB to the initial bundle even when the diff tab is not active.
- **Fix Recommendation:** Use `React.lazy()` + `Suspense` for the Monaco tab to defer loading.

### P8. Grid Layout Not Responsive
- **Severity:** Low
- **File:** Desktop `MetricsDashboard.tsx`
- **Description:** `gridTemplateColumns: 'repeat(3, 1fr)'` squashes on small windows.
- **Fix Recommendation:** Use media queries or flex wrap to achieve responsive design.

## 5. Prioritized Remediation Roadmap

1. **Phase 1: Critical Fixes (Immediate)**
   - **A1, A2, A3:** Decouple the WebSocket client, define the `BridgeClient` interface, and fix the event array unbounded growth to prevent crashes and memory leaks.
   - **P1:** Fix unmemoized derivations in hooks to resolve immediate render cascades.
2. **Phase 2: High Priority Structural & Security (Next Sprint)**
   - **A4, A5, A9:** Introduce Error Boundaries, global CLI exception handling, and a strict CSP in Tauri.
   - **A6, A8, P2, P4:** Fix WebSocket reconnections, eliminate inline styles and `setTick` anti-patterns, and virtualize event streams.
3. **Phase 3: Medium & Low Enhancements (Backlog)**
   - **A7, A10, P3, P5, P6, P7, P8:** Implement message queuing, refine Zustand subscriptions (batching, `useShallow`, `immer`), and lazy-load heavy components like Monaco.

## 6. Impact on Backend Integration
The current tight coupling (A1) and lack of queuing (A7) significantly hamper robust backend communication. By formalizing the `BridgeClient` interface (A2) and decoupling it from Zustand, the frontend can better handle backend WebSocket disconnects, rapidly replay states, and efficiently stream large volumes of structural events. Implementing batching (P6) and bounding event memory (A3) will ensure the UI remains responsive even when the Python backend transmits hundreds of events rapidly.
