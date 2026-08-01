---
status: normative
updated: 2026-07-31
---
# ADR-0024: `e0/` Is a Tool, Not a Port — Delete `ports/benchmark.py`

**Status**: Accepted
**Date**: 2026-07-31

## Context

Two parallel implementations of the E0 evaluation harness existed side by side:

* `src/sagiha/e0/` — real, CLI-wired (`sagiha harvest`, `sagiha bench`). `Harvester` walks git
  history and validates fix-commits; `BenchmarkRunner` drives a real `Kernel` and `RunLoop` per
  task; `StatisticalAnalyzer` computes pass rates and noise floors.
* `src/sagiha/adapters/benchmark/` — the declared hexagonal adapter behind `ports/benchmark.py`'s
  `CommitReplayHarvester`/`TaskRunner` Protocols. `GitCommitHarvester.harvest()` returned `[]`
  unconditionally; `validate_task()` returned `False` unconditionally; `LocalTaskRunner.run_task()`
  returned a `BenchmarkResult(error="Not implemented — awaiting senior implementation")`. All three
  are H3-class stubs (success-shaped literals for unimplemented work) that PR-1.4 missed because
  `test_block5_scaffolding.py` never looked at this package.

`refactor_sagiha_v2_guidelines.md` §11 Q3 posed this as an open question: delete the stubs and drop
the port, or make `e0/` the adapter behind it?

**The question has a structural answer, not a preference-based one.** `e0/runner.py` constructs a
`Kernel` via `sagiha.composition.build_kernel` and drives it with `sagiha.agency.run_loop.RunLoop` —
it has to, because running an agent against a harvested task *is* running the coding loop. The
`.importlinter` `layers` contract orders `sagiha.agency > sagiha.kernel > sagiha.adapters > sagiha.ports > sagiha.domain`,
and `car-layering` separately forbids `sagiha.agency` from reaching `sagiha.adapters`. An adapter
under `sagiha.adapters.benchmark` importing `sagiha.agency` and `sagiha.composition` violates both
directions of that boundary simultaneously. There is no legal way for `e0/`'s behavior to live in
`adapters/` and satisfy `ports/benchmark.py` — the port's only possible real adapter cannot exist
under the architecture's own layering rule. The two-implementations state was not indecision; it
was one implementation that works and one that structurally cannot.

## Decision

**Delete `src/sagiha/adapters/benchmark/` and `src/sagiha/ports/benchmark.py`.** `e0/` becomes the
sole implementation, with an internal seam (`src/sagiha/e0/protocols.py`: `TaskHarvester`,
`SuiteRunner`, `StatisticalTest`) for future swap-in — the same treatment
`agency/context/compactor.py`'s `ExchangeCompactor` already gets: a Protocol that is a real
extension point without being a hexagonal port, because its consumers all live above the layer a
port's adapters are required to sit at.

Port count: 19 → 17 (per ADR-0019's restated count; `CommitReplayHarvester` and `TaskRunner` are the
two Protocols removed).

## Consequences

**Easy.** One implementation to read, one to test, one CLI surface. The duplication `STATUS.md` has
flagged since v2-S1 closes without a migration — nothing in `src/` imported the stub adapters or the
port (grep-verified before deletion).

**Foreclosed.** A future contributor cannot "properly" implement `CommitReplayHarvester` behind
`adapters/benchmark/`, because the constraint that forbade it (`e0/` needing `agency`) does not go
away. If E0 ever needs a genuinely swappable harvester — e.g. a SWE-bench-backed one alongside the
commit-replay one — the swap point is `e0/protocols.py`, at the layer where the dependency is legal.

**Risk accepted.** Port-rent bookkeeping (ADR-0023) has one fewer subject to track. `e0/protocols.py`
is not subject to the port-rent rule — it was never a port.

## Reversal Conditions

A second, materially different `TaskHarvester`/`SuiteRunner` implementation is written (e.g. a
distributed runner, or a harvester over a different benchmark corpus) **and** it does not itself
need to import `sagiha.agency`/`sagiha.composition`. In that case, promoting the seam in
`e0/protocols.py` to a real `ports/` Protocol is a one-file move with no import-graph conflict —
exactly the promotion path ADR-0019 already establishes for deleted ports.

## Related

[ADR-0019](./0019-port-consolidation.md) (port consolidation and the re-promotion pattern) ·
[ADR-0023](./0023-port-rent-rule.md) (why an unbacked port is not free) ·
[`refactor_sagiha_v2_guidelines.md` §11 Q3](../implementation/refactor_sagiha_v2_guidelines.md#11-open-questions-for-the-tech-lead)
