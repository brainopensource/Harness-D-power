---
status: normative
updated: 2026-08-05
---
# ADR-0002: No Capability Number Is Published Before the A/A Floor

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F2

## Context

The prototype's primary conceptual failure was **sequencing measurement last**. Capability
shipped without proof of value, and every number taken had to be discarded. One instrument
defect — an editable install leaking live source into supposedly-isolated worktrees — made
candidate diffs invisible to the gates scoring them, and **that one produced numbers**.

A number taken over a broken instrument is not a faster route to the same place. It is work
that gets discarded retroactively, along with every decision made on it.

Both proposals wanted an A/A noise floor; the audit confirmed this. The disagreement was
narrower than it was framed: whether a capability number may be published *before* the floor
exists.

## Decision

- **No capability number is published before the A/A variance floor is.** Until
  `docs/rationale/benchmarks/noise-floor.md` holds a real number, the project reports no
  results.
- **B1 starts now** — the upstream repository cache. Standalone, no AETHER dependency, and
  it unblocks every number.
- **B3 and B4 arrive with the components they isolate** — the evaluation container and the
  typed instrument-failure distinction, respectively.
- **N ≥ 50** instances is adopted as the minimum, taken from the opposing proposal. "≥2
  passes per arm" is vaguer than it should be given a local endpoint makes passes free.

## Consequences

- The walking skeleton ships and **reports an honest zero**. That is a correct result, not a
  failure of the milestone.
- An instrument failure is never a data point. Exit-127 and uncollectable test files are
  instrument errors, not test failures.
- Every gate ships with a test proving it can fail.

## Explicitly not decided

**This is not "fix everything before writing code."** Two independent reviewers read it that
way. Code starts immediately; only *publication of a capability number* is gated. The
stronger reading is not implementable and is rejected.

## Reversal Conditions

**None.** If this is wrong, the project has no way to know anything — the statistics would
be computed over an instrument whose validity is unestablished. This is the one decision in
the set that is a post-mortem rather than a preference, and it is deliberately given no
escape hatch.
