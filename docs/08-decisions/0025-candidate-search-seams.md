---
status: normative
updated: 2026-07-31
---
# ADR-0025: `CandidateExecutor` and `CandidateScorer` Are Adapter-Internal Seams, Not Ports

**Status**: Accepted
**Date**: 2026-07-31

## Context

`CandidateSearch` v2 (`ports/search.py`) needed a Best-of-N implementation
(`adapters/search/best_of_n.py`, v2-S4 Epic S4.2). Building it required decomposing two concerns
that the previous `SequentialCandidateSearch` stub conflated:

* **Mechanism** — allocate a worktree, drive a `RunLoop` against it, tear down. This has to be
  built by the composition root, because it needs `build_kernel` and a concrete `RunLoop`, and the
  `layers`/`car-layering` import contracts forbid `sagiha.adapters` from reaching
  `sagiha.agency`/`sagiha.kernel` (nor could `adapters/search/` import `sagiha.composition` without
  a literal circular import — composition constructs the search adapter).
* **Policy** — how many candidates, when to prune, when to repair, how to rank, which one wins.
  This has to stay swappable independent of the mechanism, so the sequential and parallel launch
  strategies (S4.2b/S4.2c) can share one policy implementation.

The same split recurs for scoring: `DeterministicCompositeScorer`, `NullScorer`, and
`LocalJudgeScorer` are three interchangeable ranking strategies consumed by exactly one family of
caller (`CandidateSearch` adapters), never by anything outside `adapters/search/`.

The question this ADR answers: do `CandidateExecutor` and `CandidateScorer` become hexagonal ports
in `ports/`, or adapter-internal Protocols? The tree already has a precedent —
`agency/context/compactor.py`'s `ExchangeCompactor` is explicitly "an agency-internal protocol, not
a hexagonal port" — and the same reasoning applies here, for the same reason ADR-0024 gave `e0/`
its own `protocols.py` instead of a `ports/benchmark.py`: **a Protocol earns port status by having
consumers outside the package that defines it, not by being swappable in the abstract.**

## Decision

**`CandidateExecutor` and `CandidateScorer` live in `adapters/search/protocols.py`, not
`ports/`.** Neither is consumed by anything outside `sagiha.adapters.search`:

* `CandidateExecutor` has exactly one production implementer (`composition.KernelCandidateExecutor`)
  and exactly one consumer (`BestOfNSearch`). A hexagonal port's value is letting multiple adapters
  satisfy one contract for multiple external consumers; here there is one contract shape serving one
  internal seam.
* `CandidateScorer` has three implementers (`DeterministicCompositeScorer`, `NullScorer`,
  `LocalJudgeScorer`) but all three are selected by one function (`scoring.build_scorer`) for one
  consumer (`BestOfNSearch`). The port machinery (`PORT_VERSION`, `STABILITY`, `test_port_shape.py`'s
  dynamic discovery, the versioning policy in `port-stability-and-versioning.md`) buys nothing here
  that a plain Protocol does not already provide, and ADR-0023's port-rent rule would flag both as
  under-adapted the moment their adapter count is compared against a port's expectations rather than
  a package-internal seam's.

**The scoring ladder's promotion conditions** (`docs/implementation/sprint_v2_s4_options.md` §3):

| Backend | Status | Promotes to default when |
| :--- | :--- | :--- |
| `composite` (S-0) | Default, always on | — (the floor every other backend is measured against) |
| `null` | Available, off by default | Never a default; exists for `scoring.enabled=false` profiles |
| `judge` (S-2) | Implemented, **ships off** | An E0 ablation shows judge-scored selection beating composite-scored selection beyond the A/A floor, at the judge role's added latency/cost |
| `learned` (S-1) | `NotImplementedError` | ~50–100 labelled runs accumulate in the `TrajectoryStore` (the cold-start doctrine ADR-0005 already established for tree search applies identically here — hand-written scoring first, learned scoring once labels exist) |

Rank-never-admit is enforced structurally, not by convention: `BestOfNSearch.select()` filters to
the admitted subset before any scorer is consulted, and only falls back to the full candidate pool
when nothing admitted — recorded in `CandidateSelected.selection_basis` so the decision is visible,
not just the winner.

## Consequences

**Easy.** Adding a fourth scoring backend, or changing `CandidateExecutor`'s mechanism entirely
(e.g. a container-sandboxed executor in v2-S5), touches one file each and no port version bump, no
`test_port_shape.py` churn, no `PORT_VERSION` migration note.

**Foreclosed.** Nothing outside `adapters/search/` may depend on `CandidateExecutor` or
`CandidateScorer` directly — a hypothetical future consumer (e.g. v2-S7's Story-DAG wanting its own
executor abstraction) needs its own seam, or a case for promoting these to `ports/` on the same
re-promotion logic ADR-0019/ADR-0024 already established.

**Risk accepted.** If a second, genuinely external consumer of either Protocol appears, the
promotion is a file move (`adapters/search/protocols.py` → `ports/`) plus a `PORT_VERSION` label —
cheap, and exactly the path ADR-0019 and ADR-0024 already normalized.

## Reversal Conditions

A second production consumer of `CandidateExecutor` or `CandidateScorer` appears outside
`sagiha.adapters.search` (e.g. a Story-DAG `CodingStep` wanting to run candidates directly, or a
Conductor-level executor abstraction, per `docs/rationale/reviews/agi_evolution_path.md`). At that
point the Protocol is promoted to `ports/` following ADR-0019's pattern, with a recorded
`PORT_VERSION` and a migration note.

## Related

[ADR-0005](./0005-best-of-n-not-mcts.md) (Best-of-N, cold-start doctrine for learned routing) ·
[ADR-0019](./0019-port-consolidation.md) (the promotion/demotion pattern this ADR reuses) ·
[ADR-0023](./0023-port-rent-rule.md) (why an unbacked port is not free) ·
[ADR-0024](./0024-e0-is-a-tool-not-a-port.md) (the identical reasoning applied to `e0/`) ·
`docs/implementation/sprint_v2_s4_options.md` §2.1, §3 (the scoring ladder and its MVP scope)
