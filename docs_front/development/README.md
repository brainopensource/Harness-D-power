---
status: normative
updated: 2026-08-06
---

# Front-End Development Documentation (`docs_front/development/`)

> **Standing**: These are the pre-implementation engineering specifications for the AETHER Front-End Client Suite. When code lands in `src_front/`, **the code becomes the contract and these files stop being authoritative** (house rule: documents navigate, code defines).

---

## Document Index

| Document | Purpose | Standing |
| :--- | :--- | :--- |
| [Core Skeletons & Protocols](./core_skeletons_and_protocols.md) | TypeScript interface definitions, Zustand store skeletons, React hook signatures, bridge driver protocols, CLI/Desktop component trees | Rationale |
| [Schemas & Contracts](./schemas_and_contracts.md) | Zod schema definitions for all event/command payloads, store state shapes, cassette format, cross-boundary contract rules | Rationale |
| [System Workflows & Diagrams](./system_workflows_and_diagrams.md) | Mermaid diagrams: event flow pipeline, bridge state machine, store dispatch topology, component hierarchies, user interaction flows | Rationale |
| [Tech Stack & Infrastructure](./tech_stack_and_infra.md) | Dependency matrix with version pins, monorepo configuration, TypeScript setup, Tauri v2 config, testing strategy, CI/CD pipeline | Rationale |

---

## Relationship to Backend Development Docs

These documents are the front-end counterparts to `docs/development/`:

| Backend Document | Frontend Counterpart | Integration Point |
| :--- | :--- | :--- |
| `core_skeletons_and_protocols.md` | `core_skeletons_and_protocols.md` | Event types generated from `domain/events.py` |
| `schemas_and_contracts.md` | `schemas_and_contracts.md` | Bridge event envelope, `StoredEvent` ↔ `BridgeEvent` |
| `system_workflows_and_diagrams.md` | `system_workflows_and_diagrams.md` | Event bus → WebSocket/SSE → Front-end driver |
| `tech_stack_and_infra.md` | `tech_stack_and_infra.md` | CI pipeline shared stages |

---

## Cross-Reference Rules

1. **Event schema source of truth**: `domain/events.py` (backend). Front-end Zod schemas are CI-generated from this source.
2. **Bridge contract**: [`BRIDGE_CONTRACT.md`](../BRIDGE_CONTRACT.md) is the normative integration boundary.
3. **Invariants**: [`spec.md`](../spec.md) defines the binding front-end invariants (FI-1 through FI-5).
4. **Architecture**: [`architecture.md`](../architecture.md) defines the monorepo topology and store architecture.
