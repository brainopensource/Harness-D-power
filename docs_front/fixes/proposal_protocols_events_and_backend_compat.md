---
status: normative
---

# AETHER Frontend: Protocols, Events, and Backend Compatibility Audit Report

## 1. Executive Summary

This report documents protocol/event correctness and backend compatibility fixes for the AETHER frontend.

## 2. Status Overview

- **EV1**: `[x] DONE` - Added Zod schema validation in `MockCassettePlayer.ts` (`parseBridgeEvent`).
- **EV2**: `[x] DONE` - Added Zod schema validation in `AetherWebsocketClient.ts` (`parseBridgeEvent`).
- **EV3**: `[x] DONE` - Added payload Zod schemas and typed interfaces for all wire events.
- **EV4**: `[x] DONE` - Updated `BridgeEventType` enum and schemas with all contract event types (`RepairIterationStarted`, `CostSnapshot`, `CompactionCompleted`, etc.).
- **EV5**: `[x] DONE` - Added `BridgeCommand` type and `BridgeCommandSchema` for outbound commands (`StartRun`, `CancelRun`, `AcceptDiff`, `RejectDiff`, `ApproveMutation`).
- **EV6**: `[x] DONE` - Implemented outbound command interceptors and default mock handlers in `MockCassettePlayer.ts`.
- **EV7**: `[x] DONE` - Created `toCamelCaseKeys` utility in `types/events.ts` to automatically convert backend `snake_case` JSON payloads to frontend `camelCase`.
- **BC1**: `[ ] TODO` - Create backend `EffectRequest` mapping layer for high-level frontend commands (scheduled for Sprint FE-02).
- **BC2**: `[ ] TODO` - Add `cachedPromptTokens` to budget display.
- **BC3**: `[ ] TODO` - Add `concurrencySlots` dimension to budget meter.
- **BC4**: `[ ] TODO` - Update `GateStatusIndicator` labels from "Instrument Error" to "Unmeasured" for `NONE` status.
- **BC5**: `[x] DONE` - Added `AGENT` value to `Provenance` enum in `types/provenance.ts`.
- **BC6**: `[ ] TODO` - Align `WorkflowNode` schema fields with backend `WorkflowStep`.
- **BC7**: `[x] DONE` - Added safe Zod envelope validation (`BridgeEventEnvelopeSchema`).
- **BC8**: `[ ] TODO` - Reconcile task IDs in `tracking_list.md` with sprint backlog artifacts.

---

## 3. Protocol & Event Defects

### EV1. Zero Runtime Validation in MockCassettePlayer — `[x] DONE`
- **File:** [`src_front/packages/mock-server/src/MockCassettePlayer.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/mock-server/src/MockCassettePlayer.ts)
- **Status:** `[x] FIXED` — Enforced Invariant FI-5 by running all cassette events through `parseBridgeEvent()` before dispatching.

### EV2. WebSocket Client Also Skips Validation — `[x] DONE`
- **File:** [`src_front/packages/core/src/client/AetherWebsocketClient.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/client/AetherWebsocketClient.ts)
- **Status:** `[x] FIXED` — Incoming WebSocket frames pass through `parseBridgeEvent()` boundary validation.

### EV3. No Discriminated Union for Event Types — `[x] DONE`
- **File:** [`src_front/packages/core/src/types/events.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/types/events.ts)
- **Status:** `[x] FIXED` — Added specific typed payload schemas and envelope parsers.

### EV4. Missing Event Types vs Bridge Contract — `[x] DONE`
- **File:** [`src_front/packages/core/src/types/events.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/types/events.ts)
- **Status:** `[x] FIXED` — Expanded `BridgeEventType` enum and Zod schemas to include all contract event types.

### EV5. Missing Outbound Command Schemas — `[x] DONE`
- **File:** [`src_front/packages/core/src/types/events.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/types/events.ts)
- **Status:** `[x] FIXED` — Defined `BridgeCommand` and `BridgeCommandSchema`.

### EV6. Mock Player Doesn't Handle Outbound Commands — `[x] DONE`
- **File:** [`src_front/packages/mock-server/src/MockCassettePlayer.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/mock-server/src/MockCassettePlayer.ts)
- **Status:** `[x] FIXED` — Implemented `sendCommand()` handling and `registerCommandHandler()` mock dispatch.

### EV7. snake_case to camelCase Conversion Not Implemented — `[x] DONE`
- **File:** [`src_front/packages/core/src/types/events.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/types/events.ts)
- **Status:** `[x] FIXED` — Created `toCamelCaseKeys` recursive transformer.

---

## 4. Backend Compatibility Defects

### BC1. Command vs Effect Class Mismatch — `[ ] TODO`
- **Status:** `[ ] TODO` — Map frontend commands to backend capability effect classes.

### BC2. Missing cached_prompt_tokens Field — `[ ] TODO`
- **Status:** `[ ] TODO` — Expose cached prompt tokens in `useBudget`.

### BC3. Missing concurrency_slots Budget Dimension — `[ ] TODO`
- **Status:** `[ ] TODO` — Add concurrency slots to `BudgetMeter`.

### BC4. GateStatus Enum Values Don't Match Backend — `[ ] TODO`
- **Status:** `[ ] TODO` — Update label in `GateStatusIndicator`.

### BC5. Provenance Enum Missing AGENT Value — `[x] DONE`
- **File:** [`src_front/packages/core/src/types/provenance.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/types/provenance.ts)
- **Status:** `[x] FIXED` — Added `AGENT = "agent"` to `Provenance` enum.

### BC6. WorkflowNode Schema Missing Fields — `[ ] TODO`
- **Status:** `[ ] TODO` — Add socket_in / socket_out to `WorkflowNode`.

### BC7. No Wire Envelope Validation — `[x] DONE`
- **File:** [`src_front/packages/core/src/types/events.ts`](file:///F:/Coding/Harness-D-power/src_front/packages/core/src/types/events.ts)
- **Status:** `[x] FIXED` — Added strict Zod envelope schema validation.

### BC8. Agile Tracking Disjoint from Sprint Plans — `[ ] TODO`
- **Status:** `[ ] TODO` — Reconcile `tracking_list.md` task IDs.
