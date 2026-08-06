---
status: normative
updated: 2026-08-06
---

# AETHER Front-End Client Suite Documentation (`docs_front`)

Welcome to the normative documentation for the **AETHER Front-End Client Suite**. This documentation tree defines the architecture, design decisions, data contracts, and implementation plan for the visual and interactive surfaces of the AETHER Coding Agent Orchestrator AGI.

---

## 🎯 Front-End Vision & Mission

The front-end suite provides two primary interfaces to interact with the headless AETHER core (`src/aether/engine.py`):
1. **TUI CLI (`src_front/apps/cli`)**: A lightweight, fast, terminal-based dashboard built with **React + Ink**, designed for developers running tasks directly from the shell.
2. **GUI Desktop App (`src_front/apps/desktop`)**: A state-of-the-art visual node-graph workflow canvas built with **Tauri v2 + React 19 + `xyflow` (React Flow) + Monaco Editor**, designed for interactive DAG editing, real-time node trace monitoring, and harness self-improvement control (n8n / ComfyUI paradigm).

---

## 🏗️ Navigation Index

| Document | Tier | Description |
| :--- | :---: | :--- |
| [`vision.md`](./vision.md) | 1 | Orientation, mission statement, UX principles, and altitude architecture. |
| [`spec.md`](./spec.md) | 2 | **Normative.** Structural specification, invariants, state synchronization, and zero-privilege rules. |
| [`BRIDGE_CONTRACT.md`](./BRIDGE_CONTRACT.md) | 2 | **Normative.** WebSocket/SSE event stream protocol, event schema mapping, and Mock/Live dual-mode engine. |
| [`architecture.md`](./architecture.md) | 2 | Detailed monorepo package layout (`src_front/`), Zustand store topology, and component hierarchies. |
| [`decisions/README.md`](./decisions/README.md) | 2 | Front-End Architecture Decision Records (ADR-F series). |
| [`agile/roadmap.md`](./agile/roadmap.md) | 3 | Phased front-end roadmap (Sprint FE-01 to FE-04). |
| [`agile/sprints/sprint-fe-01.md`](./agile/sprints/sprint-fe-01.md) | 3 | Sprint FE-01 implementation backlog and acceptance criteria. |

---

## 📦 Codebase Structure (`src_front`)

All front-end source code resides in `src_front/` configured as a **pnpm / Turborepo monorepo**:

```
src_front/
├── packages/
│   ├── core/            # Shared React hooks, Zustand state stores, event stream client, domain models
│   ├── ui-components/   # Shared presentation components & themes (Tailwind CSS)
│   └── mock-server/     # Deterministic event cassette player for offline development & mock testing
├── apps/
│   ├── cli/             # TUI CLI application (React + Ink)
│   └── desktop/         # GUI Desktop application (Tauri v2 + React 19 + xyflow + Monaco)
├── pnpm-workspace.yaml
├── package.json
└── turbo.json
```

---

## ⚡ Core Invariants

* **Code Wins**: Contracts live in `src_front/packages/core/`. Documents navigate; code defines.
* **Headless Decoupling**: The front-end has zero direct imports from `src/aether/`. All communication occurs via typed events over WebSocket/SSE ([`BRIDGE_CONTRACT.md`](./BRIDGE_CONTRACT.md)).
* **Mock/Live Transparency**: Every front-end component functions identically whether consuming live engine events or mock cassette playback.
