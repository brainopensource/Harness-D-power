---
status: normative
updated: 2026-08-06
---

# Architecture & Monorepo Topology Workflows (`docs_front/workflows/architecture_and_topology.md`)

This document visually details the monorepo package structure, dependency rules, and Zustand state store topology across `src_front/`.

---

## 1. Monorepo Package Lattice & Import Boundaries

All code resides in `src_front/` managed via **pnpm workspaces** and **Turborepo**. Direct imports from backend `src/aether/` are strictly forbidden (FI-1 invariant).

```mermaid
graph TD
    subgraph Packages ["Monorepo Core Packages"]
        Core["@aether/core<br/>(Stores, Hooks, WS Client, Schemas)"]
        UI["@aether/ui-components<br/>(Tailwind v4 Components)"]
        MockServer["@aether/mock-server<br/>(Cassette Replay Engine)"]
    end

    subgraph Apps ["Executable Client Applications"]
        CLIApp["@aether/cli<br/>(React 19 + Ink TUI Terminal)"]
        DesktopApp["@aether/desktop<br/>(Tauri v2 + React 19 GUI App)"]
    end

    MockServer -->|imports types/stores| Core
    CLIApp -->|consumes| Core & MockServer
    DesktopApp -->|consumes| Core & UI & MockServer
```

---

## 2. Partitioned Zustand Domain Store Topology

State management in `@aether/core` is partitioned into **six independent domain stores** to prevent cross-store re-render pollution.

```mermaid
graph LR
    subgraph Core Stores ["@aether/core Domain Stores"]
        S1["useEngineStore<br/>• Connection status<br/>• Active run ID<br/>• Raw event log buffer"]
        S2["useWorkflowStore<br/>• Topology ID<br/>• Node states & GateStatus<br/>• Edge conditional routing"]
        S3["useBudgetStore<br/>• Integer BudgetDims<br/>• Reserved / Committed / Remaining<br/>• Overrun records"]
        S4["usePatchStore<br/>• Pending code diffs<br/>• Accept/Reject status<br/>• Patch hunks"]
        S5["useMetricsStore<br/>• McNemar p-values<br/>• Holm-Bonferroni CIs<br/>• A/B test results"]
        S6["useTaintStore<br/>• Context spans<br/>• Provenance labels<br/>• Inspected span ID"]
    end
```

---

## 3. UI Component Hierarchy & View Wiring

```mermaid
graph TD
    subgraph CLI Tree ["@aether/cli (React + Ink)"]
        AppCLI["App.tsx"]
        HeaderCLI["Header.tsx"]
        BudgetCLI["BudgetMeter.tsx"]
        StreamCLI["TurnLogStream.tsx"]
        GateCLI["GateStatusIndicator.tsx"]
        CmdCLI["CommandRunner.tsx"]
        AppCLI --> HeaderCLI & BudgetCLI & StreamCLI & CmdCLI
        StreamCLI --> GateCLI
    end

    subgraph Desktop Tree ["@aether/desktop (Tauri + React 19)"]
        AppGUI["App.tsx"]
        HeaderGUI["HeaderControls.tsx"]
        CanvasGUI["WorkflowCanvas.tsx (xyflow)"]
        TraceGUI["LiveTraceInspector.tsx"]
        TaintGUI["TaintAuditPanel.tsx"]
        DiffGUI["MonacoDiffEditor.tsx"]
        MetricsGUI["MetricsDashboard.tsx"]
        AppGUI --> HeaderGUI & CanvasGUI & TraceGUI & TaintGUI & DiffGUI & MetricsGUI
    end
```
