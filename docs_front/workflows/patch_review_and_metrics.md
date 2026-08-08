---
status: normative
updated: 2026-08-06
---

# Patch Review & Metrics Workflows (`docs_front/workflows/patch_review_and_metrics.md`)

This document visually details Monaco Editor patch diff review workflows and McNemar statistical self-improvement A/B testing loops.

---

## 1. Monaco Side-by-Side Patch Review & Patch Decision Workflow

When an agent node produces code modifications, the diff is stored in `usePatchStore` and rendered inside `MonacoDiffEditor.tsx` before committing.

```mermaid
flowchart TD
    AgentOutput["Agent Node Execution Finished"] --> GenDiff["Generate Git Unified Diff"]
    GenDiff --> StoreDiff["Add to usePatchStore.pendingDiffs"]
    StoreDiff --> RenderMonaco["Render Side-by-Side Diff in Monaco Editor"]

    RenderMonaco --> OperatorAction{"Operator Decision"}
    OperatorAction -- "Accept Diff" --> SendAccept["Dispatch AcceptDiff Command"]
    OperatorAction -- "Reject Diff" --> SendReject["Dispatch RejectDiff Command"]

    SendAccept --> EngineApply["Backend applies patch to workspace"]
    SendReject --> EngineRevert["Backend discards patch & logs rationale"]
```

---

## 2. McNemar Statistical Self-Improvement A/B Test Loop

When the meta-loop proposes topology, prompt, or skill mutations, A/B benchmark evaluation is conducted. The front-end renders McNemar statistical tests and Holm–Bonferroni confidence intervals ($\alpha = 0.05$).

```mermaid
sequenceDiagram
    autonumber
    participant MetaLoop as Evolution / Meta-Loop
    participant Evaluator as Measurement Evaluator
    participant Store as useMetricsStore
    participant Dashboard as MetricsDashboard (GUI)
    actor Operator as Operator

    MetaLoop->>Evaluator: Evaluate Candidate Mutation (Hash: cand_top_v2) vs Baseline (base_top_v1)
    Evaluator->>Evaluator: Calculate McNemar p-value & Holm-Bonferroni 95% CI
    Evaluator->>Store: Add ABTestResult (p = 0.024, CI = [0.08, 0.22])
    Store->>Dashboard: Update Metrics Dashboard View
    alt Statistically Significant (p < 0.05) & Gate Passed
        Dashboard->>Operator: Highlight "ADMITTED (GATE PASSED)"
        Operator->>MetaLoop: Approve Topology Mutation Pin
    else Gate Failed or Insufficient Lift
        Dashboard->>Operator: Highlight "REJECTED"
        Operator->>MetaLoop: Trigger Structural Topology Rollback
    end
```
