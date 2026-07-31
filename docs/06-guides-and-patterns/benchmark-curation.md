---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Benchmark Curation**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

The S0 gate reads "≥70% resolved on a pinned 30-task suite." That suite does not exist, and it is the one prerequisite that cannot be derived from the architecture — it must be curated. Without it, S0 has no exit criterion and every subsequent slice inherits an unmeasurable baseline.

This is the only remaining artifact standing between the documentation and Sprint 1.

> [!IMPORTANT]
> **The target repository is finalized.** Per [ADR-0015](../08-decisions/0015-benchmark-target-repository.md),
> commit-replay harvesting uses **`brainopensource/Harness-D-power`** (`https://github.com/brainopensource/Harness-D-power`)
> for S0 Core and E0 benchmark task harvesting, ensuring zero-contamination baseline evaluation.

## **The Three Suites**

| Suite | Size | Purpose | Cost per run |
| :--- | :--- | :--- | :--- |
| **Smoke** | 10 tasks | Per-PR sanity, fast | minutes, cents |
| **S0 Core** | 30 tasks | Slice gates, regression | ~1 hour, single-digit dollars |
| **Commit-Replay** | 200+ | RHI evaluation, statistical work | hours, hundreds of dollars |

Only Smoke runs per-PR. The others run nightly and on release tags.

## **Building the S0 Core Suite**

### Sourcing

Harvest from the target repository's own history — real commits, reverted and posed as tasks:

> **Planned — Block 2 (E0-lite)** ([STATUS.md](../STATUS.md)).

```bash
sagiha bench harvest \
  --repo /path/to/repo \
  --since 2024-01-01 \
  --require-tests \
  --max-files 3 \
  --limit 200
```

The harvester keeps commits that touched test files alongside source (giving ground-truth verification), reverts the source change while **retaining the tests**, and records the original diff as a reference solution — never as the grading criterion, since a different correct implementation must pass.

**Why harvested rather than authored**: hand-written synthetic bugs encode the author's idea of what an agent finds hard, which is uncorrelated with what agents actually find hard. Real commits carry the genuine difficulty distribution of the codebase, cost nothing to produce, and stay current as the repository evolves.

### Composition

Thirty tasks, deliberately distributed:

| Category | Count | Character |
| :--- | :--- | :--- |
| Single-file bug fix | 10 | One file, clear failing test — S0's core competency |
| Single-file feature | 6 | Add a function/method with tests |
| Multi-file refactor | 5 | 2–3 files, held out for S3 |
| Test authoring | 4 | Write tests for existing untested code |
| Diagnostic-driven | 3 | Type or lint errors, no failing test |
| **Adversarial** | 2 | Deliberately unsolvable or underspecified |

The adversarial pair earns its place: a harness that "solves" an unsolvable task is hallucinating, and one that quietly weakens a test to pass is grader-editing. **Expected outcome for these two is a clean failure with an accurate explanation** — measuring honest failure is as important as measuring success, and nothing else in the suite tests for it.

### Task Format

```yaml
task_id: fix-parser-offset-001
goal: |
  `parse_header()` returns an off-by-one column for tab-indented input.
  See the failing test.
acceptance:
  - description: The failing test passes
    check: "pytest tests/test_parser.py::test_tab_offset"
    required: true
  - description: No existing test regresses
    check: "pytest tests/"
    required: true
  - description: No new type errors
    check: "pyright src/parser.py"
    required: true
setup:
  base_commit: a1b2c3d
  revert_files: [src/parser.py]
budget:
  max_usd: 0.50
  max_wall_clock_s: 600
metadata:
  category: single_file_bugfix
  reference_diff: .bench/solutions/fix-parser-offset-001.diff
```

### Selection Criteria

Include a candidate only if all hold:

* **Verifiable** — acceptance is fully machine-checkable
* **Self-contained** — no network, no external services, no credentials
* **Deterministic** — the test suite is not itself flaky (verify: run 5× on the base commit)
* **Bounded** — reference solution under ~200 changed lines
* **Non-trivial** — a trivial one-liner measures nothing

Exclude: anything needing a migration, anything time- or timezone-dependent, anything whose tests touch the network.

**Verify flakiness before inclusion, not after.** A flaky task injects variance directly into the noise floor and will be misread as harness instability for weeks.

## **Freezing**

Once assembled, the suite is **frozen and committed** under `benchmarks/definitions/`, which sits inside the [trusted computing base](../04-workflows-and-loops/rhi-outer-loop.md) — not writable by the agent, protected by the CI path check.

A moving benchmark makes every historical comparison meaningless. When the suite must change:

* Adding tasks creates **v2**, run alongside v1 through at least one full cycle
* Removing a task requires a recorded reason
* The suite version is stamped into every result

## **Establishing the Noise Floor**

Before the suite grades anything:

> **Planned — Block 2**.

```bash
sagiha bench --suite s0-core --runs 2 --mode aa --model <exact-version>
```

This runs the unmodified harness twice and reports the score-delta distribution under pure stochasticity. Publish it in `benchmarks/noise-floor.md`.

**Re-measure whenever the model version changes.** A provider updating a model underneath you is statistically indistinguishable from your harness changing — and without a current floor, that ambiguity silently contaminates every subsequent conclusion.

## **Reporting**

Never a bare percentage:

```
Suite: s0-core v1 (30 tasks) · model <version> · harness 0.4.2 · config a3f9e1
Runs: 3 · Noise floor: ±4.2pp

Resolved:      22.3 / 30  (74.3% ± 3.1)
Cost/success:  $0.31 ± 0.08
Wall/success:  4m12s ± 1m03s
Cache hit:     0.84
Gate failures: tests_pass 5 · tests_unmodified 0 · coverage 2
Degradations:  0
```

`tests_unmodified 0` and `degradations 0` are validity preconditions, not scores. A run with either nonzero is discarded — the first means a candidate may have edited its grader, the second means capability silently disappeared mid-run. In both cases the headline number is not measuring what it claims to.
