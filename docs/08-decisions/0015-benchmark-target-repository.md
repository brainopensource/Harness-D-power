---
status: normative
updated: 2026-07-29
---

# ADR-0015: S0 Benchmark Target Repository

**Status**: **Proposed** — requires maintainer sign-off before it is Accepted
**Date**: 2026-07-29

## Context

The S0 gate is stated as a resolve rate over a pinned 30-task suite, and
[Benchmark Curation](../06-guides-and-patterns/benchmark-curation.md) specifies commit-replay
harvesting: take a real repository, find commits that fix a failing test, revert to the parent, and
grade the agent on reproducing the fix.

That requires a repository with history **and** tests **and** a revertable base commit. SAGIHA has no
code, so it cannot harvest from itself at S0. **An external repository is therefore a hard dependency
of the project's first gate**, and its characteristics — language, test framework, size, flake rate —
silently determine what "≥70% resolved" means.

Right now that repository is unnamed. Every number the project reports is relative to a choice nobody
has written down, which makes the headline metric unfalsifiable.

## Decision

**The rubric is decided. The repository is not, and cannot be decided by the author of this ADR** —
it is a maintainer judgement about what the project wants to be good at.

### Selection rubric

| Requirement | Reason |
| :--- | :--- |
| ≥2 years of history, ≥1,000 commits | Enough fix-commits to harvest 30 tasks without scraping the barrel |
| Test suite green at HEAD, runs in <5 min | The evaluator runs it per candidate; a 20-minute suite makes best-of-N unaffordable |
| Measured flake rate <1% | A flaky suite makes the A/A noise floor meaningless, and the noise floor is the moat |
| Python, pytest | Matches the only v1 `Toolchain` adapter |
| Permissive licence (MIT/Apache-2.0/BSD) | Task definitions and diffs get published with results |
| Not in any public agent benchmark | Contamination: SWE-bench repos are in every frontier model's training data |
| Non-trivial but not sprawling (10k–100k LOC) | Below 10k, tasks are toy; above 100k, retrieval dominates and S0 stops measuring the inner loop |
| Multi-file fixes present | Single-file-only would make the S0 target trivially met and uninformative |

### Candidate classes

| Class | Example shape | Pro | Con |
| :--- | :--- | :--- | :--- |
| **A — Mid-size OSS library** | A well-tested utility or client library outside the SWE-bench set | Realistic, clean history, publishable | Contamination must be verified, not assumed |
| **B — The maintainer's own repository** | A private or personal project with real history | Zero contamination risk; failures are legible to the maintainer | Results are not externally reproducible; cannot be published |
| **C — Both, reported separately** | A as the public number, B as the private control | Cross-checks contamination directly: a large A/B gap *is* the contamination signal | Twice the harvesting work |

**Recommended: C**, with A as the headline suite. The extra cost is one harvester run, and it converts
contamination from an assumption into a measurement — which is the same discipline the A/A noise floor
applies to comparison.

### Recorded regardless of choice

The task manifest pins: repository URL, commit SHA range harvested, harvester version, per-task base
commit, and the measured flake rate at harvest time. A benchmark whose provenance is not pinned is a
number that cannot be defended six months later.

## Consequences

**Makes easy**: the S0 target becomes a claim about a named artifact. Anyone can re-run it.

**Makes hard**: the choice is close to irreversible in practice — changing the target repository
invalidates every historical comparison, so the first change costs the project its trend line.

**Forecloses**: nothing technically, but it does set what "good" means for the first year of
development. That is why it needs a decision rather than a default.

## Reversal Conditions

* The suite saturates — resolve rate exceeds 90% and stops discriminating between harness changes.
* Contamination is discovered after the fact (the model reproduces fixes verbatim, including comments).
* Multi-language support arrives and a Python-only benchmark stops representing the workload.

In all three cases the old suite is retained and reported alongside the new one for at least one
release, so the trend line survives the transition.

## Open

**Name the repository.** Until that happens this ADR stays `Proposed`, and the S0 resolve-rate target
should be read as a placeholder rather than a commitment.
