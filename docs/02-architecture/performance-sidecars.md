---
status: rationale
updated: 2026-07-29
---
# **Native Sidecars — Deferred, and Scoped Down**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Status: Deferred**

No sidecar is built until a measured Python baseline misses a stated budget. The ports are already shaped to permit the swap, which is exactly why deferring costs nothing.

## **Reassessing the Premise**

The original rationale was that compiled services keep the Python event loop unblocked. That goal is met far more cheaply by `asyncio.to_thread` and a process pool — no gRPC, no protobuf, no cross-language toolchain. A separate compiled service is justified only when a process must **stay warm holding large in-memory state**, such as an index or a language server.

## **Rule: Draw the Boundary at the Query, Never at Parsing**

A sidecar that returns ASTs or bulk symbol tables serializes the whole structure across the process boundary and rebuilds it as Python objects — reintroducing precisely the cost the sidecar existed to avoid, plus IPC overhead. Drawn there, a sidecar is measurably *slower* than in-process parsing.

The `Indexer` port is therefore query-shaped, and the sidecar **owns** the index:

```python
async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]: ...
async def get_skeleton(self, file_path: str) -> str: ...
async def neighbors(self, symbol: Symbol, hops: int = 1) -> list[Symbol]: ...
```

Twenty results cross the boundary, never fifty thousand.

## **Decisions**

### Rust AST Indexer — deferred, plausible later

`py-tree-sitter` binds the same C library, so parsing already runs at C speed; the overhead is in materializing Python objects per node and in filesystem walking. Using the query API to avoid node materialization, plus multiprocessing across files, typically recovers most of the available gain. **Measure the Python baseline before funding a rewrite** — the ≥5× target may well be met without leaving Python, and the answer may be two days of `ProcessPoolExecutor`.

**Trigger**: measured incremental indexing misses its latency budget on the target repository after in-process optimization.

### Go Vector Sidecar — dropped

LanceDB is already Rust, embeds in-process, memory-maps, and returns zero-copy Arrow with **no IPC at all**. Qdrant already ships a production TurboQuant engine. Building `tq_vector_go` would duplicate two mature engines while adding a second language toolchain — doubling build, CI, cross-compilation, release, and debugging burden for no architectural gain. One sidecar language at most, and zero for now.

### LSP Daemon Sidecar — dropped

Language servers **are** already daemons speaking JSON-RPC over stdio. Wrapping them in another compiled service adds indirection, not speed. The real problems are entirely different, and none of them are solved by a sidecar:

* **Cold start**: 30s+ for `pyright` or `rust-analyzer` on large repositories.
* **Unsaved edits**: diagnostics must reflect in-memory state via `didChange`, not disk.
* **Server explosion under parallel search**: N worktrees × M languages, each with its own server, exhausts RAM quickly — a direct and unaddressed consequence of the System 2 design.

The answer is a **Python supervisor** holding warm servers, driven by in-memory document overlays, with a bounded pool shared across worktrees rather than one server per worktree.

## **If a Sidecar Is Eventually Built**

* **One language**, not two.
* **Transport**: start with length-prefixed msgpack or JSON-RPC over a Unix domain socket. gRPC brings protobuf schema management across languages and a threading model that fights asyncio; adopt it only when a second consumer exists.
* **Bulk data**: Arrow IPC or shared memory, never row-by-row protobuf.
* **Contract**: the existing conformance suite for `Indexer` must pass unchanged against the sidecar adapter. That is the acceptance test for the migration.
