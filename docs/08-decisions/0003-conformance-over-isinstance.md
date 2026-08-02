---
status: normative
updated: 2026-07-29
---
# ADR-0003: Conformance Suites, Not `@runtime_checkable`

**Status**: Accepted  
**Date**: 2026-07-28

## Context
`@runtime_checkable` Protocols only verify method presence, not signatures, creating false confidence in adapter compatibility.

## Decision
- Verification via static typing (`pyright` strict, blocking CI).
- Behavioral contract testing via parametrized conformance suites in `tests/contracts/`.
- `@runtime_checkable` is prohibited for correctness guarantees. Unchecked adapters are unsupported.

## Consequences
- Adapter replacements are safely verifiable in CI.
- Increased initial implementation effort per adapter.

## Reversal Conditions
- None (removing conformance checks invalidates contract guarantees).
