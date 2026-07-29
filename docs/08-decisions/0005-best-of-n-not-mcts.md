---
status: normative
updated: 2026-07-29
---

# ADR-0005: System 2 Is Best-of-N, Not MCTS

**Status**: Accepted
**Date**: 2026-07-28

## Context
The design called System 2 "Monte Carlo Tree Search," but the port exposed `explore_branches(prompt, candidates_count)` and `evaluate_branch(path) -> float` — no persistent tree, no visit counts, no UCT selection, no backpropagation. That is best-of-N at depth one. MCTS also assumes cheap rollouts, while one expansion here costs a full agent run plus a test suite: branching factor 3 at depth 3 is roughly thirty leaf evaluations, in minutes and dollars.

## Decision
System 2 is verifier-guided **best-of-N with sequential repair**, named accordingly, behind a `CandidateSearch` port. Tree search with backpropagation is gated on a calibrated value model — making the PRM a hard prerequisite rather than a peer deliverable.

## Consequences
Honest naming prevents building machinery the system cannot yet afford. Best-of-N plus repair has the better yield per dollar at this cost profile. The port is shaped so real tree search can slot in later without changing consumers.

## Reversal Conditions
A calibrated PRM exists (demonstrated AUC on held-out trajectories) **and** an ablation shows tree search beating best-of-N by more than the measured A/A noise floor at equal cost.
