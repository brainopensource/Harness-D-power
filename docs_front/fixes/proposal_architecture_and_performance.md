---
status: normative
---

# AETHER Frontend Architecture & Performance Audit Report

## 1. Executive Summary
This report outlines critical architecture and performance defects identified within the AETHER frontend ecosystem. The audit covers the React 19 application, Tauri desktop client, Ink-based CLI, and core `@aether/core` packages.

## 2. Status Overview

- **A1**: `[x] DONE` - Decoupled WebSocket client from Zustand stores via typed event listener architecture.
- **A2**: `[x] DONE` - Created formal `BridgeClient` interface in `@aether/core/client/BridgeClient.ts`.
- **A3**: `[x] DONE` - Implemented Ring Buffer cap (`maxEvents: 500`) in `useEngineStore` to eliminate memory leaks.
- **A4**: `[x] DONE` - Created `<ErrorBoundary>` component in `@aether/ui-components` and wrapped Desktop main shell & tabs.
- **A5**: `[ ] TODO` - Global CLI process `uncaughtException` handler (scheduled for Sprint FE-02).
- **A6**: `[x] DONE` - Cleared `reconnectTimerId` on `disconnect()` in `AetherWebsocketClient.ts`.
- **A7**: `[ ] TODO` - Message queuing while in CONNECTING state.
- **A8**: `[ ] TODO` - Refactor inline style objects to CSS modules / Tailwind classes.
- **A9**: `[ ] TODO` - Tighten Tauri CSP configuration in `tauri.conf.json`.
- **A10**: `[ ] TODO` - Fine-grained sub-path exports for tree-shaking optimization.
- **P1**: `[x] DONE` - Refactored `useNodeTrace.ts` with `useMemo` to eliminate unmemoized array derivation re-render storms.
- **P2**: `[x] DONE` - Removed `setTick` forced re-render anti-pattern from CLI `App.tsx` and Desktop `App.tsx`.
- **P3**: `[ ] TODO` - Refactor multi-selector hooks (`useBudget`, `useTaintAudit`) to single shallow selector.
- **P4**: `[ ] TODO` - Add list virtualization (`react-window`) to `LiveTraceInspector.tsx`.
- **P5**: `[ ] TODO` - Add `immer` middleware to `useWorkflowStore.ts`.
- **P6**: `[ ] TODO` - Add event batching via `requestAnimationFrame`.
- **P7**: `[ ] TODO` - Lazy-load Monaco Diff Editor via `React.lazy()`.
- **P8**: `[ ] TODO` - Make Metrics Dashboard grid responsive.

---

## 3. Architecture Defects

### A1. WebSocket Client Tightly Coupled to Zustand Stores — `[x] DONE`
- **Severity:** Critical
- **File:** [`src_front/packages/core/src/client/AetherWebsocketClient.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/client/AetherWebsocketClient.ts)
- **Status:** `[x] FIXED` — Decoupled store synchronization into safe Zod schema parsers; client exposes typed listener subscriptions.

### A2. No Formal BridgeClient Interface — `[x] DONE`
- **Severity:** Critical
- **File:** [`src_front/packages/core/src/client/BridgeClient.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/client/BridgeClient.ts)
- **Status:** `[x] FIXED` — Created `BridgeClient` interface implemented by both `AetherWebsocketClient` and `MockCassettePlayer`.

### A3. Event Array Unbounded Growth / Memory Leak — `[x] DONE`
- **Severity:** Critical
- **File:** [`src_front/packages/core/src/stores/useEngineStore.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/stores/useEngineStore.ts)
- **Status:** `[x] FIXED` — Implemented ring-buffer cap (`maxEvents = 500`) to prevent unbounded array memory growth.

### A4. Missing React Error Boundaries — `[x] DONE`
- **Severity:** High
- **Files:** [`src_front/packages/ui-components/src/ErrorBoundary.tsx`](file:///F:/Coding/Harness-D-power/src_front/packages/ui-components/src/ErrorBoundary.tsx), Desktop `App.tsx`
- **Status:** `[x] FIXED` — Created `<ErrorBoundary>` component and wrapped Desktop App shell and view tabs.

### A5. No Global Error/Exception Handler for CLI Process — `[ ] TODO`
- **Severity:** Medium
- **File:** [`src_front/apps/cli/src/index.tsx`](file:///F:/Coding/Harness-D-power/src_front/apps/cli/src/index.tsx)
- **Status:** `[ ] TODO` — Needs `process.on('uncaughtException')` handler.

### A6. WebSocket Reconnection Leak — `[x] DONE`
- **Severity:** High
- **File:** [`src_front/packages/core/src/client/AetherWebsocketClient.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/client/AetherWebsocketClient.ts)
- **Status:** `[x] FIXED` — Added `clearReconnectTimer()` on disconnect.

### A7. No Message Queuing for Outbound Commands — `[ ] TODO`
- **Severity:** Medium
- **Status:** `[ ] TODO` — Queue outbound commands when socket is connecting.

### A8. Inline Styles Creating New Object References Every Render — `[ ] TODO`
- **Severity:** High
- **Status:** `[ ] TODO` — Extract to Tailwind CSS or static constants.

### A9. CSP Disabled in Tauri — `[ ] TODO`
- **Severity:** High (Security)
- **Status:** `[ ] TODO` — Set strict CSP in `tauri.conf.json`.

### A10. Store Coupling — Monolithic Exports from @aether/core — `[ ] TODO`
- **Severity:** Medium
- **Status:** `[ ] TODO` — Optimize package export paths.

---

## 4. Performance Defects

### P1. Unmemoized Array Derivations in Hooks — `[x] DONE`
- **Severity:** Critical
- **File:** [`src_front/packages/core/src/hooks/useNodeTrace.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/hooks/useNodeTrace.ts)
- **Status:** `[x] FIXED` — Refactored hook with `useMemo` to stabilize reference returns and prevent render storms.

### P2. setTick Anti-Pattern for Force Re-renders — `[x] DONE`
- **Severity:** High
- **Files:** CLI `App.tsx`, Desktop `App.tsx`
- **Status:** `[x] FIXED` — Removed `setTick` anti-pattern; state is reactively driven by Zustand stores.

### P3. Multiple Store Subscriptions Per Hook — `[ ] TODO`
- **Severity:** Medium
- **Status:** `[ ] TODO` — Use `useShallow` for multi-selector hooks.

### P4. No List Virtualization for Event Streams — `[ ] TODO`
- **Severity:** High
- **Status:** `[ ] TODO` — Add `react-window` to `LiveTraceInspector.tsx`.

### P5. WorkflowStore Deep Nested Updates — `[ ] TODO`
- **Severity:** Medium
- **Status:** `[ ] TODO` — Add `immer` middleware.

### P6. No Debouncing on Rapid Event Processing — `[ ] TODO`
- **Severity:** Medium
- **Status:** `[ ] TODO` — Throttle rapid events with `requestAnimationFrame`.

### P7. Monaco Editor Not Lazy Loaded — `[ ] TODO`
- **Severity:** Medium
- **Status:** `[ ] TODO` — Wrap Monaco in `React.lazy()`.

### P8. Grid Layout Not Responsive — `[ ] TODO`
- **Severity:** Low
- **Status:** `[ ] TODO` — Add responsive breakpoints to `MetricsDashboard.tsx`.
