---
status: historical
updated: 2026-07-29
---
# ADR-0012: Determinism Means Record/Replay

**Status**: Accepted  
**Date**: 2026-07-28

## Context
LLM generation is inherently non-deterministic. Expecting zero-variance reproducible generation misdirects testing strategies.

## Decision
- Guarantee **record/replay determinism**.
- Record model calls and tool responses; replay re-uses recorded responses.
- Tool classifications (`PURE`, `IDEMPOTENT`, `DESTRUCTIVE`); replay only executes `PURE` tool calls.
- Cassette adapter for `ModelProvider` enables zero-API CI validation (`sagiha replay --verify-all`).

> **Implementation note (2026-07-30)**: Cassette adapter stubbed; full replay verification targeted for Sprint 3. See [STATUS.md](../STATUS.md).

## Consequences
- Enables offline unit testing and time-travel debugging.
- Prevents accidental re-execution of side-effects during replay.

## Reversal Conditions
- None (reproducible generation is LLM-impossible).
