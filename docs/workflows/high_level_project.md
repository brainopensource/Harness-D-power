# High-Level Project Workflow

This workflow documents the end-to-end orchestration cycle of the **AETHER AGI Agent Coding LLM Orchestrator**, from client invocation down through workflow execution, kernel dispatch, sandbox execution, TCB evaluation, and event streaming.

```mermaid
flowchart TD
    %% Client & Headless Engine Layer
    subgraph CLIENT_LAYER["Client & Headless Interface Layer"]
        CLI["CLI / TUI / CI Client"]
        ENGINE["engine.py (Headless API)"]
        QUEUE["Domain Task Queue"]
    end

    %% Workflow Orchestration Layer
    subgraph WORKFLOW_LAYER["Workflow Orchestration Layer (TCB-Adjacent)"]
        VAL["workflow/validator.py<br/>(Schema & DAG Verification)"]
        EXE["workflow/executor.py<br/>(Declarative DAG Engine)"]
    end

    %% Agency & Context Assembly Layer
    subgraph AGENCY_LAYER["Agency Layer (Mutable Loop & Context)"]
        AGENCY["agency/loop.py<br/>(Agent Execution Controller)"]
        CTX["agency/context/<br/>(Span Assembler & Compactor)"]
        TAINT["taint_gate<br/>(Provenance Auditor)"]
    end

    %% Kernel Choke Point (TCB)
    subgraph KERNEL_LAYER["Kernel Layer (TCB - Security & Dispatch)"]
        DISP[["kernel/dispatch.py<br/>SINGLE DISPATCH CHOKE POINT (I5)"]]
        POL["kernel/policy.py<br/>(PolicyEngine - CAR Model)"]
        GOV["kernel/governor.py<br/>(ResourceGovernor - USD/Tokens)"]
        BUS["kernel/bus.py<br/>(Append-Only Event Stream)"]
    end

    %% Adapters & Execution Sandbox
    subgraph ADAPTER_LAYER["Adapters & Execution Container Layer"]
        MP["adapters/model_provider/<br/>(Anthropic / OpenAI API)"]
        WS["adapters/workspace/<br/>(Git CLI / Worktree Manager)"]
        SBX["adapters/sandbox/<br/>(Podman Tool Container)"]
    end

    %% Measurement & Evaluator (TCB)
    subgraph MEASUREMENT_LAYER["Measurement Layer (TCB - Judge)"]
        EVAL["measurement/evaluator.py<br/>(Isolated Eval Container - I7/I8)"]
        REPORT["GateReport {True | False | None}"]
    end

    %% Consumers
    subgraph CONSUMERS["Event Consumers"]
        TSTORE["TrajectoryStore (SQLite WAL)"]
        UI_FEED["TUI / Console Live Stream"]
    end

    %% High-level Flow Connections
    CLI -->|1. Submit Task Request| ENGINE
    ENGINE -->|2. Enqueue Task| QUEUE
    QUEUE -->|3. Trigger Execution| EXE
    EXE -->|4. Validate Graph Topology| VAL
    EXE -->|5. Execute Nodes| AGENCY
    
    AGENCY -->|6. Assemble Context & Spans| CTX
    CTX -->|7. Label Provenance| TAINT
    
    AGENCY -->|8. Request Effect Authorization| DISP
    DISP <-->|8a. Verify Policy & Lease Budget| POL & GOV
    
    DISP -->|9a. Model Call| MP
    DISP -->|9b. Workspace I/O| WS
    DISP -->|9c. Execute Tool / Shell| SBX
    
    EXE -->|10. Dispatch Evaluation| DISP
    DISP -->|11. Run Pinned Test Digest| EVAL
    EVAL -->|12. Output Verdict| REPORT
    REPORT -->|13. Return Gate Status| EXE

    DISP -.->|Emit Events| BUS
    EXE -.->|Emit Workflow Events| BUS
    BUS -->|Subscribe| TSTORE & UI_FEED

    %% Styling
    style DISP fill:#ffe0e0,stroke:#c00,stroke-width:2px
    style EVAL fill:#ffe0e0,stroke:#c00,stroke-width:2px
    style KERNEL_LAYER fill:#fff0f0,stroke:#fbb
    style MEASUREMENT_LAYER fill:#fff0f0,stroke:#fbb
    style CLIENT_LAYER fill:#f0f5ff,stroke:#99b
```

## Key Invariants Documented

1. **Single Dispatch Choke Point (I5)**: All interactions with models, filesystem worktrees, shell execution, and evaluators must cross `kernel/dispatch.py`. Direct adapter invocations from agency or workflow layers are prohibited.
2. **Generator $\ne$ Evaluator Isolation (I7 & I8)**: `agency/` can never reach `measurement/evaluator.py`. Evaluation commands execute pinned container images defined in immutable manifests.
3. **Observation via Append-Only Event Bus**: The workflow graph drives node execution; `kernel/bus.py` streams observation events out to `TrajectoryStore` and client interfaces asynchronously without driving scheduling decisions.
