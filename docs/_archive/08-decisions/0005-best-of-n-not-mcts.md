---
status: normative
updated: 2026-07-29
---
# ADR-0005: System 2 Is Best-of-N, Not MCTS

**Status**: Accepted  
**Date**: 2026-07-28

## Context
MCTS requires cheap rollouts and backpropagation. Full agent rollouts + test evaluations are expensive (~30 leaf evaluations per depth-3 tree). Previous interfaces (`explore_branches`, `evaluate_branch`) actually implemented depth-1 best-of-N.

## Decision
- System 2 implements verifier-guided **best-of-N with sequential repair** behind a `CandidateSearch` port.
- MCTS deferred until a calibrated Process Reward Model (PRM) exists.

## Consequences
- Optimizes cost/performance yield for high-cost rollouts.
- Maintains a clean port seam for future tree search algorithms.

## Reversal Conditions
- Availability of a calibrated PRM (validated AUC) **and** benchmark proof that MCTS outperforms best-of-N at equal cost.
