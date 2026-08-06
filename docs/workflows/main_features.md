# Core Backend Features Workflow

This document details the primary backend features of the **AETHER LLM Orchestrator Harness**, including:
1. **Capability Authorization (CAR Model)** & Kernel Dispatch Lifecycle (`authorize` $\rightarrow$ `verify grant` $\rightarrow$ `acquire lease` $\rightarrow$ `dispatch` $\rightarrow$ `release`).
2. **Resource Governor** token & USD reservation workflow.
3. **TaintGate Security Propagation** & Untrusted Content Containment (Invariant **I11**).

---

## 1. Kernel Dispatch & CAR Model Authorization Workflow

Every side effect in AETHER must pass through the single dispatch choke point in `kernel/dispatch.py`. Verification occurs at the point of effect execution—not authorization time—preventing stale grant re-use.

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

## 2. Resource Governor Reserve-Commit-Release Workflow

Budget is reserved before execution to handle fan-out branch allocations correctly, rather than accounting after effects complete.

```mermaid
sequenceDiagram
    autonumber
    participant Step as Agency / Workflow Step
    participant Kernel as kernel/dispatch.py
    participant Governor as kernel/governor.py (TCB)
    participant Adapter as Port Adapter (Model/Sandbox)

    Step->>Kernel: Request effect with budget estimation (Max Tokens, Max USD)
    Kernel->>Governor: reserve_lease(resource_id, estimated_cost)
    
    alt Budget Available
        Governor-->>Kernel: LeaseGranted { lease_id, reserved_amount }
        Kernel->>Adapter: dispatch(effect_payload)
        Adapter-->>Kernel: EffectResult { actual_tokens, actual_usd, status }
        Kernel->>Governor: commit_lease(lease_id, actual_cost)
        Governor-->>Kernel: LeaseCommitted (Unused reserve returned to pool)
        Kernel-->>Step: Return EffectResult
    else Budget Exceeded
        Governor-->>Kernel: LeaseDenied { reason: "Token / USD Budget Exceeded" }
        Kernel-->>Step: Raise BudgetExceededError (Halt Branch Execution)
    end
```

---

## 3. TaintGate Provenance & Capability Security Workflow (Invariant I11)

Context spans carry provenance labels. Untrusted spans (e.g. repo code, issue text, web search results, shell stdout) produce `untrusted-derived` LLM outputs. Untrusted content can *inform* work, but can **never satisfy policy predicates that grant or widen execution authority**.

```mermaid
flowchart TB
    subgraph SPAN_SOURCES["Context Span Sources & Provenance Labels"]
        S1["System Prompt & Builtin Policy<br/>Label: trusted-system"]
        S2["Operator Console Input<br/>Label: operator"]
        S3["Agent Prior Reasoning Outputs<br/>Label: agent"]
        S4["Repo Files, Issue Text, Tool Stdout, Web/MCP<br/>Label: untrusted-external"]
    end

    subgraph CONTEXT_ASSEMBLER["Context Assembler & Compactor"]
        ASM["Assemble L1..L5 Context Window<br/>(Preserve span-level labels)"]
    end

    subgraph LLM_GENERATION["Model Completion Step"]
        MODEL["Model Completion Stream"]
    end

    subgraph PROV_PROPAGATION["Deterministic Provenance Propagation"]
        PROP_CHECK{"Completion consumed ANY<br/>untrusted-external or<br/>untrusted-derived span?"}
        DERIVED["Output Spans Labeled: untrusted-derived"]
        AGENT_LBL["Output Spans Labeled: agent"]
    end

    subgraph POLICY_AUDIT["kernel/policy.py (Dispatch Choke Point Audit)"]
        EFFECT_REQ["Agent Effect Request<br/>(e.g., capability-widening ask: shell execution)"]
        TAINT_AUDIT["TaintGate Audit:<br/>Inspect justifying context spans"]
        PREDICATE{"Predicate Check:<br/>Are justifying spans ∈ {trusted-system, operator}?"}
        GRANT_OK["GRANT: Execute Dispatch"]
        DENY_FAIL["REJECT / FAIL CLOSED:<br/>Untrusted content attempted capability escalation!"]
    end

    %% Flow
    S1 & S2 & S3 & S4 --> ASM --> MODEL --> PROP_CHECK
    PROP_CHECK -->|Yes| DERIVED
    PROP_CHECK -->|No| AGENT_LBL
    
    DERIVED & AGENT_LBL --> EFFECT_REQ --> TAINT_AUDIT --> PREDICATE
    PREDICATE -->|Pass| GRANT_OK
    PREDICATE -->|Fail| DENY_FAIL

    style S4 fill:#fdd,stroke:#c00
    style DERIVED fill:#fdd,stroke:#c00
    style POLICY_AUDIT fill:#ffe0e0,stroke:#c00
```

## Key Feature Invariants

- **Grant Verification at Effect Time (I5)**: Capability grants are checked right before dispatching the effect, avoiding authorization race conditions.
- **Pre-Execution Budget Reservations**: `ResourceGovernor` reserves estimated costs to prevent runaway parallel branch overruns.
- **Taint Security Boundary (I11)**: Prompt injections in repo files or issues cannot hijack execution authority because untrusted-derived spans fail capability-widening policy predicates closed.
