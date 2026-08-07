---
status: normative
---

# AETHER Frontend: Testing, Mocks, and Developer Experience Audit Report

## 1. Executive Summary

This report outlines critical deficiencies in the AETHER frontend's testing infrastructure, mock implementations, and overall developer experience (DX). The current state presents significant risks to the maintainability, reliability, and velocity of the project. Test coverage is virtually non-existent, the mock infrastructure fails to align with the defined bridge contract, and standard developer tooling (linting, formatting, CI) is absent. Implementing the recommendations in this report will establish a robust foundation for building a production-ready application.

## 2. Severity Distribution Table

| Category | Critical | High | Medium | Low | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Testing | 2 | 3 | 2 | 0 | 7 |
| Mocks | 1 | 3 | 1 | 1 | 6 |
| Developer Experience | 0 | 1 | 4 | 1 | 6 |
| **Total** | **3** | **7** | **7** | **2** | **19** |

## 3. Test Coverage Audit

### T1. Near-Zero Test Coverage (Critical)
- **Finding:** Only 2 test files exist in the entire frontend (`events.test.ts` for Zod schemas, `player.test.ts` for synchronous mock player functions). There are zero tests for stores, hooks, WebSocket client, CLI components, Desktop components, or ui-components.
- **Fix:** Establish and enforce minimum coverage targets: 80% for `@aether/core` and 60% for apps. Integrate coverage reporting via Vitest.

### T2. Mock Player Tests Don't Cover Async Playback (Critical)
- **Finding:** `player.test.ts` only tests the synchronous `stepForward()` method. The core `play()` method, which handles asynchronous timers and event dispatch, is untested.
- **Fix:** Implement tests using `vi.useFakeTimers()` to accurately test timed event emission, speed multipliers, and the pause/resume lifecycle.

### T3. No Store Unit Tests (High)
- **Finding:** All 6 Zustand stores (`useEngineStore`, `useBudgetStore`, `useWorkflowStore`, `usePatchStore`, `useMetricsStore`, `useTaintStore`) lack test coverage.
- **Fix:** Write unit tests covering state transitions, event-driven mutations, and edge cases (e.g., empty states, budget overflows).

### T4. No Hook Unit Tests (High)
- **Finding:** The 4 custom hooks (`useAetherStream`, `useBudget`, `useNodeTrace`, `useTaintAudit`) are completely untested.
- **Fix:** Utilize `@testing-library/react-hooks` or `renderHook` from `@testing-library/react` to validate hook behavior and side effects.

### T5. No Component Tests (High)
- **Finding:** Zero tests exist for any of the 6 CLI components or 9 Desktop components.
- **Fix:** Implement component tests using `ink-testing-library` for the CLI and `@testing-library/react` for the Desktop application.

### T6. No E2E Tests (Medium)
- **Finding:** Despite Playwright being listed in the tech stack, no End-to-End (E2E) tests are defined.
- **Fix:** Introduce Playwright E2E tests covering the core user flows within the Desktop app.

### T7. No CI Pipeline for Frontend (Medium)
- **Finding:** The repository lacks a GitHub Actions workflow or a root-level `test` script, preventing automated validation of changes.
- **Fix:** Add a CI pipeline configuration that executes `pnpm test` and `pnpm lint` across all workspaces on every PR.

## 4. Mock Infrastructure Audit

### M1. MockCassettePlayer API Doesn't Match Bridge Contract (Critical)
- **Finding:** The established contract requires `loadCassette(path: string): Promise<void>`. However, the current implementation provides `loadCassetteData(cassetteData: Cassette): void`, which is synchronous and expects data rather than a path.
- **Fix:** Align the implementation with the contract. Support both path-based loading (`loadCassette`) and direct data injection for testing flexibility.

### M2. Only 2 Cassettes Exist (High)
- **Finding:** The mock environment relies on only two cassettes (`swe_bench_pass.json` and `repair_loop_ablation.json`). It lacks scenarios for failures, budget exhaustion, taint escalation, complex DAGs, fan-outs, and disconnects.
- **Fix:** Develop a comprehensive library of cassettes covering a wide array of success, failure, and edge-case scenarios.

### M3. Cassettes Don't Cover All Bridge Contract Event Types (High)
- **Finding:** Current cassettes only emit a subset of events. Missing events include `EffectAuthorized`, `EffectDenied`, `TaintSpanEmitted`, `RepairIterationStarted`, `CostSnapshot`, and `RunFinished`.
- **Fix:** Generate or manually craft cassettes that exercise every single event type defined in the bridge contract to ensure all UI states are testable.

### M4. No Mock Command Response System (High)
- **Finding:** The mock player is purely unidirectional; it replays events but cannot respond to commands sent from the client (e.g., pause, resume, authorize effect).
- **Fix:** Implement a mock command interceptor system that can provide configurable responses to client commands during playback.

### M5. No Cassette Recording Infrastructure (Medium)
- **Finding:** Once the real backend is integrated, there is no system to record actual WebSocket sessions into cassettes for future regression testing.
- **Fix:** Add a "recording mode" to `AetherWebsocketClient` that intercepts and serializes incoming events and outbound commands into JSON cassettes.

### M6. Speed Multiplier Only Affects New Timers (Low)
- **Finding:** Adjusting the playback speed mid-run does not alter the delay of the currently pending timer, leading to inconsistent playback speeds during transitions.
- **Fix:** Refactor the timer implementation in `MockCassettePlayer` to recalculate or clear and reset the current timeout when the speed multiplier changes.

## 5. Developer Experience Audit

### DX1. No ESLint or Prettier Configuration (High)
- **Finding:** The project lacks configured linting or formatting tools, leading to inconsistent code styles and potential latent bugs.
- **Fix:** Introduce a shared ESLint configuration (incorporating React and TypeScript plugins) and a Prettier configuration at the monorepo root.

### DX2. No Hot Module Replacement for CLI Development (Medium)
- **Finding:** The CLI development script relies on `tsx watch`, which completely restarts the process on file changes. This destroys the terminal state, making TUI development frustrating.
- **Fix:** Document the recommended CLI development workflow. Investigate and implement Ink's dev mode or alternative HMR solutions for the TUI.

### DX3. Turbo Cache Configuration Incomplete (Medium)
- **Finding:** `turbo.json` does not explicitly define `inputs` for its tasks, which can lead to stale caches and incorrect builds.
- **Fix:** Update `turbo.json` with precise `inputs` arrays for all relevant tasks (build, test, lint).

### DX4. No Development Documentation (Medium)
- **Finding:** The project is missing essential onboarding documentation, such as `CONTRIBUTING.md`, local setup guides, or architectural overviews.
- **Fix:** Create a comprehensive "Getting Started" guide and architecture decision map in the `docs_front/development/` directory.

### DX5. React 19 CommonJS Hack in CLI Entry Point (Low)
- **Finding:** `src_front/apps/cli/src/index.tsx` contains a manual patch for `__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE` to achieve CommonJS compatibility. This is brittle.
- **Fix:** Document this hack clearly with a link to the relevant upstream Ink/React issue. Track the issue and remove the hack once resolved upstream.

### DX6. No Type-Checking Script Across Monorepo (Medium)
- **Finding:** There is no centralized way to run TypeScript type-checking across all packages without emitting files.
- **Fix:** Add a `typecheck` script (`tsc --noEmit`) to each package and configure a corresponding Turbo task.

## 6. Proposed Test Strategy

To ensure long-term stability, AETHER should adopt a standard testing pyramid:

1.  **Unit Tests (Base):**
    *   **Focus:** Core logic, Zod schemas, Zustand store reducers, utility functions, and custom hooks.
    *   **Tools:** Vitest, `@testing-library/react` (for hooks).
    *   **Goal:** Fast, isolated verification of individual units of code.

2.  **Integration Tests (Middle):**
    *   **Focus:** Component rendering, interactions between components and stores, and the mock player lifecycle.
    *   **Tools:** Vitest, `@testing-library/react`, `ink-testing-library`.
    *   **Goal:** Ensure components correctly consume state and dispatch actions.

3.  **End-to-End Tests (Top):**
    *   **Focus:** Complete user journeys in the Desktop application (e.g., loading a run, viewing traces, approving an effect).
    *   **Tools:** Playwright.
    *   **Goal:** Validate the application from the user's perspective, running against the mock server or a staging backend.

## 7. Mock Cassette Library Design

A comprehensive cassette library is essential for reliable UI testing. The library should include:

*   **`success_basic.json`**: A straightforward, successful run with minimal nodes.
*   **`success_complex_dag.json`**: A run featuring extensive fan-out and multi-node dependencies.
*   **`failure_exception.json`**: A run terminating early due to a node execution exception.
*   **`budget_exhaustion.json`**: A run that halts because the configured budget is exceeded.
*   **`taint_escalation.json`**: A run demonstrating taint spans and policy violations.
*   **`interactive_authorization.json`**: A run requiring user intervention (e.g., `EffectAuthorized` / `EffectDenied`).
*   **`repair_loop.json`**: A run containing `RepairIterationStarted` events to test iterative UI updates.
*   **`network_instability.json`**: A simulated run testing disconnect/reconnect scenarios (may require mock server configuration rather than just a cassette).

## 8. CI Pipeline Proposal

Implement a GitHub Actions workflow (`.github/workflows/frontend.yml`) triggered on pull requests and pushes to main.

**Pipeline Stages:**
1.  **Install:** `pnpm install`
2.  **Lint:** `pnpm run lint` (ESLint & Prettier)
3.  **Typecheck:** `pnpm run typecheck` (tsc --noEmit)
4.  **Test (Unit/Integration):** `pnpm run test` (Vitest with coverage reporting)
5.  **Build:** `pnpm run build` (Ensures apps and packages compile successfully)
6.  **Test (E2E):** `pnpm run e2e` (Playwright tests)

## 9. Prioritized Remediation Roadmap

**Phase 1: Immediate Stabilization (Weeks 1-2)**
*   Fix M1: Align MockCassettePlayer API with the bridge contract.
*   Address DX1 & DX6: Implement ESLint, Prettier, and standard type-checking.
*   Resolve T1 & T3: Set up Vitest and write initial unit tests for core Zod schemas and all Zustand stores.

**Phase 2: Mock Infrastructure & Core Tests (Weeks 3-4)**
*   Address M2 & M3: Develop the comprehensive Mock Cassette Library covering all events.
*   Fix T2: Refactor and test async playback in the Mock Player.
*   Resolve T4 & T5: Implement component and hook testing using Testing Library.

**Phase 3: DX Enhancements & Automation (Weeks 5-6)**
*   Address T7: Create the CI Pipeline.
*   Implement M4: Add the mock command response system.
*   Fix DX3 & DX4: Update Turbo cache config and write Developer Documentation.
*   Address T6: Introduce initial Playwright E2E tests for the Desktop app.
