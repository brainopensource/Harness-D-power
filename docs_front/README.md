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

## 🚀 Quickstart Guide (WSL2 / Linux / Windows)

### 1. Prerequisites
- **Node.js**: `>=20.0.0`
- **Package Manager**: `pnpm` (`>=9.0.0`)
- **WSL2 / Linux Utilities**: `webkit2gtk` & `libssl-dev` (only if compiling native Tauri desktop binaries in Linux/WSL2)

```bash
# In WSL2 / Ubuntu, install build essentials for Tauri (optional for web dev mode):
sudo apt update && sudo apt install -y build-essential curl wget file libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

---

### 2. Install Workspace Dependencies
From the repository root or `src_front/` directory:

```bash
# Navigate to front-end workspace
cd src_front

# Install all pnpm monorepo dependencies
pnpm install
```

---

### 3. Running in Development Mode (Dev Mode)

You can launch either interface immediately using **Mock Engine Mode** (no running backend required, streams recorded cassettes) or connect to a live backend engine (`ws://localhost:8080/ws`).

#### Option A: Terminal TUI CLI (`@aether/cli`)
Interactive React + Ink terminal dashboard with keyboard shortcuts (`p` to play/pause, `s` to step, `1`/`2`/`5` for speed, `c` to switch cassette):

```bash
# In WSL2 / Bash:
cd src_front
pnpm --filter @aether/cli dev

# Or using npx from root:
npx pnpm --filter @aether/cli dev
```

#### Option B: Desktop GUI Canvas (`@aether/desktop`)
Launch the React 19 + Vite web GUI locally in dev mode (opens visual node-graph canvas, trace inspector, Monaco diff editor, McNemar dashboard):

```bash
# Quick Web Dev Mode (Browser on http://localhost:1420):
cd src_front
pnpm --filter @aether/desktop dev

# Native Tauri App Shell (WSL2 with X11/WSLg or Windows CMD):
cd src_front/apps/desktop
pnpm tauri dev
```

---

### 4. Production Build Commands

#### Build TUI CLI
```bash
cd src_front
pnpm --filter @aether/cli build
# Executable output available at: src_front/apps/cli/dist/index.js
```

#### Build Desktop GUI
```bash
cd src_front
pnpm --filter @aether/desktop build
# Static bundle available at: src_front/apps/desktop/dist/

# Native Desktop App Bundle (Installer/Executable):
cd src_front/apps/desktop
pnpm tauri build
```

---

### 5. Workspace Quality & Typechecking Commands

```bash
# Run TypeScript compilation check across all packages & apps (0 errors expected):
cd src_front
pnpm --recursive run build   # or run tsc per package:
pnpm --filter @aether/core exec tsc --noEmit
pnpm --filter @aether/cli exec tsc --noEmit
pnpm --filter @aether/desktop exec tsc --noEmit

# Run unit tests:
pnpm --filter @aether/core test
```

---

## 🏗️ Navigation Index

| Document | Tier | Description |
| :--- | :---: | :--- |
| [`vision.md`](./vision.md) | 1 | Orientation, mission statement, UX principles, and altitude architecture. |
| [`spec.md`](./spec.md) | 2 | **Normative.** Structural specification, invariants, state synchronization, and zero-privilege rules. |
| [`BRIDGE_CONTRACT.md`](./BRIDGE_CONTRACT.md) | 2 | **Normative.** WebSocket/SSE event stream protocol, shared type definitions (GateStatus, Provenance, BudgetDims), event schema mapping, command registry, and mock cassette engine. |
| [`architecture.md`](./architecture.md) | 2 | Detailed monorepo package layout (`src_front/`), Zustand store topology (6 stores), DAG topology rendering specification, and component hierarchies. |
| [`decisions/README.md`](./decisions/README.md) | 2 | Front-End Architecture Decision Records (ADR-F series). |
| [`agile/roadmap.md`](./agile/roadmap.md) | 3 | Phased front-end roadmap (Sprint FE-01 to FE-04). |
| [`fixes/`](./fixes) | 3 | Audit reports, fix proposals, and status trackers for Architecture, Performance, Protocols, UI/UX, and Testing. |

---

## 📦 Codebase Structure (`src_front`)

All front-end source code resides in `src_front/` configured as a **pnpm / Turborepo monorepo**:

```
src_front/
├── packages/
│   ├── core/            # Shared React hooks, Zustand state stores, event stream client, domain models
│   ├── ui-components/   # Desktop-GUI Tailwind components & ErrorBoundary
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
* **Event Schema Validation**: Wire events are validated at the bridge boundary via Zod schemas (`@aether/core/types/events.ts`). Invalid events are dropped with diagnostic warnings.
