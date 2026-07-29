---
status: normative
updated: 2026-07-29
---

# **Sidecar Development**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Status: No Sidecar Is Currently Planned**

The Go vector sidecar and the LSP daemon sidecar are **dropped**; the Rust AST indexer is **deferred** behind a measurement. See [Performance Sidecars](../02-architecture/performance-sidecars.md) for the reasoning. This guide exists for the day a trigger fires.

## **Before You Build One**

Answer these in order. A "no" anywhere means do not build it.

1. **Have you measured the Python baseline?** Not estimated — measured, on the real repository, with a profiler. `py-tree-sitter` binds the same C library the Rust crate does, so the overhead is usually Python object materialization and filesystem walking rather than parsing.
2. **Have you tried the in-process fixes?** `asyncio.to_thread`, a process pool, the Tree-sitter query API to avoid materializing nodes, and incremental re-index. These typically recover most of the available gain for days of work rather than months.
3. **Does a warm in-memory state actually justify a process?** That is the only durable reason. "Not blocking the event loop" is not — a thread solves it.
4. **Does an existing engine already do this?** LanceDB and Qdrant both do, for the vector case. Duplicating mature infrastructure is the most expensive way to fail.

## **If You Proceed**

### Draw the boundary at the query

The sidecar **owns** the index and answers queries. It must never return ASTs or bulk symbol tables — serializing the whole structure across the boundary and rebuilding it as Python objects reintroduces exactly the cost the sidecar existed to avoid, plus IPC. Drawn wrongly, a sidecar is measurably slower than in-process work.

Twenty results cross the boundary, never fifty thousand.

### One language

Not two. Each additional toolchain multiplies build, CI, cross-compilation, release, and debugging burden — a cost paid forever by a small team, in exchange for a one-time performance win.

### Start with the simplest transport

Length-prefixed msgpack or JSON-RPC over a Unix domain socket. gRPC brings protobuf schema management across languages and a threading model that fights asyncio; adopt it when a second consumer exists. For bulk data, Arrow IPC or shared memory — never row-by-row protobuf.

### Lifecycle is your problem now

Startup ordering, health checks, crash recovery, version skew between the Python client and the compiled binary, and clean shutdown. The adapter owns all of it, and must degrade to a typed error rather than hanging the agent loop when the sidecar is down.

## **The Acceptance Test**

**The existing conformance suite for the port must pass unchanged against the sidecar adapter.** No new tests, no relaxed assertions, no special-casing. If it does not pass unchanged, either the sidecar is wrong or the port was never abstract enough to permit the swap — and both are worth discovering before the migration lands rather than after.
