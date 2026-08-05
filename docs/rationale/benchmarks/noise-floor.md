---
status: rationale
updated: 2026-08-01
retrieval: excluded
---
> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is a historical rationale, research reference, or benchmark log (`retrieval: excluded`). It is excluded from active search indexing and context retrieval. Do not cite this file as normative status or active code contracts.

# 📐 v2-S4 A/A Noise Floor — s0-core

**Status: still not populated. A run was attempted on 2026-08-01 and produced no usable floor.**
The reason is recorded below, in full, because "we tried and it did not work" is a result and
silently leaving the old template in place would not be.

> **Do not cite a noise floor from this file.** There is not one yet. Do not cite the `0.0%` pass
> rate the attempted run printed either — see *What the attempted run actually measured*.

## What exists now

`benchmarks/definitions/s0-core.json` is **committed and pinned** (W9.1/W9.2, audit M-1):

| Property | Value |
| :--- | :--- |
| Suite id | `s0-core-swebench-lite-30` |
| Source | `princeton-nlp/SWE-bench_Lite`, imported via `scripts/import_swebench_lite.py` |
| Tasks | 30 |
| Repos | 12 (astropy, django, matplotlib, seaborn, flask, requests, xarray, pylint, pytest, scikit-learn, sphinx, sympy) |
| Base commits | 30/30 pinned, full 40-char shas |
| Reproducing test command | 30/30, derived from each task's `FAIL_TO_PASS` set |
| `validated` | **`false` on every task** — see below |

Imported rather than harvested because harvesting this repo yields 0/23 valid tasks
([s4-harvest-findings.md](./s4-harvest-findings.md)). Selection is round-robin across repos in
`instance_id` order, so re-running the importer reproduces the identical 30 tasks — verified by
running it twice and diffing.

`validated: false` is deliberate and load-bearing. Validation in this harness means *this tree
reproduced the failing test at `base_commit`*. That has not happened. SWE-bench's own validation is
not ours to claim, and marking these `true` would be the H-series defect in a data file.

## What blocks the A/A run

**The E0 runner cannot execute an imported suite.** It materializes each task with
`git worktree add <base_commit>` against **the local repository** (`adapters/workspace/worktree.py`,
called from `e0/runner.py`). SWE-bench base commits live in twelve upstream repositories that are
not cloned here, so every one is an invalid reference:

```
fatal: invalid reference: 0a4204fd7555cfedd43f43017c94d24ef48244a5
```

All 30 tasks × 2 passes failed this way. Closing this needs per-task upstream clone/fetch in the
runner — a real capability addition to `e0/`, not a remediation-wave fix.

**Second, independent blocker: no model.** No endpoint (`localhost:11434` refused) and no
`OPENROUTER_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in this environment. Even with
working worktrees there is nothing to run the suite against, and no cassettes exist for these tasks.

## What the attempted run actually measured

```
A/A Calibration mean_delta: 0.000, beats_noise_floor: None
Benchmark complete! Pass rate: 0.0%
```

**These numbers are not a measurement of the harness.** `mean_delta: 0.000` is the difference
between two passes that both failed identically at worktree setup, and `0.0%` is 30 infrastructure
failures, not 30 unsolved tasks. Publishing either as a noise floor would manufacture exactly the
kind of measured-looking-but-never-computed number that H1/H5 and C-1 exist to eliminate. They are
quoted here only so nobody re-derives them and mistakes them for a result.

## Consequences for the ablations (W9.5)

All three remain **not yet measured**:

| Ablation | Status |
| :--- | :--- |
| Best-of-N vs single-shot | Not measured — no floor, no runnable suite, no model |
| Retrieval on vs off | Not measured — same |
| `sagiha init` on vs off | Not measured — same |

Therefore **`search.enabled` and `retrieval.enabled` both stay `false`.** A default flip requires a
measured delta that beats a measured floor; neither exists. The mechanisms are complete and the
empirical halves are open — that is the honest-negative posture, unchanged.

## How this gets populated

Three preconditions, in order:

1. **Runner support for imported suites** — clone/fetch each task's upstream repo at `base_commit`
   before allocating a worktree, or a `--repo-cache` the runner materializes from.
2. **A model** — a live endpoint or recorded cassettes for these 30 tasks.
3. **Then**, and only then:

```bash
uv run sagiha bench --suite benchmarks/definitions/s0-core.json --aa --runs 2 \
    --output docs/rationale/benchmarks/noise-floor.md
```

`tests_unmodified` nonzero on an A/A run (both passes are the *unmodified* harness) is itself a
signal worth investigating before trusting anything else in the report — see `e0/reporter.py`'s
gate-failure breakdown.

## Template shape (to be overwritten by the real report)

```
Suite: s0-core v1 (N tasks) · model <version> · harness <version> · config <hash>
Runs: 2 · Noise floor: ±<ci_width>pp

Resolved:      <mean> / <n_tasks>  (<pct>% ± <std>pp)
Cost/success:  $<mean> ± $<std>
Wall/success:  <mean>s
Cache hit:     <rate>
Gate failures: tests_pass <n> · tests_unmodified <n> · coverage <n>
Bootstrap CI:  [<lo>, <hi>] (alpha=0.05, seed=0, n=<n_tasks>)
```
