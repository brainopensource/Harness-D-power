---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Native Sidecars — Deferred and Scoped**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Status: Deferred**

Sidecars are deferred until measured Python baselines (`asyncio.to_thread`, `ProcessPoolExecutor`) fail to meet performance budgets.

## **Boundary Principle: Query-Level Boundaries**

Cross-process IPC serializing whole ASTs is slower than in-process execution. Sidecars must **own** state and expose high-level query APIs on the `Indexer` port:

```python
async def find_symbols(self, query: str, limit: int = 20) -> list[Symbol]: ...
async def get_skeleton(self, file_path: str) -> str: ...
async def neighbors(self, symbol: Symbol, hops: int = 1) -> list[Symbol]: ...
```

## **Component Evaluation**

* **Rust AST Indexer (Deferred)**: `py-tree-sitter` already parses at C speed. Optimize via process pools before considering a external Rust binary.
* **Go Vector Sidecar (Dropped)**: LanceDB (Rust/Arrow) embeds in-process with zero IPC overhead. Avoid adding Go toolchain complexity.
* **LSP Daemon Sidecar (Dropped)**: Language servers are already stdio JSON-RPC daemons. Optimization uses a **Python supervisor** holding warm server instances with document overlay buffers.

## **Sidecar Implementation Criteria**

If a sidecar becomes strictly required by performance metrics:
1. Max **one** extra language ecosystem.
2. **IPC Transport**: Length-prefixed msgpack or JSON-RPC over Unix domain sockets (or Arrow IPC for bulk data).
3. **Contract Conformance**: Must pass the existing `Indexer` port conformance test suite unchanged.
