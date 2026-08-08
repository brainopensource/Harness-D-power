---
status: normative
updated: 2026-08-06
---

# Security & Taint Audit Workflows (`docs_front/workflows/security_and_taint_audit.md`)

This document visually details TaintGate provenance tracking, prompt layer security assembly, and front-end unprivileged action authorization.

---

## 1. Context Span Provenance Labeling & Taint Audit

Every context span used during LLM prompt assembly carries a provenance label (`domain/taint.py`, ADR-0015). Untrusted spans can never acquire capability grants (I11 invariant).

```mermaid
flowchart TD
    subgraph Span Origins ["Context Span Sources"]
        SystemPrompt["System Prompt Prefix L1"] --> L1["Provenance.TRUSTED_SYSTEM"]
        OperatorCmd["Operator Task Command"] --> L2["Provenance.OPERATOR"]
        AgentCode["Agent Generated Patch"] --> L3["Provenance.AGENT"]
        RepoIssue["Retrieved Repo Issue / Web Docs"] --> L4["Provenance.UNTRUSTED_EXTERNAL"]
        DerivedSummary["LLM Summarized Context"] --> L5["Provenance.UNTRUSTED_DERIVED"]
    end

    subgraph FrontEnd ["TaintAuditPanel Inspector"]
        L1 --> Badge1["[TRUSTED_SYSTEM] Blue Badge"]
        L2 --> Badge2["[OPERATOR] Cyan Badge"]
        L3 --> Badge3["[AGENT] Magenta Badge"]
        L4 --> Badge4["[UNTRUSTED_EXTERNAL] Red Warning Badge"]
        L5 --> Badge5["[UNTRUSTED_DERIVED] Yellow Badge"]
    end

    subgraph Security Gate ["Backend PolicyEngine (kernel/policy.py)"]
        Badge4 & Badge5 --> Check{"Satisfies Policy Predicate?"}
        Check -- Untrusted Span --> Deny["Deny Capability Grant (I11)"]
        Check -- Trusted Span --> Grant["Grant Effect Lease"]
    end
```

---

## 2. Unprivileged Consumer & Action Authorization Flow

The front-end is an unprivileged consumer (FI-4 rule). Operator actions (such as `AcceptDiff` or `StartRun`) are dispatched to the engine and must pass through `PolicyEngine.authorize()` in `kernel/dispatch.py`.

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Operator / Trainer
    participant GUI as Desktop GUI (MonacoDiffEditor)
    participant WS as AetherWebsocketClient
    participant Dispatch as kernel/dispatch.py
    participant Policy as PolicyEngine

    Operator->>GUI: Click "Accept Patch" Button
    GUI->>WS: sendCommand({ commandType: "AcceptDiff", runId, diffId })
    WS->>Dispatch: Authorize effect request
    Dispatch->>Policy: PolicyEngine.authorize(grant)
    alt Policy Granted
        Policy-->>Dispatch: Authorization Lease Granted
        Dispatch-->>WS: Emit EffectAuthorized event
        WS-->>GUI: Update diff status to ACCEPTED
    else Policy Denied
        Policy-->>Dispatch: Authorization Denied
        Dispatch-->>WS: Emit EffectDenied event
        WS-->>GUI: Render Denial Alert in Taint Panel
    end
```
