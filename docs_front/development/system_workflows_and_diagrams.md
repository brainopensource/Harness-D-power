---
status: rationale
updated: 2026-08-06
---

# SYSTEM_WORKFLOWS_AND_DIAGRAMS — Front-End Component Spec

This document details the visual flows, data pipelines, state management dispatching, and interaction models of the AETHER front-end applications (`apps/cli` and `apps/desktop`). 

---

## Diagram 1 — Event Stream Flow (Engine → Store → Component)

This sequence diagram illustrates the unidirectional data flow (FI-1) from the headless backend out to the React and Ink view layers. Notice that events are validated and normalized before hitting the state stores.

```mermaid
sequenceDiagram
    autonumber
    participant EN as Backend (engine.py/bus.py)
    participant TR as Transport (WS / SSE)
    participant DR as Bridge Driver (Websocket/Mock)
    participant ST as Zustand Store Dispatcher
    participant STO as Domain Stores (core)
    participant UI as React/Ink Component

    EN->>TR: Emit JSON Event (snake_case)
    TR->>DR: Receive raw payload
    Note over DR: Validate payload via Zod<br/>Convert snake_case to camelCase
    DR->>ST: Route valid event
    ST->>STO: Update specific store (e.g. useWorkflowStore)
    STO-->>UI: Trigger hook re-render (useWorkflowStore)
    Note over UI: UI updates seamlessly (CLI or Desktop)
```

---

## Diagram 2 — Bridge Driver State Machine

The client drivers manage the connectivity lifecycle securely and transparently. In Mock mode, network states are bypassed to maintain component determinism (FI-3).

```mermaid
stateDiagram-v2
    direction LR
    
    [*] --> disconnected
    
    state LiveMode {
        disconnected --> connecting : init()
        connecting --> connected : WS Open
        connecting --> reconnecting : WS Error (Backoff)
        connected --> reconnecting : WS Close
        reconnecting --> connected : WS Open
        reconnecting --> disconnected : Max Retries Met
    }
    
    state MockMode {
        [*] --> connected_mock
        note right of connected_mock
            Always 'connected'
            Cassette events flow instantly
        end note
    }
```

---

## Diagram 3 — Store Dispatch Topology

All shared logic lives in `@aether/core` (FI-2). The bridge driver dispatches backend events directly to the appropriate decoupled Zustand stores, updating different slices of the application state asynchronously.

```mermaid
flowchart TB
    EVENTS["Incoming Validated Events (camelCase)"]
    
    EVENTS --> E_RS[RunStarted]
    EVENTS --> E_NES[NodeExecutionStarted]
    EVENTS --> E_NEF[NodeExecutionFinished]
    EVENTS --> E_BLU[BudgetLeaseUpdated]
    EVENTS --> E_MSD[ModelStreamDelta]
    EVENTS --> E_TSE[TaintSpanEmitted]

    subgraph STORES ["@aether/core Zustand Stores"]
        S_ENG[useEngineStore<br/>Connection, active run, log]
        S_WF[useWorkflowStore<br/>DAG nodes, edges, execution]
        S_BUD[useBudgetStore<br/>Reserve/commit ledger]
        S_TSE[useTaintStore<br/>Context spans, labels]
    end

    E_RS --> S_ENG
    E_RS --> S_WF
    
    E_NES --> S_WF
    E_NEF --> S_WF
    E_NEF --> S_BUD
    
    E_BLU --> S_BUD
    E_MSD --> S_ENG
    E_TSE --> S_TSE

    style STORES fill:#f4f4f4,stroke:#333,stroke-width:2px
```

---

## Diagram 4 — CLI Component Hierarchy

The TUI CLI is powered by React 19 + Ink. It renders purely text-based Flexbox layouts designed for constrained terminal window sizes while tapping into the exact same hooks as the desktop counterpart.

```mermaid
graph TD
    APP[App]
    APP --> HDR[Header]
    APP --> MAIN[MainPanel]
    APP --> FTR[Footer]
    
    HDR --> PI[PhaseIndicator]
    HDR --> BM[BudgetMeter]
    
    MAIN --> EL[EventLog]
    MAIN --> DV[DiffViewer]
    
    FTR --> KH[KeyboardHelp]
    FTR --> GSI[GateStatusIndicator]

    classDef cli fill:#000,stroke:#fff,color:#fff;
    class APP,HDR,MAIN,FTR,PI,BM,EL,DV,KH,GSI cli;
```

---

## Diagram 5 — Desktop GUI Component Hierarchy

The Desktop app utilizes Tauri v2 for native framing, rendering a React 19 SPA optimized for deep visibility into system execution, patching, and tracing.

```mermaid
graph TD
    APP[App]
    APP --> TB[Toolbar]
    APP --> ML[MainLayout]
    APP --> SB[StatusBar]
    
    ML --> TP[TreePanel]
    ML --> CP[CanvasPanel]
    ML --> EP[EditorPanel]
    
    CP --> WC[WorkflowCanvas / xyflow]
    WC --> CN[CustomNode]
    WC --> CE[ConditionalEdge]
    WC --> RLO[RepairLoopOverlay]
    
    EP --> MDE[MonacoDiffEditor]
    
    SB --> EL[EventLog]
    SB --> MB[MetricsBar]
```

---

## Diagram 6 — User Command Flow (Client → Engine)

When the operator decides to intervene, authorize patches, or stop a run, actions flow backwards to the engine (FI-4) via structured JSON-RPC command primitives.

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Component
    participant ST as Zustand Action
    participant DR as Bridge Driver
    participant EN as Backend (kernel/dispatch)

    U->>UI: Click 'Start Run'
    UI->>ST: startRun(topologyHash, budget)
    ST->>DR: Dispatch {commandType: "StartRun", payload}
    DR->>EN: Transmit via WS

    U->>UI: Review Monaco Diff -> Accept
    UI->>ST: acceptDiff(diffId, hunks)
    ST->>DR: Dispatch {commandType: "AcceptDiff"}
    DR->>EN: apply_patch via authorize->verify->lease->dispatch->release (operator provenance)

    U->>UI: Click 'Cancel Run'
    UI->>ST: cancelRun(reason)
    ST->>DR: Dispatch {commandType: "CancelRun"}
    DR->>EN: Release leases, halt execution

    Note over DR,EN: Backend validates all inbound commands.<br/>Unauthorized or invalid commands return RPC Error.<br/>AcceptDiff does not bypass the hard evaluation gates (I7-I9) —<br/>it is an operator-provenance effect, not a benchmark admission.
```

---

## Diagram 7 — Mock vs Live Mode Switching

Seamless testing and parallel development is enforced by the injection of the underlying stream implementation (FI-3). Both the live WS client and the mock cassette player fulfill the same contract.

```mermaid
flowchart TD
    INIT[App Startup]
    CHK{Check Env / Config}
    
    INIT --> CHK
    
    CHK -- "Mode = Live" --> LM[AetherWebsocketClient]
    CHK -- "Mode = Mock" --> MM[MockCassettePlayer]
    
    LM -- "Real WS Events" --> HOOK[useAetherStream]
    MM -- "Cassette JSON Events" --> HOOK
    
    HOOK --> COMP[React View Components]
    
    Note right of COMP: No conditional logic<br/>inside components.
```

---

## Diagram 8 — DAG Canvas Interaction Flow (Desktop)

The `xyflow` graph is the primary interactive surface for the user to understand what the orchestration loop is doing. Actions on the DAG directly expose telemetry.

```mermaid
sequenceDiagram
    actor U as User
    participant C as WorkflowCanvas (xyflow)
    participant N as CustomNode
    participant E as ConditionalEdge
    participant P as Tracing / Editor Panels
    
    Note over N: Node states update live: idle → running → passed/failed/none

    U->>N: Click Node
    N->>P: Inspect node trace / SpanViewer
    
    U->>E: Hover Edge
    E-->>U: Show conditional routing tooltips (on_pass, on_fail)
    
    Note over C: Repair Loop execution
    C->>C: Display RepairLoopOverlay (Iteration 1/3)
    
    Note over C: Fan-out execution
    C->>N: Expand Fan-out candidates
    N-->>U: Display N candidate lanes & status
```
