# Inner Loop & Bounded Repair Workflow

This workflow documents the inner execution loop of **AETHER**, detailing DAG node unrolling, context assembly with taint labeling, candidate code generation, worktree patch application, AST shell classification, gate evaluation, and the static bounded repair cycle ($i \le k$).

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

## Detailed Inner Loop Logic

```mermaid
flowchart TD
    START([Start Node Execution]) --> RETRIEVE[1. Retrieve Context & Files]
    RETRIEVE --> TAINT_LABEL[Label Spans: untrusted-external]
    TAINT_LABEL --> ASSEMBLE[2. Assemble Context L1..L5 Prefix]
    
    ASSEMBLE --> REQ_MODEL[3. Request LLM Candidate Code]
    REQ_MODEL --> DISP_MODEL{Kernel Dispatch Choke Point}
    DISP_MODEL -->|Check Taint & Lease| MODEL_EXEC[Invoke ModelProvider Adapter]
    MODEL_EXEC --> PATCH_GEN[Candidate Diff Patch Produced]
    
    PATCH_GEN --> APPLY_PATCH[4. Apply Patch to Worktree Candidate]
    APPLY_PATCH --> AST_CHECK{Shell AST Command Requested?}
    
    AST_CHECK -->|Yes| AST_CLASS[Classify Shell AST]
    AST_CLASS --> SBX_EXEC[Run in Network-Isolated Container]
    SBX_EXEC --> EVAL_NODE
    AST_CHECK -->|No| EVAL_NODE
    
    EVAL_NODE[5. Run Gate Evaluation in TCB Container] --> GATE_VERDICT{GateReport Status}
    
    GATE_VERDICT -->|True| RESOLVED([Task Resolved Successfully])
    GATE_VERDICT -->|None| INSTR_ERR([Instrument Error B4 - Flagged Run])
    
    GATE_VERDICT -->|False| BOUND_CHECK{Repair Iterations i ≤ k?}
    BOUND_CHECK -->|Yes (i < k)| REPAIR[Node: Repair - Feed Tail Truncated Log]
    REPAIR --> ASSEMBLE
    BOUND_CHECK -->|No (i > k)| UNRESOLVED([Task Unresolved - Exceeded Repair Bound])

    style DISP_MODEL fill:#ffe0e0,stroke:#c00
    style EVAL_NODE fill:#ffe0e0,stroke:#c00
```

## Key Invariants & Rules

- **Bounded Repair ($i \le k$)**: The unroll limit $k$ is statically configured in `workflow_schema.repair.max_iterations`. Infinite repair loops are prohibited.
- **Instrument Error ($B4$) handling**: Tri-state `GateReport` emits `None` on container or execution environment failures (e.g. exit code 127). Instrument failures are never counted as code test failures.
- **Taint Monotonicity**: Output generated from consumption of `untrusted-external` inputs is labeled `untrusted-derived` and cannot satisfy capability-widening requests.
