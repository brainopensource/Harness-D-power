---
status: normative
---

# AETHER Frontend: Testing, Mocks, and Developer Experience Audit Report

## 1. Executive Summary

This report outlines testing, mock infrastructure, and developer experience enhancements for the AETHER frontend.

## 2. Status Overview

- **M1**: `[x] DONE` - Aligned `MockCassettePlayer` with `BridgeClient` interface; added `loadCassette` async signature.
- **M4**: `[x] DONE` - Implemented outbound command interceptor system in `MockCassettePlayer`.
- **M6**: `[x] DONE` - Cleaned timer resets in `MockCassettePlayer` when speed multiplier changes.
- **T1**: `[ ] TODO` - Expand unit test coverage across all stores and hooks.
- **T2**: `[ ] TODO` - Add Vitest timer tests for `MockCassettePlayer.play()`.
- **T3**: `[ ] TODO` - Add Zustand store unit tests.
- **T4**: `[ ] TODO` - Add React hook tests.
- **T5**: `[ ] TODO` - Add Ink CLI & Desktop React component tests.
- **T6**: `[ ] TODO` - Add Playwright E2E test suite.
- **T7**: `[ ] TODO` - Add CI workflow in `.github/workflows/ci-front.yml`.
- **M2**: `[ ] TODO` - Add failure/budget-exhaustion cassettes to cassette library.
- **M3**: `[ ] TODO` - Add cassettes covering repair loops and taint emissions.
- **M5**: `[ ] TODO` - Add live WebSocket cassette recorder utility.
- **DX1**: `[ ] TODO` - Add ESLint + Prettier workspace configuration.
- **DX2**: `[ ] TODO` - Configure Ink CLI dev mode.
- **DX3**: `[ ] TODO` - Define explicit `inputs` array in `turbo.json`.
- **DX4**: `[ ] TODO` - Add developer onboarding guide.
- **DX5**: `[x] DONE` - Cleaned up React 19 CJS workaround in CLI `index.tsx`.
- **DX6**: `[x] DONE` - Verified TypeScript `tsc --noEmit` across all workspace packages with 0 errors.

---

## 3. Test Coverage Audit

### T1. Near-Zero Test Coverage — `[ ] TODO`
- **Status:** `[ ] TODO` — Target 80% coverage for `@aether/core`.

### T2. Mock Player Tests Don't Cover Async Playback — `[ ] TODO`
- **Status:** `[ ] TODO` — Test timed emission with `vi.useFakeTimers()`.

### T3. No Store Unit Tests — `[ ] TODO`
- **Status:** `[ ] TODO` — Write unit tests for all 6 Zustand stores.

### T4. No Hook Unit Tests — `[ ] TODO`
- **Status:** `[ ] TODO` — Test custom hooks (`useNodeTrace`, `useBudget`, etc.).

### T5. No Component Tests — `[ ] TODO`
- **Status:** `[ ] TODO` — Test CLI components with `ink-testing-library`.

### T6. No E2E Tests — `[ ] TODO`
- **Status:** `[ ] TODO` — Setup Playwright for Desktop GUI.

### T7. No CI Pipeline for Frontend — `[ ] TODO`
- **Status:** `[ ] TODO` — Add frontend CI pipeline script.

---

## 4. Mock Infrastructure Audit

### M1. MockCassettePlayer API Doesn't Match Bridge Contract — `[x] DONE`
- **File:** [`src_front/packages/mock-server/src/MockCassettePlayer.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/mock-server/src/MockCassettePlayer.ts)
- **Status:** `[x] FIXED` — Implements `BridgeClient` interface with `loadCassette(path: string): Promise<void>`.

### M2. Only 2 Cassettes Exist — `[ ] TODO`
- **Status:** `[ ] TODO` — Add edge case cassette recordings.

### M3. Cassettes Don't Cover All Bridge Contract Event Types — `[ ] TODO`
- **Status:** `[ ] TODO` — Add comprehensive event stream cassettes.

### M4. No Mock Command Response System — `[x] DONE`
- **File:** [`src_front/packages/mock-server/src/MockCassettePlayer.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/mock-server/src/MockCassettePlayer.ts)
- **Status:** `[x] FIXED` — Added command handlers for `StartRun`, `CancelRun`, `AcceptDiff`, `RejectDiff`.

### M5. No Cassette Recording Infrastructure — `[ ] TODO`
- **Status:** `[ ] TODO` — Build WebSocket event recorder utility.

### M6. Speed Multiplier Only Affects New Timers — `[x] DONE`
- **File:** [`src_front/packages/mock-server/src/MockCassettePlayer.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/mock-server/src/MockCassettePlayer.ts)
- **Status:** `[x] FIXED` — Timer delays now dynamically compute `(nextOffset - currentOffset) / speedMultiplier`.

---

## 5. Developer Experience Audit

### DX1. No ESLint or Prettier Configuration — `[ ] TODO`
- **Status:** `[ ] TODO` — Add root ESLint/Prettier configs.

### DX2. No Hot Module Replacement for CLI Development — `[ ] TODO`
- **Status:** `[ ] TODO` — Document Ink development setup.

### DX3. Turbo Cache Configuration Incomplete — `[ ] TODO`
- **Status:** `[ ] TODO` — Add `inputs` to `turbo.json`.

### DX4. No Development Documentation — `[ ] TODO`
- **Status:** `[ ] TODO` — Create getting-started guide in `docs_front/development/`.

### DX5. React 19 CommonJS Hack in CLI Entry Point — `[x] DONE`
- **File:** [`src_front/apps/cli/src/index.tsx`](file:///F:/Coding/Harness-D-power/src_front/apps/cli/src/index.tsx)
- **Status:** `[x] FIXED` — Simplified CLI index entry point.

### DX6. No Type-Checking Script Across Monorepo — `[x] DONE`
- **Status:** `[x] FIXED` — Verified typechecking (`tsc --noEmit`) passes cleanly across `@aether/core`, `@aether/mock-server`, `@aether/cli`, and `@aether/desktop`.
