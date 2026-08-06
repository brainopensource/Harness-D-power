# AETHER — Backend Workflows & System Diagrams

This directory contains the canonical Mermaid workflow charts for **AETHER v3.0.0**, the autonomous coding harness and AGI agent LLM orchestrator. These diagrams document and specify the system's operational control flows, security gating, execution loops, and structural architecture for printing, documentation, and technical review.

## Workflow Index

| Document | Focus & Scope | Description |
| :--- | :--- | :--- |
| [`high_level_project.md`](./high_level_project.md) | **High-Level Project Workflow** | End-to-end task orchestration from `Engine` entry point down to execution, evaluation, and event bus broadcast. |
| [`inner_loop.md`](./inner_loop.md) | **Inner Loop & Bounded Repair** | Step-by-step DAG node processing, context assembly, patch application, AST shell classification, and bounded repair loop ($i \le k$). |
| [`outer_loop.md`](./outer_loop.md) | **Outer Loop & Meta-Improvement** | Offline topology/prompt/skill evolution, TCB immutability protection, McNemar + Holm–Bonferroni holdout gate evaluation, and A/A variance floor. |
| [`main_features.md`](./main_features.md) | **Core Backend Features** | Capability Authorization (CAR Model), Kernel Dispatch Choke Point (`authorize` → `verify` → `lease` → `dispatch` → `release`), Resource Governor, and TaintGate security propagation. |
| [`architecture.md`](./architecture.md) | **Port-Adapter Architecture** | System component layers, strict import lattice (`engine > agency/workflow > kernel > adapters > ports > domain`), and TCB vs. mutable layer boundaries. |

---

## Rendering & Printing Instructions

All diagrams in these documents are standard **Mermaid** blocks (` ```mermaid `).

- **In IDE / Markdown Viewers**: VS Code, Antigravity IDE, GitHub, and GitLab render Mermaid automatically in preview mode.
- **CLI Rendering**: To export to PNG/SVG/PDF for print or design reviews, use `@mermaid-js/mermaid-cli`:
  ```bash
  npx @mermaid-js/mermaid-cli -i docs/workflows/high_level_project.md -o docs/workflows/high_level_project.pdf
  ```
- **Live Editing & Review**: Copy diagram blocks directly into [Mermaid Live Editor](https://mermaid.live).
