---
status: normative
updated: 2026-08-06
---

# Front-End Vision & UX Architecture (`docs_front/vision.md`)

## 1. Executive Summary

The AETHER Front-End Client Suite empowers human operators and AI agent trainers to inspect, control, and evolve the **AETHER Coding Agent Orchestrator AGI**.

Rather than treating agent execution as a opaque black-box terminal loop, AETHER provides **visual observability, interactive DAG manipulation, and immediate execution feedback**—combining the power of node-graph workflow tools like **n8n** and **ComfyUI** with the precision of modern developer IDEs.

---

## 2. Core User Interfaces

```
                                  +---------------------------------------+
                                  |    AETHER Engine Core (src/aether)    |
                                  +---------------------------------------+
                                                      |
                                     WebSocket / SSE Event Stream Bridge
                                                      |
                 +------------------------------------+------------------------------------+
                 |                                                                         |
                 v                                                                         v
+-------------------------------------------------+     +-------------------------------------------------+
|               TUI CLI (Terminal)                |     |              GUI Desktop (Windows/Linux)         |
|             src_front/apps/cli                  |     |             src_front/apps/desktop              |
|                                                 |     |                                                 |
|  • Framework: React + Ink                       |     |  • Shell: Tauri v2 (Rust)                       |
|  • Ideal for: Terminal workflow, CI execution,  |     |  • Framework: React 19 + Tailwind CSS           |
|    keyboard-only SSH sessions                   |     |  • Node Canvas: xyflow (React Flow)             |
|  • Key Features: Real-time turn logs, AST parse |     |  • Code Editor: Monaco Editor (VS Code core)    |
|    tree views, live cost & token counters       |     |  • Ideal for: Visual DAG editing, live trace    |
|                                                 |     |    debugging, self-improvement review           |
+-------------------------------------------------+     +-------------------------------------------------+
```

---

## 3. Key UX Pillars

### Pillar 1: ComfyUI / n8n-Style Workflow DAG Graph
Users can visually construct, inspect, and tweak execution topologies. Nodes represent workflow steps (`Retrieve`, `Generate`, `Apply`, `Evaluate`, `Repair`), while edges denote data sockets and tri-state evaluation routing (`on_pass`, `on_fail`, `on_instrument_error`).

### Pillar 2: Live Execution Trace & Taint Audit
Every node on the canvas reflects its execution state in real time:
* **Idle** (gray) $\rightarrow$ **Running** (animated pulse) $\rightarrow$ **Passed** (green) / **Failed** (red) / **Instrument Error** (amber).
* Clicking any node or context span reveals its **TaintGate provenance label** (`trusted-system`, `operator`, `agent`, `untrusted-external`, `untrusted-derived`) per ADR-0015.

### Pillar 3: Split Code Diff & Patch Review
When an agent node generates code modifications, the user can inspect unified diffs side-by-side inside an embedded Monaco Editor before patches are committed or pushed.

### Pillar 4: Harness Self-Improvement Monitor
When the meta-loop proposes prompt, skill, or topology mutations (Milestones M4–M5), the GUI renders side-by-side A/B statistical evaluation metrics (McNemar p-values, Holm–Bonferroni confidence intervals, token cost deltas) allowing operators to approve or roll back candidate harness improvements.

---

## 4. Performance & Responsiveness Targets

* **TUI CLI**: Startup time $< 100\text{ ms}$, memory usage $< 60\text{ MB}$, zero rendering lag at 30+ FPS stream ingestion.
* **GUI Desktop**: App bundle installer $< 20\text{ MB}$ (via Tauri v2 Webview2 / WebKitGTK), idle memory $< 40\text{ MB}$, 60 FPS canvas panning/zooming for graphs up to 500 nodes via `xyflow`.
