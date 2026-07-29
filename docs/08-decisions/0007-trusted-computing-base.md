# ADR-0007: The Trusted Computing Base Is Never Agent-Writable

**Status**: Accepted
**Date**: 2026-07-28

## Context
The RHI outer loop listed "adapter code, policies" as mutable artifacts and had validated mutations "automatically commit to the production scaffolding baseline." Combined with shell access, that made editing the grader the cheapest available path to a higher score. This is not a question of intent: an improver optimized against benchmark results has a gradient pointing directly at the benchmark, and it will find it.

## Decision
The following are outside the agent's writable surface: policy engine and autonomy config, Evaluator, gate definitions, benchmark task definitions, the deployment gate itself, secret handling, and the sandbox boundary. Enforced three ways — path allowlist in `MutationProposal.targets`, residence on a branch the agent cannot push, and CI rejection of any diff touching a TCB path. Deployment of any validated mutation requires human sign-off.

The `tcb-isolation` import-linter contract additionally forbids the policy engine and evaluator from importing `agency` or `aoi`, so the TCB cannot acquire a dependency on mutable code.

## Consequences
Self-improvement is bounded and auditable. The loop cannot fully self-deploy, which is the intended limit rather than a shortcoming. Related gate: `tests_unmodified` prevents the same exploit one level down, at candidate scope.

## Reversal Conditions
None. Removing this makes every self-improvement measurement unfalsifiable.
