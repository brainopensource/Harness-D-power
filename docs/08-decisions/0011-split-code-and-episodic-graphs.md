---
status: normative
updated: 2026-07-29
---
# ADR-0011: Split the Code Graph from Episodic Memory

**Status**: Accepted
**Date**: 2026-07-28

## Context
The design routed both structural code facts and learned experience through a single bi-temporal graph engine performing LLM-based entity extraction on ingest. Code structure — imports, call edges, definitions, inheritance, ownership, co-change — is exactly derivable from Tree-sitter and git. Passing it through LLM extraction pays tokens and latency for facts a parser already knows with certainty, and admits hallucinated edges into a dependency graph that impact analysis then trusts.

## Decision
Two stores with different epistemics. The **deterministic code graph** is built directly by the indexer into SQLite (embedded Kùzu if recursive traversal outgrows SQL), is exact, and is fully rebuildable from HEAD — a cache, not a system of record. **Episodic and decision memory** — ADRs, PR rationale, "we tried X and it failed because Y" — is where facts are genuinely unstructured and lose validity over time, and is where bi-temporal modelling and LLM extraction earn their cost.

Note that git is already bi-temporal for code: valid time is commit time, transaction time is index time, and structure re-derives at any ref. Rebuilding that inside a graph database duplicates version control.

## Consequences
Impact analysis is exact and cheap. Temporal invalidation applies only where it pays. Two stores to maintain instead of one, with a clear rule for which receives a given fact.

## Reversal Conditions
Evidence that unified storage materially improves retrieval quality on the labelled query set, at acceptable ingest cost.
