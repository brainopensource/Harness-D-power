---
status: normative
updated: 2026-07-29
---
# ADR-0011: Split the Code Graph from Episodic Memory

**Status**: Accepted  
**Date**: 2026-07-28

## Context
LLM entity extraction on code structure introduces hallucinations, latency, and token cost for facts already known deterministically via ASTs and Git.

## Decision
Maintain two distinct storage models:
1. **Deterministic Code Graph**: Built directly via Tree-sitter into SQLite (or Kùzu). Exact, rebuildable from HEAD (acting as a cache).
2. **Episodic & Decision Memory**: Semi-structured history (ADRs, PR rationale, failure cases) using LLM extraction and bi-temporal models.

## Consequences
- Code impact analysis is fast, exact, and zero-token cost.
- Temporal invalidation and LLM extraction apply strictly to unstructured memory.

## Reversal Conditions
- Unified graph storage demonstrating superior retrieval precision/recall at acceptable ingestion costs.
