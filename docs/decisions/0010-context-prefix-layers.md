---
status: normative
updated: 2026-08-05
---
# ADR-0010: Five Prefix Layers; the Generated Repo Layer Is the First M2 Ablation

**Status**: Accepted (provisional) · **Date**: 2026-08-05 · **Fork**: F10

## Context

Both proposals wanted a stable, cache-friendly prompt prefix, and both wanted a generated
repository-context layer inside it — one as a five-layer prefix, one as three fixed cache
markers with an AST skeleton map as marker three. Both targeted a >92% cache hit rate.

**Neither had evidence that the repository-context layer helps.** And the one piece of
literature either cited on the question measured this category as *negative-value when
generated*: repository context files did not generally improve success rate, increased
inference cost by >20%, and LLM-generated files **reduced** success by ~3% while
human-written ones improved it by ~4%.

One proposal cited that paper to argue against generic auto-dumps while simultaneously
pinning a machine-generated repo skeleton into its cache. The other has the same exposure.
**The split matters more than the average: generated context is the negative-value half.**

## Decision

- **Five prefix layers**, at most four `cache_control` breakpoints.
- The prompt cache is architecture, not optimization: fixed layer order, explicit
  breakpoints, hit rate as a gated CI metric over a fixed replay.
- **The generated repository-context layer ships enabled and is the first M2 ablation**,
  measured against a hand-authored brief of equal token budget.

## Consequences

- The >92% hit-rate figure is **a target to calibrate against our own replay**, not a figure
  taken from a reference. The first measurement may move it.
- Best-of-N fan-out must be cache-sequenced. Naive fan-out over a shared prefix is a large
  cost multiple, and that is the workload the prefix design exists for.
- If the layer loses its ablation, this design collapses to something very close to the
  three-marker alternative — the gap between the two proposals was one measurement wide.

## Reversal Conditions

**The M2 ablation.** If the generated layer does not clear the noise floor against a
hand-authored brief of equal token budget, **it is deleted, not demoted**.

If it shows *negative* value, that is a finding worth publishing rather than a defect to
hide — it would replicate a published result on our own instruments.
