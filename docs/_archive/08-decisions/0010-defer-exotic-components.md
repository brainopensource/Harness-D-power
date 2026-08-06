---
status: historical
updated: 2026-07-29
---
# ADR-0010: Defer Exotic Components Behind Trigger Conditions

**Status**: Accepted  
**Date**: 2026-07-28

## Context
Premature infrastructure (Rust/Go sidecars, vector quantization, Redis, graph DBs, gRPC, A2A) addresses scale issues far beyond initial repository bounds (~10⁵–10⁶ vectors perform SIMD scans in <10ms).

## Decision
Defer complex infrastructure until empirical triggers fire:
- **Dropped**: Go vector/LSP sidecars, Redis (replaced by SQLite-WAL), dedicated graph daemons (replaced by embedded storage).
- **Deferred behind triggers**: Rust AST indexer (Python baseline check), Vector Quantization (latency/memory thresholds), gRPC (multi-consumer need), A2A (remote peer need).

## Consequences
- Focuses initial effort on core agent capabilities (context windows, prompt layout, tool execution).
- Port interfaces isolate components for deferred adoption without breaking callers.

## Reversal Conditions
- Empirical benchmark measurements demonstrating bottleneck limits under real workloads.
