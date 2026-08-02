---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Python Control Plane & Core Ecosystem**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

## **Core Runtime & Ecosystem**

* **Runtime Engine**: Python $\ge$3.13, async-first.
* **Schema Validation**: Pydantic v2 for frozen domain models, trajectories, and configs.
* **Hexagonal Protocols**: `typing.Protocol` with strict `mypy`/`pyright` validation. Avoids runtime `@runtime_checkable` due to type-signature overhead.
* **Composition Root**: `build_kernel(config) -> Kernel` (see [Composition & Configuration](./composition-and-configuration.md)).
* **Boundary Enforcement**: `import-linter` layer checks enforce `agency/` isolation from `runtime/` and `adapters/`.

## **Explicit Composition over DI Containers**

Dependency injection containers and dynamic plugin reflection are prohibited:
* Preserves static type-checker navigability ("go to definition"), enabling LLM code analysis.
* Packaging entry points resolve external extensions predictably without dynamic scanning ([Extension Model](../02-architecture/extension-model.md), [ADR-0013](../08-decisions/0013-extension-registration.md)).

## **Storage Layout & Concurrency**

Databases reside under `.sagiha/` at the **repository root** (never inside ephemeral candidate worktrees):

| File | Contents | Sole Writer | Rebuildable |
| :--- | :--- | :--- | :--- |
| `trajectories.db` | Append-only event log; source of truth for replay & training | `TrajectoryStore` | ❌ Never |
| `codegraph.db` | Code graph & FTS5 index (Tree-sitter + git) | `Indexer` | ✅ From HEAD |
| `memory.db` | Durable knowledge, decisions, and preferences | `Memory` adapter | ❌ Never |

* Configured via `state_dir` (see [Configuration Reference](./configuration-reference.md)).

### SQLite Connection Invariants

All connections enforce WAL mode and busy timeouts:

```sql
PRAGMA journal_mode = WAL;      -- Single writer, concurrent readers
PRAGMA busy_timeout = 5000;     -- Block on transient locks
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
```

### Write Serialization & Concurrency

* **Single Writer Architecture**: Serializes store writes through a single async queue to eliminate lock contention during N-way worktree execution ([EventBus](../02-architecture/event-bus-and-hooks.md)).
* **Parallel Worktrees**: Function purely as readers emitting events; they do not write to SQLite directly.
* **Cache Rebuilding**: `codegraph.db` is treated as a rebuildable cache; schema updates trigger full re-indexing rather than migrations ([Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md)).

## **Testing Stack**

* **pytest**: Runs contract suites (`tests/contracts/`) across adapters.
* **Cassette Replay**: `ModelProvider` cassette record/replay enables full offline CI execution without API calls.
* **Property Tests**: Verifies trajectory DAGs and effect-class replay semantics.

## **Observability & Configuration**

* OpenTelemetry with GenAI semantic conventions tracks token consumption, cost, and cache performance.
* Local `config.toml` validated by Pydantic at startup. Config parameterizes policy options without mutating structural safety boundaries ([Composition & Configuration](./composition-and-configuration.md)).
