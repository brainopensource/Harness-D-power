---
status: normative
updated: 2026-07-31
---
# ADR-0025: `CandidateExecutor` and `CandidateScorer` Are Adapter-Internal Seams, Not Ports

**Status**: Accepted  
**Date**: 2026-07-31  

## Context

Implementing Best-of-N candidate search (`ports/search.py`, `adapters/search/best_of_n.py`) required decoupling execution mechanisms (worktree allocation, `RunLoop` execution) from search policy (pruning, repair, scoring, candidate selection). 

Because `adapters/search/` cannot import `agency` or `kernel` directly without violating import layering rules, execution must be constructed by the composition root. However, because both `CandidateExecutor` and `CandidateScorer` serve strictly within `adapters/search/`, they are internal extension points rather than global hexagonal ports.

## Decision

**`CandidateExecutor` and `CandidateScorer` live in `adapters/search/protocols.py`, not `ports/`.**

- `CandidateExecutor`: Single production implementer (`composition.KernelCandidateExecutor`) serving single consumer (`BestOfNSearch`).
- `CandidateScorer`: Three implementers (`DeterministicCompositeScorer`, `NullScorer`, `LocalJudgeScorer`) selected by `scoring.build_scorer` exclusively for `BestOfNSearch`.

### Scoring Ladder Promotion Conditions

| Backend | Status | Promotion Trigger |
| :--- | :--- | :--- |
| `composite` (S-0) | Default, always on | Baseline floor. |
| `null` | Available, off by default | Enabled via `scoring.enabled=false` profiles. |
| `judge` (S-2) | Implemented, ships off | E0 ablation demonstrates judge scoring beats composite scoring beyond A/A floor. |
| `learned` (S-1) | `NotImplementedError` | ~50–100 labeled runs accumulate in `TrajectoryStore` (cold-start rule per [ADR-0005](./0005-best-of-n-not-mcts.md)). |

`BestOfNSearch.select()` filters to admitted candidates before consulting scorers. Falls back to full pool only if no candidates are admitted, recording basis in `CandidateSelected.selection_basis`.

## Consequences

- **Easy**: Internal search strategy additions or updates require no `ports/` version bumps or `test_port_shape.py` changes.
- **Foreclosed**: Direct external module dependencies on search internal protocols.
- **Risk Accepted**: Promoted to `ports/` via file relocation if external consumers emerge.

## Reversal Conditions

A second external production consumer of `CandidateExecutor` or `CandidateScorer` emerges outside `sagiha.adapters.search` (e.g., Story-DAG execution or Conductor-level search).

## Related

[ADR-0005](./0005-best-of-n-not-mcts.md) · [ADR-0019](./0019-port-consolidation.md) · [ADR-0023](./0023-port-rent-rule.md) · [ADR-0024](./0024-e0-is-a-tool-not-a-port.md)
