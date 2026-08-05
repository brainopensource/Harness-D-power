---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Sidecar Development**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Status: No Sidecar Is Currently Planned**

Go vector and LSP daemon sidecars are dropped; the Rust AST indexer is deferred pending performance measurements. See [Performance Sidecars](../02-architecture/performance-sidecars.md).

## **Prerequisite Decision Checklist**

Before building a sidecar, verify these conditions in order:

1. **Python Baseline Measured**: Profile performance on realistic repositories. (`py-tree-sitter` uses the C library; overhead is often object materialization/file I/O).
2. **In-Process Optimizations Exhausted**: Evaluate `asyncio.to_thread`, process pools, Tree-sitter query APIs (avoiding full AST materialization), and incremental re-indexing.
3. **Warm In-Memory State Required**: A separate process is justified only if persistent warm in-memory state is essential. Non-blocking requirements are handled via worker threads.
4. **No Standard Off-The-Shelf Alternative**: Avoid building custom vector infrastructure when mature solutions (LanceDB, Qdrant) exist.

## **Architecture & Implementation Guidelines**

* **Query-Level Boundaries**: The sidecar owns the index and executes queries. Return small query result sets (e.g., ≤20 items), never raw ASTs or full symbol tables that require expensive cross-IPC deserialization.
* **Single Secondary Toolchain**: Avoid maintaining multiple non-Python compiled languages to limit build, CI, and cross-compilation overhead.
* **Simple Transports**: Use length-prefixed msgpack or JSON-RPC over Unix domain sockets (or Arrow IPC / shared memory for bulk data). Reserve gRPC/protobuf for multi-consumer scenarios.
* **Lifecycle Ownership**: The Python adapter manages process startup, health checks, version compatibility, crash recovery, and shutdown, raising typed errors if the sidecar fails.

## **Acceptance Criterion**

The port's existing conformance suite must pass **unchanged** against the sidecar adapter without special-casing or modified assertions.
