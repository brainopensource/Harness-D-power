# ADR-0003: Conformance Suites, Not `@runtime_checkable`

**Status**: Accepted
**Date**: 2026-07-28

## Context
The suite asserted a "Contract Guarantee" — that any adapter can be replaced without touching consumers — across 24 documents that never specified an enforcement mechanism. `@runtime_checkable` was applied to every Protocol, which checks method *presence* only and never signatures: an adapter whose method takes entirely different arguments passes `isinstance`. That is worse than no check, because it looks like verification.

## Decision
Verification is static (`pyright` strict, blocking) plus a behavioral conformance suite per port in `tests/contracts/`, parametrized over every adapter, run in CI as a matrix. `@runtime_checkable` is not used as a correctness mechanism. An adapter absent from the suite is unsupported.

## Consequences
The migration matrix becomes safe to execute — a new backend ships when the existing suite passes unchanged. Writing an adapter costs more up front. High-risk migrations still need shadow reads and retrieval metrics on top, since two adapters can satisfy a contract while ranking differently.

## Reversal Conditions
None foreseen. Removing this would make every swappability claim in the suite unfalsifiable.
