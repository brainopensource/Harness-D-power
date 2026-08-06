---
status: normative
updated: 2026-08-06
---

# ADR-F001: Monorepo Structure in `src_front/` with pnpm Workspaces

**Status**: Accepted · **Date**: 2026-08-06

---

## Context

The AETHER front-end requires two distinct target executables:
1. A lightweight terminal UI CLI (`apps/cli`).
2. A visual desktop application for Windows and Linux (`apps/desktop`).

Both applications must consume identical event streams, shared React hooks, state management stores, and domain model definitions. Separating them into disconnected repositories would result in code duplication, schema drift, and doubled maintenance overhead.

---

## Decision

- Create a unified front-end monorepo located at **`src_front/`** managed by **pnpm workspaces** and **Turborepo**.
- Structure packages into `@aether/core` (hooks, stores, event client), `@aether/ui-components` (Tailwind UI elements), and `@aether/mock-server` (mock cassettes).
- Separate application entry points under `src_front/apps/cli` and `src_front/apps/desktop`.

---

## Consequences

- **Pros**: 100% shared business logic, state stores, and WebSocket drivers; single `pnpm install` and build pipeline; zero schema drift between CLI and GUI.
- **Cons**: Requires managing monorepo workspace configurations (`pnpm-workspace.yaml`, `turbo.json`).
