---
status: rationale
updated: 2026-08-07
---

# Architecture Diagrams

**Four diagrams, consolidated from the six files that used to be `docs/workflows/` plus
`development/system_workflows_and_diagrams.md`.** Everything that merely restated
[`spec.md` §3](./spec.md#3-structure)'s lattice table or [`vision.md` §3](./vision.md#3-architecture-at-altitude)'s
component graph was dropped rather than merged — a diagram whose only content is a second
rendering of a normative table is a drift risk, not an aid.

> [!IMPORTANT]
> **These diagrams show the target architecture, and parts of it are not built.**
> `agency/loop.py`, `agency/context/`, `kernel/shell_ast.py` and `evolution/` appear below and
> **do not exist in `src/aether/` today** — they are `TASK-053`–`058`, `TASK-030a` and a
> post-M4 milestone respectively. [`STATUS.md`](./STATUS.md) is the authority on what is
> implemented; when a diagram and the code disagree, **the diagram is the bug**
> ([`README.md`](../README.md)).

---

## 1. End-to-end orchestration

Client → headless engine → validated topology → executor → the dispatch choke point → adapters
→ TCB evaluator → event bus. Every arrow into an adapter passes through `kernel/dispatch.py`;
there is no second path, and an architecture test proves it.

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

---

## 2. The inner loop — one task

`retrieve → generate → apply → evaluate`, then the bounded repair edge statically unrolled to
`max_iterations`. Two properties this diagram is drawn to show: **a `GateStatus.NONE` never
routes into repair** (an instrument failure is not a repair candidate), and **each iteration
reserves its own budget** through the governor's reserve/commit/release triple.

```mermaid
sequenceDiagram
    autonumber
    participant Engine as engine.py
    participant Executor as workflow/executor.py (TCB)
    participant Agency as agency/loop.py
    participant Context as agency/context (Assembler)
    participant Dispatch as kernel/dispatch.py (TCB Choke Point)
    participant Model as ModelProvider Adapter
    participant Worktree as Workspace/Worktree Adapter
    participant Sandbox as Tool Container Sandbox
    participant Evaluator as measurement/evaluator.py (TCB)

    Engine->>Executor: run(topology_hash, task_id, budget)
    Note over Executor: Validate DAG graph & unroll repair edges<br/>(ADR-0013 / ADR-0014)

    rect rgb(240, 245, 255)
    Note over Executor, Worktree: Step 1: Retrieval Node
    Executor->>Agency: execute(retrieve_node, task)
    Agency->>Dispatch: authorize(read_repo) → verify grant → acquire lease
    Dispatch->>Worktree: dispatch: search_symbols / read_files
    Worktree-->>Agency: source files, specs [provenance: untrusted-external]
    end

    rect rgb(240, 255, 240)
    Note over Executor, Model: Step 2: Generation Node
    Agency->>Context: assemble_context(spans L1..L5, taint-labeled)
    Context-->>Agency: ContextWindow (taint provenance attached)
    Agency->>Dispatch: authorize(model_call) → verify → lease(tokens, usd)
    Dispatch->>Model: dispatch: stream completion
    Model-->>Agency: ModelStreamEvents (deltas, tool calls)
    Dispatch->>Dispatch: commit(lease, actual_usage)
    end

    rect rgb(255, 250, 235)
    Note over Executor, Sandbox: Step 3: Application Node
    Agency->>Dispatch: authorize(write_worktree) → verify → lease
    Dispatch->>Worktree: dispatch: apply diff patch to isolated candidate worktree
    opt Agent-Requested Tool / Shell Command
        Agency->>Dispatch: authorize(shell_command)
        Dispatch->>Dispatch: kernel/shell_ast classifies command (ADR-0008)
        Dispatch->>Sandbox: dispatch in tool container (network=none)
        Sandbox-->>Agency: stdout/exit code [provenance: untrusted-external]
    end
    end

    rect rgb(255, 240, 240)
    Note over Executor, Evaluator: Step 4: Evaluation Node (TCB Boundary)
    Executor->>Dispatch: authorize(evaluate) → verify → lease(eval_slot)
    Dispatch->>Evaluator: dispatch: run pinned test command in eval container
    Evaluator-->>Executor: GateReport { status: True | False | None }
    end

    loop Bounded Repair Loop (i ≤ k static bound)
        alt GateReport.status == False (Test Failure)
            Evaluator-->>Agency: failure tail-truncated block [untrusted-external]
            Note over Agency: Node: Repair<br/>Inject failure log into context window<br/>Re-plan minimal delta patch
            Agency->>Dispatch: authorize(model_call) + apply patch
            Dispatch->>Worktree: write updated candidate diff
            Executor->>Dispatch: authorize(re-evaluate)
            Dispatch->>Evaluator: run pinned test suite
            Evaluator-->>Executor: GateReport { status }
        else GateReport.status == True (Resolved)
            Note over Executor: Exit repair loop: Task RESOLVED
        else GateReport.status == None (Instrument Error B4)
            Note over Executor: Flag run as instrument_error<br/>Never score as failure or data point
        end
    end

    Executor-->>Engine: RunResult (resolved | unresolved | instrument_error)
```

---

## 3. The outer loop — measurement and admission

A run over N tasks × arms producing paired outcomes, through the statistics engine, against a
**pre-declared** gate family. The TCB boundary is the point: the mutable surface on the left
proposes; the immutable measurement suite on the right decides, and cannot be edited by what it
is judging.

```mermaid
flowchart TD
    %% Offline Evolution Space
    subgraph MUTABLE_SURFACE["Mutable Surface (Meta-Loop Auto-Commit Eligible)"]
        PROMPTS["System Prompts & Prompt Layers"]
        SKILLS["Agent Skills & Tool Instructions"]
        TOPOLOGY["workflow/*.yaml (Workflow Topologies as Data)"]
        RETRIEVAL["Retrieval Hyperparameters & Compactor Rules"]
    end

    %% Evolution Engine
    subgraph EVOLUTION_ENGINE["evolution/ (Offline Optimizer - Pure Sandbox)"]
        MUTATOR["Meta-Improver / Topology Mutator"]
        PROPOSER["Generate Candidate Harness Variation V'"]
    end

    %% TCB Gate & Benchmark Execution
    subgraph TCB_EVALUATION["TCB Measurement & Gate Suite (Immutable - I8)"]
        MANIFEST["Pinned Task Manifests (SWE-bench Pro / Verified)"]
        RUNNER["measurement/runner.py"]
        SUITE_A["Arm A: Baseline Harness Configuration V"]
        SUITE_B["Arm B: Candidate Harness Variation V'"]
        HARVEST["measurement/harvester.py (Timer & Cost Collector)"]
    end

    %% Statistical Admission Control
    subgraph ADMISSION_GATE["ADR-0003 Rev 2 Holdout Gate Admission"]
        MCNEMAR["Exact McNemar Test (Paired Binary Outcomes)"]
        HOLM["Holm-Bonferroni Correction (α = 0.05 Family-wise)"]
        COST_CHECK["Non-Inferiority Cost Check (Cost/Resolved Task ≤ +20%)"]
        AA_CHECK{"A/A Variance Floor Verified?"}
    end

    %% Verdict Outcomes
    subgraph VERDICT_OUTCOMES["Admission Outcomes"]
        ADMITTED["ADMITTED: Merge V' to Default Topology Pin"]
        REJECTED["REJECTED: Discard Candidate V' (Record Negative Result)"]
        PR_REQ["PR REQUIRED: Structural / TCB File Changes"]
    end

    %% Connections
    MUTABLE_SURFACE --> MUTATOR
    MUTATOR --> PROPOSER
    PROPOSER -->|Submit Harness Candidate V'| RUNNER
    MANIFEST --> RUNNER
    
    RUNNER -->|Run Paired Evaluation| SUITE_A & SUITE_B
    SUITE_A & SUITE_B --> HARVEST
    HARVEST --> AA_CHECK
    
    AA_CHECK -->|No Floor Established| REJECTED
    AA_CHECK -->|Passed Floor| MCNEMAR
    
    MCNEMAR --> HOLM
    HOLM --> COST_CHECK
    
    COST_CHECK -->|All Gates Passed| ADMITTED
    COST_CHECK -->|Statistically Insignificant or Inferior Cost| REJECTED
    
    MUTATOR -.->|If mutating code in TCB| PR_REQ

    %% Styling
    style TCB_EVALUATION fill:#ffe0e0,stroke:#c00,stroke-width:2px
    style ADMISSION_GATE fill:#fff0f0,stroke:#fbb
    style MUTABLE_SURFACE fill:#e8ffe8,stroke:#090
```

---

## 4. The dispatch lifecycle (CAR model)

`authorize → verify grant → acquire lease → dispatch → release`. **Verification happens at the
point of effect, not at authorization time** — arguments can drift between issuance and use,
and a resumed run can carry a stale grant. That re-check is the subtle requirement, and it is
why the seam stays a distinct named step even where it is currently a precondition rather than
a full two-phase flow.

```mermaid
flowchart TD
    %% Requester
    REQ["Agency / Workflow Step Requesting Effect"]

    %% Kernel Dispatch Lifecycle
    subgraph DISPATCH_CHOKE_POINT["kernel/dispatch.py — Single Dispatch Choke Point (I5)"]
        AUTH["1. authorize(capability, params)"]
        POL_CHECK{"2. PolicyEngine.authorize()<br/>Evaluate CAR Predicates"}
        GRANT_GEN["Generate Capability Grant"]
        
        VERIFY["3. verify_grant(grant, target_params)<br/>(Verified at effect time, not grant time)"]
        VERIFY_CHECK{"Grant Valid & Unexpired?"}

        LEASE_ACQ["4. acquire_lease(resource_type, budget)"]
        GOV_CHECK{"ResourceGovernor:<br/>Budget Available?"}
        
        EXEC["5. dispatch(adapter_method, payload)"]
        ADAPTER_CALL["Invoke Subordinate Port Adapter"]
        
        COMMIT["6. commit / release(lease, actual_usage)"]
        BUS_EMIT["Emit Effect Execution Event to Bus"]
    end

    %% Outcomes
    DENIED_POL["DENIED: Policy Violation (AskFailClosed / Reject)"]
    DENIED_GOV["DENIED: Budget Overrun"]
    SUCCESS["EFFECT COMPLETED & RETURNED"]

    %% Flow connections
    REQ --> AUTH --> POL_CHECK
    POL_CHECK -->|Pass| GRANT_GEN --> VERIFY
    POL_CHECK -->|Fail| DENIED_POL
    
    VERIFY --> VERIFY_CHECK
    VERIFY_CHECK -->|Valid| LEASE_ACQ
    VERIFY_CHECK -->|Invalid / Stale| DENIED_POL
    
    LEASE_ACQ --> GOV_CHECK
    GOV_CHECK -->|Budget Available| EXEC
    GOV_CHECK -->|Exceeded| DENIED_GOV
    
    EXEC --> ADAPTER_CALL --> COMMIT --> BUS_EMIT --> SUCCESS

    style DISPATCH_CHOKE_POINT fill:#ffe0e0,stroke:#c00,stroke-width:2px
```

---

## What was dropped, and why

| Source | Disposition |
| :--- | :--- |
| `workflows/architecture.md` | Port/adapter lattice — duplicated `spec.md` §3's table and `vision.md` §3's graph, both normative or canonical |
| `workflows/README.md` | An index for a directory that no longer exists |
| `workflows/main_features.md` §2–3 | Governor reservation and taint propagation — `spec.md` §5 and ADR-0015 state both, and stated once is enough |
| `development/system_workflows_and_diagrams.md` | Orphan; overlapped every diagram above |
