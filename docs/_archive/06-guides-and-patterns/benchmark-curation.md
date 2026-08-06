---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Benchmark Curation**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

The S0 gate requires ≥70% resolution on a pinned 30-task suite to establish exit criteria and a measurable baseline for subsequent slices.

> [!IMPORTANT]
> **Target Repository**: Per [ADR-0015](../08-decisions/0015-benchmark-target-repository.md), commit-replay harvesting uses **`brainopensource/Harness-D-power`** (`https://github.com/brainopensource/Harness-D-power`) for S0 Core and E0 benchmarks to guarantee zero-contamination baselines.

## **The Three Suites**

| Suite | Size | Purpose | Execution Cadence / Cost |
| :--- | :--- | :--- | :--- |
| **Smoke** | 10 tasks | Fast per-PR sanity check | Per-PR (minutes, cents) |
| **S0 Core** | 30 tasks | Slice gates & regression testing | Nightly / Releases (~1 hr, single-digit $) |
| **Commit-Replay** | 200+ tasks | RHI evaluation & statistical work | Nightly / Releases (hours, hundreds $) |

## **Building the S0 Core Suite**

### Sourcing & Harvesting

Harvested from real historical target repository commits (reverted into tasks while retaining tests as ground truth):

> **Planned — Block 2 (E0-lite)** ([STATUS.md](../STATUS.md)).

```bash
sagiha bench harvest \
  --repo /path/to/repo \
  --since 2024-01-01 \
  --require-tests \
  --max-files 3 \
  --limit 200
```

* **Rationale**: Real commits reflect true codebase difficulty distributions, cost nothing to generate, and remain immune to synthetic task author bias.

### Task Composition (30 Tasks)

| Category | Count | Scope & Purpose |
| :--- | :--- | :--- |
| **Single-file bug fix** | 10 | 1 file, clear failing test (S0 core target) |
| **Single-file feature** | 6 | Add function/method with tests |
| **Multi-file refactor** | 5 | 2–3 files (held out for S3) |
| **Test authoring** | 4 | Write tests for existing untested code |
| **Diagnostic-driven** | 3 | Type/lint errors, no failing test |
| **Adversarial** | 2 | Deliberately unsolvable or underspecified (measures clean failure / non-hallucination) |

### Task Specification Format

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

### Selection & Inclusion Criteria

* **Inclusion**: Machine-verifiable acceptance, self-contained (no network/credentials), deterministic (5× pass on base commit), bounded (diff <200 lines), non-trivial.
* **Exclusions**: DB migrations, time/timezone-dependent logic, network-dependent tests. Flakiness must be verified *before* inclusion.

## **Suite Freezing & Versioning**

Frozen suites are committed under `benchmarks/definitions/` within the [trusted computing base](../04-workflows-and-loops/rhi-outer-loop.md) (read-only to agents, enforced by CI).

* Modifications increment version (e.g., **v2**) and must run alongside prior versions.
* Task removals require logged justification, and versions are stamped into all run results.

## **Establishing the Noise Floor**

Measure stochastic baseline variance prior to suite evaluation:

> **Planned — Block 2**.

```bash
sagiha bench --suite s0-core --runs 2 --mode aa --model <exact-version>
```

Calculates score-delta distributions under pure stochasticity (`benchmarks/noise-floor.md`). Re-measure whenever underlying model versions change to avoid confusing provider updates with harness changes.

## **Reporting Standard**

Results must report variance, cost, latency, and gating metrics:

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

> [!NOTE]
> `tests_unmodified 0` and `degradations 0` are mandatory validity preconditions. Non-zero values invalidate the run.
