---
status: historical
updated: 2026-07-29
---
# ADR-0015: S0 Benchmark Target Repository

**Status**: Accepted  
**Date**: 2026-07-29  
**Target Repository**: `brainopensource/Harness-D-power` (`https://github.com/brainopensource/Harness-D-power`)

## Context

The S0 gate requires a resolve rate over a 30-task suite harvested via commit-replay per [Benchmark Curation](../06-guides-and-patterns/benchmark-curation.md). SAGIHA has no self-harvestable code at S0, making an external repository a hard dependency to establish an unfalsifiable baseline.

## Decision

`brainopensource/Harness-D-power` (`https://github.com/brainopensource/Harness-D-power`) is adopted as Candidate Class B (Maintainer Repository) for commit-replay task harvesting, establishing a zero-contamination baseline for E0/S0 gates.

### Selection Rubric

| Requirement | Reason |
| :--- | :--- |
| ≥2 years history, ≥1,000 commits | Harvest 30 tasks without exhausting history |
| Test suite green at HEAD, runs in <5 min | Fast evaluator execution per candidate |
| Flake rate <1% | Protects A/A noise floor integrity |
| Python, pytest | Compatible with v1 `Toolchain` adapter |
| Permissive license (MIT/Apache-2.0/BSD) | Task definitions and diffs can be published |
| Not in public agent benchmarks | Prevents SWE-bench training set contamination |
| 10k–100k LOC | Non-trivial size without being dominated by retrieval |
| Multi-file fixes present | Ensures meaningful multi-file task evaluation |

### Candidate Classes

| Class | Example shape | Pro | Con |
| :--- | :--- | :--- | :--- |
| **A — Mid-size OSS library** | Outside SWE-bench set | Realistic, clean history | Contamination must be verified |
| **B — Maintainer repository** | Private/personal project | Zero contamination risk | Not externally reproducible |
| **C — Both (reported separately)** | A as headline, B as control | Directly measures contamination gap | Twice the harvest effort |

**Recommended**: Class C with A as headline suite.

### Pinned Task Manifest Requirements
Manifest must pin: repository URL, commit SHA range, harvester version, per-task base commit, and measured flake rate at harvest time.

## Consequences

- **Easy**: S0 benchmark target becomes a verifiable, reproducible named artifact.
- **Hard**: Changing target repository invalidates historical comparisons and trend lines.
- **Forecloses**: Prevents unpinned, informal metrics.

## Reversal Conditions

- Suite saturates (resolve rate > 90%).
- Post-hoc contamination is discovered.
- Multi-language support arrives, rendering Python-only benchmarking insufficient.

Old suite is retained alongside new suite for at least one release upon transition.

## Status & Resolution

**Resolved.** Target repository finalized as `brainopensource/Harness-D-power`. S0/E0 commit-replay harvesting uses this baseline.
