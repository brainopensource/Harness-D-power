---
status: normative
updated: 2026-07-29
---
# ADR-0012: Determinism Means Record/Replay

**Status**: Accepted
**Date**: 2026-07-28

## Context
The microkernel was described as offering "deterministic execution... strictly reproducible." That is false for any LLM-driven system: generation is non-deterministic even at temperature zero, and model versions drift underneath a running deployment. Leaving the claim unqualified would have driven the wrong test strategy — chasing reproducible generation instead of reproducible replay.

## Decision
The kernel guarantees **record/replay determinism**. Every model call and tool result is recorded; replay serves recorded observations rather than re-executing. Every tool declares an `EffectClass` (`PURE` / `IDEMPOTENT` / `DESTRUCTIVE`), and replay re-executes only `PURE` calls. A cassette adapter implementing `ModelProvider` runs the entire kernel in CI with zero API calls, verified by `sagiha replay --verify-all`.

> **Implementation note (2026-07-30):** the decision stands. The cassette adapter exists in stub form; digest-matched replay and the `sagiha replay --verify-all` CI gate are **Planned — Sprint 3**. See [STATUS.md](../STATUS.md).

## Consequences
The orchestrator becomes unit-testable at Day 0 — the cheapest testability win in the design, which is why it is an S0 deliverable rather than a later refinement. Time-travel debugging becomes sound: without effect classification, replaying a trajectory containing `git push` or `rm` would perform it again. A replay failure reliably indicates the kernel became sensitive to something outside the recording — wall-clock, dict ordering, unseeded randomness, or an unclassified side effect.

## Reversal Conditions
None. Reproducible generation is not achievable, and this is the strongest available substitute.
