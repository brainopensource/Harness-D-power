---
status: normative
---

# AETHER Frontend: Protocols, Events, and Backend Compatibility Audit Report

## 1. Executive Summary

This report documents the findings of an audit focused on protocol/event correctness and backend compatibility within the AETHER frontend. The audit revealed significant gaps in strict event schema validation, disjoints between frontend implementations and the defined bridge contracts, and missing domain model alignments with the Python backend. Addressing these defects is critical to ensure a stable, type-safe integration between the AETHER frontend and backend engine.

## 2. Severity Distribution Table

| Severity | Count | Issue Identifiers |
| :--- | :--- | :--- |
| **Critical** | 3 | EV1, EV2, BC1 |
| **High** | 6 | EV3, EV4, EV5, EV6, EV7, BC2, BC3 |
| **Medium** | 4 | BC4, BC5, BC6, BC7 |
| **Documentation Bug** | 1 | BC8 |

## 3. Protocol & Event Defects

### EV1. Zero Runtime Validation in MockCassettePlayer (Critical)
*   **File:** `src_front/packages/mock-server/src/MockCassettePlayer.ts`
*   **Analysis:** Violates Invariant FI5 (Strict Event Schema Validation). The player blindly trusts cassette data without any `zod` validation, relying on unsafe `as any` type assertions for payloads.
*   **Fix Recommendation:** Validate every event against the Zod schemas from `@aether/core/types/events` before dispatching. Log and drop invalid events.

### EV2. WebSocket Client Also Skips Validation (Critical)
*   **File:** `src_front/packages/core/src/client/AetherWebsocketClient.ts`
*   **Analysis:** Similar to EV1, the WebSocket client lacks Zod parsing for incoming messages, utilizing `as any` casts on payloads.
*   **Fix Recommendation:** Parse with `BridgeEventSchema.safeParse()`. On failure, emit a validation error event.

### EV3. No Discriminated Union for Event Types (High)
*   **File:** `src_front/packages/core/src/types/events.ts`
*   **Analysis:** The `BridgeEvent<T, P>` generic defaults the payload to `Record<string, unknown>`, forcing manual type assertions down the line.
*   **Fix Recommendation:** Create a discriminated union: `type AetherEvent = RunStartedEvent | NodeExecutionStartedEvent | ModelStreamDeltaEvent | ...` with `eventType` as the discriminant.

### EV4. Missing Event Types vs Bridge Contract (High)
*   **Analysis:** The codebase `BridgeEventType` enum defines a subset of events. The `BRIDGE_CONTRACT.md` specifies additional events: `RepairIterationStarted`, `CostSnapshot`, `RunFinished`, `CompactionCompleted`, which are missing in the code.
*   **Fix Recommendation:** Add all contract-specified event types to the enum and create their corresponding payload Zod schemas.

### EV5. Missing Outbound Command Schemas (High)
*   **Analysis:** The bridge contract defines outbound commands: `StartRun`, `CancelRun`, `AcceptDiff`, `RejectDiff`, `ApproveMutation`. However, there are no Zod schemas, TypeScript types, or send methods implemented for these.
*   **Fix Recommendation:** Define an `OutboundCommand` union type with Zod schemas for each respective command.

### EV6. Mock Player Doesn't Handle Outbound Commands (High)
*   **Analysis:** `MockCassettePlayer` only replays events (Engine → Client) and lacks mock handlers for outbound commands (Client → Engine).
*   **Fix Recommendation:** Add command interceptors to the mock player that produce appropriate mock responses (e.g., intercepting `AcceptDiff` and emitting the next `NodeExecutionStarted`).

### EV7. snake_case to camelCase Conversion Not Implemented (High)
*   **Analysis:** The `BRIDGE_CONTRACT.md` specifies automatic field name conversion from backend `snake_case` to frontend `camelCase`. This is missing in both the WebSocket client and mock player.
*   **Fix Recommendation:** Add a `transformKeys` utility function in the bridge driver layer to handle bidirectional or unidirectional key transformation.

## 4. Backend Compatibility Defects

### BC1. Command vs Effect Class Mismatch (Critical)
*   **Analysis:** The frontend assumes high-level commands (e.g., `AcceptDiff`) are sent to the backend. Conversely, the backend's `EffectRequest` (in `PolicyEngine.authorize()`) expects low-level effect classes: `read`, `write`, `shell`, `network`, `model`, `evaluate`. There is no native `AcceptDiff` effect class.
*   **Fix Recommendation:** Define a command protocol that maps frontend commands to backend effect requests. The backend (`engine.py`) should expose high-level command handlers that internally generate the appropriate `EffectRequests`.

### BC2. Missing `cached_prompt_tokens` Field (High)
*   **Analysis:** The backend `UsageEvent` tracks `prompt_tokens`, `completion_tokens`, and `cached_prompt_tokens`. The frontend `BudgetDims` type only tracks `tokensMicros`.
*   **Fix Recommendation:** Add `cachedPromptTokens` to the frontend budget types and update the `BudgetMeter` component to display this metric.

### BC3. Missing `concurrency_slots` Budget Dimension (High)
*   **Analysis:** The backend `BudgetDims` includes `concurrency_slots`. This is entirely omitted in the frontend budget types and `BudgetMeter`.
*   **Fix Recommendation:** Add `concurrencySlots` to the frontend budget model and corresponding UI components.

### BC4. GateStatus Enum Values Don't Match Backend (Medium)
*   **Analysis:** While both ends use `PASSED | FAILED | NONE`, the frontend `GateStatusIndicator` maps `NONE` to "Instrument Error". The backend interprets `NONE` as "unmeasured", a broader category.
*   **Fix Recommendation:** Update the frontend mapping to use "Unmeasured" as the label for `NONE`, supplementing it with a tooltip explaining potential causes.

### BC5. Provenance Enum Missing AGENT Value (Medium)
*   **Analysis:** The frontend `Provenance` enum lacks the `AGENT` value, which exists in the backend enum alongside `TRUSTED_SYSTEM`, `OPERATOR`, `UNTRUSTED_EXTERNAL`, and `UNTRUSTED_DERIVED`.
*   **Fix Recommendation:** Add the `AGENT` value to the frontend `Provenance` enum.

### BC6. WorkflowNode Schema Missing Fields (Medium)
*   **Analysis:** The frontend `WorkflowNode` is missing several fields present in the backend `WorkflowStep`, specifically `socket_in`, `socket_out` (used for topology validation), and edge conditions (`when`).
*   **Fix Recommendation:** Align the frontend `WorkflowNode` schema with the full shape of the backend `WorkflowStep`.

### BC7. No Wire Envelope Validation (Medium)
*   **Analysis:** The bridge contract dictates a wire envelope with `seq`, `runId`, `eventType`, `at`, and `payload`. The current Zod schema uses loose `z.string()` types for `runId` and `at`.
*   **Fix Recommendation:** Strengthen validation by using `z.string().uuid()` for `runId` and `z.string().datetime()` for the `at` field.

### BC8. Agile Tracking Completely Disjoint from Sprint Plans (Documentation Bug)
*   **Analysis:** `tracking_list.md` tracks `TASK-FE-000` through `TASK-FE-033` (reporting 100% completion), while sprint plans use `TASK-FE-101` through `TASK-FE-408`. The tracking list is disjoint from sprint deliverables.
*   **Fix Recommendation:** Reconcile tracking IDs with sprint plan IDs, or deprecate/mark `tracking_list.md` as stale.

## 5. Missing Event/Command Coverage Matrix

| Bridge Contract Item | Type | Implemented in Code? | Fix Needed |
| :--- | :--- | :--- | :--- |
| `RunStarted` | Event | Yes | - |
| `NodeExecutionStarted` | Event | Yes | - |
| `NodeExecutionFinished` | Event | Yes | - |
| `ModelStreamDelta` | Event | Yes | - |
| `EffectAuthorized` | Event | Yes | - |
| `EffectDenied` | Event | Yes | - |
| `BudgetLeaseUpdated` | Event | Yes | - |
| `GateReportEmitted` | Event | Yes | - |
| `TaintSpanEmitted` | Event | Yes | - |
| `RepairIterationStarted`| Event | **No** | Add to enum and schema |
| `CostSnapshot` | Event | **No** | Add to enum and schema |
| `RunFinished` | Event | **No** | Add to enum and schema |
| `CompactionCompleted` | Event | **No** | Add to enum and schema |
| `StartRun` | Command | **No** | Define Zod schema & union |
| `CancelRun` | Command | **No** | Define Zod schema & union |
| `AcceptDiff` | Command | **No** | Define Zod schema & union |
| `RejectDiff` | Command | **No** | Define Zod schema & union |
| `ApproveMutation` | Command | **No** | Define Zod schema & union |

## 6. Schema Alignment Checklist

| Domain Type | Backend (Python) | Frontend (Zod/TS) | Alignment Status | Action Item |
| :--- | :--- | :--- | :--- | :--- |
| **Command Mapping** | `EffectRequest` (read, write...) | High-level (AcceptDiff) | ❌ **Mismatch** | Create command-to-effect translation layer (BC1) |
| **BudgetDims** | includes `concurrency_slots` | missing `concurrencySlots` | ❌ **Mismatch** | Add `concurrencySlots` to frontend (BC3) |
| **UsageEvent** | includes `cached_prompt_tokens` | missing `cachedPromptTokens` | ❌ **Mismatch** | Add `cachedPromptTokens` to frontend (BC2) |
| **GateStatus** | `NONE` means "unmeasured" | `NONE` mapped to "Error" | ❌ **Mismatch** | Update UI label to "Unmeasured" (BC4) |
| **Provenance** | includes `AGENT` | missing `AGENT` | ❌ **Mismatch** | Add `AGENT` to enum (BC5) |
| **WorkflowStep** | `socket_in`, `socket_out`, `when` | missing fields | ❌ **Mismatch** | Update `WorkflowNode` schema (BC6) |
| **Wire Envelope**| UUID `runId`, ISO8601 `at` | generic `string()` | ❌ **Loose Validation** | Update to `z.string().uuid()` and `z.string().datetime()` (BC7) |

## 7. Prioritized Remediation Roadmap

1.  **Phase 1: Validation & Type Safety (Critical)**
    *   Implement strict Zod parsing in `AetherWebsocketClient` (EV2) and `MockCassettePlayer` (EV1).
    *   Define the `AetherEvent` discriminated union (EV3).
2.  **Phase 2: Contract Alignment (High)**
    *   Add missing events to `BridgeEventType` (EV4).
    *   Implement `OutboundCommand` schemas and handlers in mock (EV5, EV6).
    *   Implement `snake_case` to `camelCase` transformation utility (EV7).
3.  **Phase 3: Domain Model Reconciliation (High/Medium)**
    *   Resolve Command vs Effect Class mismatch via translation protocol (BC1).
    *   Update `BudgetDims`, `UsageEvent`, `GateStatus`, `Provenance`, and `WorkflowNode` schemas (BC2, BC3, BC4, BC5, BC6).
    *   Strengthen wire envelope validation (BC7).
4.  **Phase 4: Documentation (Low)**
    *   Reconcile agile tracking IDs with sprint plans (BC8).

## 8. Risk Assessment for Backend Integration

*   **Data Corruption/Panic Risk (High):** Due to EV1 and EV2, the frontend is currently highly susceptible to crashing or presenting invalid states if the backend contract changes or sends unexpected payloads.
*   **Functional Blockers (Critical):** The mismatch identified in BC1 means the frontend currently has no functional way to authorize operations like diff acceptance, breaking the core interaction loop.
*   **Telemetry/Observability Gaps (Medium):** Missing budget metrics (BC2, BC3) and incorrect status interpretations (BC4) will lead to skewed operator understanding of system health and costs.
