---
status: normative
updated: 2026-08-06
---

# Front-End Architecture Decision Records (ADR-F Log)

This directory records binding architectural decisions for the AETHER Front-End Client Suite.

---

## Log

| ADR | Title | Status | Scope |
| :--- | :--- | :---: | :--- |
| [0001](./0001-monorepo-src-front-structure.md) | Monorepo Structure in `src_front/` with pnpm Workspaces | Accepted | Infrastructure |
| [0002](./0002-react-ink-tui-cli.md) | React 19 + Ink Choice for TUI CLI Client | Accepted | `apps/cli` |
| [0003](./0003-tauri-v2-react-xyflow-gui.md) | Tauri v2 + React 19 + `xyflow` Choice for Desktop GUI | Accepted | `apps/desktop` |
| [0004](./0004-mock-live-dual-mode-bridge.md) | Deterministic Mock Cassette Engine for Parallel Frontend Development | Accepted | `packages/mock-server` |
