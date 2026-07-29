# ADR-0010: Defer Exotic Components Behind Trigger Conditions

**Status**: Accepted
**Date**: 2026-07-28

## Context
The original roadmap scheduled compiled Rust/Go sidecars, TurboQuant vector quantization, Redis, Neo4j/FalkorDB, gRPC, and A2A by phase number. Several solved problems the system does not have at its actual scale: a large repository chunks to ~10⁵–10⁶ vectors, where an exhaustive SIMD scan runs in single-digit milliseconds. Meanwhile the components that determine whether a coding agent works — model port, context and cache layout, chunking, edit application, error recovery — were unspecified.

## Decision
Each advanced component carries a **trigger condition** rather than a calendar slot. Specifically: the Go vector sidecar and LSP daemon sidecar are dropped outright; the Rust AST indexer is deferred behind a measured Python baseline; quantization waits on a measured latency or memory ceiling; Redis is dropped (SQLite-WAL covers STM); graph daemons are dropped in favor of embedded storage; gRPC waits for a second consumer; A2A waits for a genuinely remote peer.

## Consequences
Effort concentrates on what moves task success. Deferral is free **because** the ports were drawn correctly — a query-shaped `Indexer` accepts a compiled sidecar later without touching a consumer. That is the entire return on the hexagonal discipline, and it only holds if ADR-0002 and ADR-0003 hold.

## Reversal Conditions
Per component, the stated trigger firing — measured, on the real workload, after in-process optimization has been attempted.
