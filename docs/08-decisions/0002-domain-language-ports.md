---
status: normative
updated: 2026-07-29
---
# ADR-0002: Ports Speak Domain Language

**Status**: Accepted  
**Date**: 2026-07-28

## Context
Storage-shaped port interfaces (e.g., `store_vector`, `search_similar`) leaked database details into the core, forcing core dependency on embedding models and blocking non-vector storage adapters (e.g., temporal graphs).

## Decision
- Ports use domain concepts (`Memory` methods: `remember`, `recall`, `invalidate`).
- Embeddings reside inside adapters behind `EmbeddingProvider`.
- All cross-port payloads are Pydantic models (no raw `dict[str, Any]`).
- Timestamps are timezone-aware UTC.

## Consequences
- Adapters are modular and swappable without core changes.
- Complexity shifts into adapters (embedding, retries, schema migration).

## Reversal Conditions
- Measured performance cost of domain-shaped interfaces that adapter-side optimizations cannot resolve.
