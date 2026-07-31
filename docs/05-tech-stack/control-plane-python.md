---
status: rationale
retrieval: excluded
updated: 2026-07-29
---
# **Python Control Plane & Core Ecosystem**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Core Runtime & Ecosystem**

* **Runtime Engine**: Python >=3.13, async-first.
* **Schema Validation**: Pydantic v2 for frozen domain schemas, trajectories, and configuration.
* **Hexagonal Protocols**: `typing.Protocol`, verified by `mypy`/`pyright` in strict mode plus per-port conformance suites. **`@runtime_checkable` is not used as a correctness mechanism** — it checks method presence only, never signatures, so an adapter with wrong argument types passes it while incurring runtime cost for a guarantee it does not provide.
* **Composition**: a single explicit composition root, `build_kernel(config) -> Kernel`. See [Composition & Configuration](./composition-and-configuration.md).
* **Boundary Enforcement**: `import-linter` layer contracts in CI, enforcing that `agency/` cannot import `runtime/` or `adapters/`.

## **No DI Container, No Plugin Discovery**

Both are dropped in favor of explicit wiring, and the reasoning is specific to this system rather than general taste.

A container with runtime plugin discovery defeats static analysis: type checkers cannot see dynamically registered implementations, so "go to definition" fails and call sites become unresolvable. This codebase's **principal maintainer is an LLM navigating it through a language server** — that is the system's stated purpose. Static navigability is therefore a first-class architectural requirement, not a style preference, and the harness should be designed for the comprehension of the agent that will maintain it.

Explicit imports and one wiring function are also greppable, type-checkable, and trivially testable. Dynamic indirection buys flexibility the system does not need, at the cost of the analyzability it depends on most.

Extensions remain fully supported, and third parties do **not** need to fork the repository to ship
one. They are loaded from **declared locations** — packaging entry points written by the extender,
resolved once at composition and then frozen — rather than by scanning, which preserves exactly the
property above: the target is an ordinary module path, so the type checker resolves it and "go to
definition" works. See [Extension Model](../02-architecture/extension-model.md) and
[ADR-0013](../08-decisions/0013-extension-registration.md).

## **Storage Layout & Concurrency**

Three SQLite databases, each with a different write pattern, accessed by parallel runs across parallel
worktrees. Getting this wrong produces `database is locked` under exactly the load the architecture is
designed for — best-of-N — so the discipline is specified rather than discovered.

### Which databases exist, and where

| File | Contents | Sole writer | Rebuildable |
| :--- | :--- | :--- | :--- |
| `trajectories.db` | Append-only event log; source of truth for replay, audit, training | `TrajectoryStore` | ❌ Never |
| `codegraph.db` | Code graph + FTS5 index derived from Tree-sitter and git | `Indexer` | ✅ From HEAD |
| `memory.db` | Durable knowledge, decisions, preferences, links | `Memory` adapter | ❌ Never |

All three sit under `state_dir` (default `.sagiha/`) — see
[Configuration Reference](./configuration-reference.md).

**All three live under `.sagiha/` at the repository root — never inside a worktree.** A worktree is
ephemeral and per-candidate; a trajectory store inside one means each candidate writes a private log
that is deleted on release, and the run becomes unreplayable. This is the single most consequential
line in this section.

### WAL plus a busy timeout, as a connection-factory invariant

Every connection to every store is opened through one factory that applies:

```sql
PRAGMA journal_mode = WAL;      -- one writer, concurrent readers, set once per database
PRAGMA busy_timeout = 5000;     -- block rather than raise on transient contention
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;    -- safe under WAL; full fsync per commit is not worth the cost here
```

Stated once, here, rather than repeated per store — a pragma applied in three places is a pragma
missing from a fourth. WAL's guarantee is **one writer with concurrent readers**, and that guarantee is
the entire design constraint below.

### One writer per database

Each database has exactly one owning component, and that component is the only code that writes to it.
Writes are serialized through a single async task draining a bounded queue; every other component
reads.

This is not a new mechanism — the [EventBus](../02-architecture/event-bus-and-hooks.md) already implies
it. `TrajectoryStore` is the one observer whose queue is unbounded and whose writes are awaited,
precisely because a dropped trajectory event corrupts replay. The rule here just names the property
and extends it to the other two stores.

Consequences for parallel work:

* **Parallel worktrees are readers.** A candidate branch never writes to any of the three directly; it
  emits events, and the owning component writes. This is what keeps N-way parallelism from becoming
  N-way lock contention.
* **Cross-store transactions do not exist.** Three databases means no atomic write spanning them. Where
  ordering matters, the event log is authoritative and the others are caught up from it.
* **`busy_timeout` is a backstop, not the design.** If it is firing under normal load, a second writer
  has appeared somewhere and the fix is to remove it, not to raise the timeout.

### Rebuild over repair

`codegraph.db` is a cache derivable from HEAD, so corruption, a schema change, or a suspected
inconsistency is answered by **deleting and re-indexing** — never by a migration. Only the two
non-rebuildable stores carry schema versioning and upcasters
([Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md)).

## **Testing Stack**

* **`pytest`** with the conformance suites in `tests/contracts/` parametrized across adapters.
* **Cassette replay** at the `ModelProvider` boundary — the entire kernel runs in CI with zero API calls, which is the cheapest testability win in the design and the reason record/replay is a Day-0 deliverable rather than a later nicety.
* **Property tests** for the trajectory DAG and effect-class replay semantics.

## **Observability**

OpenTelemetry using the **GenAI semantic conventions**, so LLM call spans carry token counts, cost, and cache-hit data in a form existing tooling already understands. The Trajectory Store subscribes to the EventBus directly; it is not derived from the span log. A sampled span log must never be the source of a durable trajectory record.

## **Configuration**

Local-first `config.toml`: model endpoints, autonomy level, worktree root, MCP servers, budgets, governor limits. Validated by Pydantic at startup, so misconfiguration fails immediately and loudly rather than at the first tool dispatch.

Configuration parameterizes **policy, never structure** — it selects which adapter implements a port
and what the thresholds are, and it can never disable the dispatch choke point, the `tests_unmodified`
gate, or the gate/score distinction. The mechanism, the layering rules, and the full parametric-vs-fixed
boundary are in [Composition & Configuration](./composition-and-configuration.md).
