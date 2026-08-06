---
status: normative
updated: 2026-08-05
---
# ADR-0004: Lift Is the Committed Target; Absolutes Are Provisional

**Status**: Accepted (provisional) · **Date**: 2026-08-05 · **Fork**: F4

## Context

Two target sets were proposed: Pro ≥ 80% / Verified ≥ 96%, versus Verified ≥ 90% / Pro ≥ 60%
/ Terminal-Bench ≥ 75%. The higher set was derived from a leaderboard re-baselining (Pro
leader ~80.3%, Verified frontier ~96%) that is **single-session web research, independently
unverified, and flagged as such by its own author**. The entire fork rests on it.

Meanwhile the number that actually reflects our work was being treated as secondary in both
proposals. The absolute score is dominated by which model we are allowed to call — a
commercial decision, not an engineering one.

## Decision

**Lift is the committed target.**

- **Lift ≥ +10 points** — the resolve-rate delta between a bare model call and the same model
  inside AETHER, on identical tasks, same model both sides.
- **An absolute number is never published without its lift.**

**Absolute targets are provisional**, pending re-verification of the leaderboard:

| Suite | Committed | Stretch |
| :--- | :--- | :--- |
| SWE-bench Verified | ≥ 90% | ≥ 96% |
| SWE-bench Pro | ≥ 60% | ≥ 80% |
| Terminal-Bench | ≥ 75% | — |

Terminal-Bench is adopted regardless of how the re-verification lands — it measures something
the other two do not.

## Consequences

- Inverting the priority costs nothing. The lift target was **identical in both proposals**,
  which is the strongest signal available that it is the real target.
- Lift survives a model swap, a leaderboard reshuffle and a diligence review. Absolutes
  survive none of those.
- Roughly 30% of public Pro tasks were estimated broken in a mid-2026 audit. That is another
  reason not to let an absolute define success on its own.

## Reversal Conditions

- **The absolute targets are re-set when the leaderboard is independently re-verified.**
  Until then they are committed gates in form only, and no roadmap decision may rest on the
  gap between the committed and stretch numbers.
- Benchmark retirement or migration; a leaderboard shift making Pro uninformative;
  contamination findings invalidating the public pool.
- The lift target is re-set only if a measured lift ceiling proves +10 points unreachable on
  a verified instrument — never because it is inconvenient.
