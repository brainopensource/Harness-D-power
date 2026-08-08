---
status: normative
updated: 2026-08-06
---

# Event Stream Bridge Workflows (`docs_front/workflows/event_stream_bridge.md`)

This document visually details the event stream protocol, Zod wire deserialization, and dual-mode execution (Live WebSocket vs Mock Cassette Replay).

---

## 1. Dual-Mode Stream Ingestion Sequence

Every UI component in `@aether/cli` and `@aether/desktop` consumes stream events via the unified `useAetherStream` hook, remaining transparent to whether events come from live WebSocket or mock cassette replay (FI-3 invariant).

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Human Operator
    participant UI as React UI Component
    participant Hook as useAetherStream()
    participant WS as AetherWebsocketClient
    participant Mock as MockCassettePlayer
    participant Zod as Zod Event Schema Validator
    participant Store as Zustand Core Stores

    alt Mode: Live WebSocket Engine
        Operator->>WS: Connect (ws://localhost:8080/ws)
        WS-->>Zod: Inbound JSON Wire Envelope
        Zod-->>Zod: BridgeEventEnvelopeSchema.safeParse()
        Zod->>Store: Dispatch Event & Sync Dims
        Store->>Hook: State Update Trigger
        Hook->>UI: Re-render with New Event Delta
    else Mode: Mock Cassette Replay
        Operator->>Mock: play(speedMultiplier = 2.0)
        loop Timed Event Emission (offsetMs)
            Mock->>Store: Emit Inbound Event & Sync Dims
            Store->>Hook: State Update Trigger
            Hook->>UI: Re-render with New Event Delta
        end
    end
```

---

## 2. Inbound Wire Event Payload Processing Flow

```mermaid
flowchart TD
    RawJSON["Raw Wire JSON Message"] --> Parse["JSON.parse()"]
    Parse --> EnvelopeVal{"Zod Envelope Check<br/>(BridgeEventEnvelopeSchema)"}
    EnvelopeVal -- Invalid --> Drop["Log Warning & Drop Event"]
    EnvelopeVal -- Valid --> TypeSwitch{"Event Type Discriminator"}

    TypeSwitch -- "RunStarted" --> SyncEngine["Update activeRunId & status"]
    TypeSwitch -- "NodeExecutionStarted" --> SyncWorkflowStart["Mark node RUNNING on Canvas"]
    TypeSwitch -- "NodeExecutionFinished" --> SyncWorkflowEnd["Update GateStatus (PASSED / FAILED / NONE)"]
    TypeSwitch -- "ModelStreamDelta" --> SyncStream["Append streaming text delta"]
    TypeSwitch -- "BudgetLeaseUpdated" --> SyncBudget["Update Reserved/Committed/Remaining Dims"]

    SyncEngine & SyncWorkflowStart & SyncWorkflowEnd & SyncStream & SyncBudget --> DispatchStore["Dispatch to Subscribers"]
```
