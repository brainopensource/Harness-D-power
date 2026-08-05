---
status: historical
updated: 2026-07-31
---
# ADR-0024: `e0/` Is a Tool, Not a Port — Delete `ports/benchmark.py`

**Status**: Accepted  
**Date**: 2026-07-31  

## Context

Two parallel evaluation harness implementations existed: `src/sagiha/e0/` (CLI-wired, functional) and `src/sagiha/adapters/benchmark/` (unbacked stub protocols in `ports/benchmark.py`).

Because `e0/runner.py` must import `sagiha.agency` and `sagiha.composition` to drive benchmark execution, housing `e0/` inside `adapters/benchmark/` violates `.importlinter` layering contracts (`sagiha.agency > sagiha.kernel > sagiha.adapters > sagiha.ports > sagiha.domain`). An adapter cannot import higher-level agency and composition modules.

## Decision

**Delete `src/sagiha/adapters/benchmark/` and `src/sagiha/ports/benchmark.py`.**

`e0/` becomes the single implementation, maintaining an internal seam (`src/sagiha/e0/protocols.py`: `TaskHarvester`, `SuiteRunner`, `StatisticalTest`). This provides extensible internal abstractions without misclassifying tooling as a hexagonal port.

Port count reduces: 19 → 17 Protocols (`CommitReplayHarvester` and `TaskRunner` removed).

## Consequences

- **Easy**: Consolidates evaluation codebase to a single CLI-backed pipeline.
- **Foreclosed**: Implementing benchmark runners under `adapters/benchmark/` (prevented by layer import rules).
- **Risk Accepted**: `e0/protocols.py` is excluded from port-rent tracking ([ADR-0023](./0023-port-rent-rule.md)) as it is an internal tool seam, not a port.

## Reversal Conditions

Re-promote `e0/protocols.py` to `ports/` per [ADR-0019](./0019-port-consolidation.md) only if a alternative harvester/runner backend is created that does not require importing `sagiha.agency`/`sagiha.composition`.

## Related

[ADR-0019](./0019-port-consolidation.md) · [ADR-0023](./0023-port-rent-rule.md) · [`refactor_sagiha_v2_guidelines.md` §11 Q3](../implementation/refactor_sagiha_v2_guidelines.md#11-open-questions-for-the-tech-lead)
