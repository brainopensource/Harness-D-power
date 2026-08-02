---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Extension Model**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Registration Model**

Extensions use Python entry points declared in `pyproject.toml`. Resolved once at composition and frozen for the run manifest, preserving static analysis per [ADR-0013](../08-decisions/0013-extension-registration.md) (amending [ADR-0004](../08-decisions/0004-no-di-container.md)):

```toml
[project.entry-points."sagiha.adapters"]
qdrant_indexer = "myorg_sagiha_qdrant:QdrantIndexer"

[project.entry-points."sagiha.tools"]
jira = "myorg_sagiha_jira:jira_tool"

[project.entry-points."sagiha.skills"]
django_orm = "myorg_sagiha_django:skill"
```

Operators retain override control via configuration:
```toml
[extensions]
enabled  = ["qdrant_indexer", "jira"]
disabled = ["django_orm"]
```

## **The Four Extension Surfaces**

Extension is **additive within the hexagon** and cannot widen authority or introduce new ports.

| Surface | Description | Entry Point Group | Constraint |
| :--- | :--- | :--- | :--- |
| **Adapter** | Port implementation | `sagiha.adapters` | Must pass `sagiha conformance --port ...` suite unchanged. |
| **Tool** | Registry capability | `sagiha.tools` | Declares `EffectClass` and grant; policy-gated at dispatch choke point. |
| **Skill** | Instructions & tool bundles | `sagiha.skills` | Defaults to `EXTERNAL` provenance; progressively disclosed. |
| **Hook** | EventBus subscriber | `config.toml` | Observers cannot alter run; interceptors may only deny. |

### Skill Architecture

Skills package versioned instructions and references:

```
myorg_sagiha_django/
├── skill.toml          # Metadata, triggers, required tools
├── SKILL.md            # Primary instruction body
└── references/         # On-demand reference materials
```

* **Progressive Disclosure**: Descriptors (`name`, `trigger`, `description`) sit in the stable prompt prefix (~30 tokens). Full `SKILL.md` loads into Layer 5 of [Prompt Architecture](./prompt-architecture.md) only on trigger match.
* **Trust Boundary**: Skill content is marked `EXTERNAL` provenance by default and cannot bypass policy or gates.

## **Extension Invariants**

| Forbidden Action | Rationale |
| :--- | :--- |
| **Define new ports** | Ports define the system boundaries; custom ports split conformance. |
| **Reach past port boundaries** | Extensions must operate strictly through established hexagonal interfaces. |
| **Mint capability grants** | Only `PolicyEngine` mints grants, managed strictly within `kernel/dispatch.py`. |
| **Modify TCB** | Policy engine, evaluators, and benchmark specs remain protected ([ADR-0007](../08-decisions/0007-trusted-computing-base.md)). |
| **Runtime registration** | Registrations are immutable after composition for trajectory replay reproducibility. |

## **Versioning**

Extensions specify supported major port contract versions, checked at startup. See [Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md).
