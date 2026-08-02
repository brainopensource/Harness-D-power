---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Running Benchmarks & Evaluating Trajectories**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Establish the Noise Floor First**

Before evaluating harness changes, execute A/A baseline measurements to quantify stochastic variance:

> **Planned — Block 2 (E0-lite)** ([STATUS.md](../STATUS.md)). CLI `sagiha bench` is planned.

```bash
sagiha bench --suite internal --runs 2 --mode aa
```

Score changes inside the noise floor are statistically meaningless. Always re-measure the baseline floor whenever model versions change.

## **The Evaluation Suites**

### Commit-Replay (Primary Suite)

Reverts historical commits in target repositories to create tasks with ground-truth diffs and test suites:

> **Planned — Block 2** ([STATUS.md](../STATUS.md)).

```bash
sagiha bench harvest --repo /path/to/repo --since 2024-01-01 --limit 200
sagiha bench --suite commit-replay
```

Uncontaminated, in-distribution, multi-file, and self-maintaining.

### Public Benchmarks (Sanity Check Only)

* **SWE-bench Lite**: Avoid as a primary benchmark (high model contamination, Python-only, single-repo focus).
* **SWE-bench Verified / Multi-SWE-bench**: Use as secondary sanity checks rather than primary optimization targets.

### Retrieval Benchmarks (Isolated Measurement)

> **Planned — Block 4** (retrieval metrics).

```bash
sagiha bench retrieval --labelled-set queries.jsonl   # recall@k
```

Evaluated separately from task resolution to prevent retrieval regressions from hiding inside full-run noise. *(Note: LongMemEval is excluded as it measures chat context rather than code retrieval).*

## **Reporting Rules**

1. **Variance Tracking**: Run $k \ge 3$ iterations per task and report variance ranges (never single point estimates).
2. **Noise Floor Comparison**: Filter out score deltas contained within the noise baseline.
3. **Multiple Comparison Corrections**: Apply statistical correction thresholds when screening multiple candidates.
4. **Paired Execution**: Standardize task sets, random seeds, and model versions across comparisons.
5. **Economic Metrics**: Always pair resolution rates with token costs and cache hit rates.

## **Budget Governance**

Pre-filter candidate improvements via AOI ranking and set `governor.max_spend_usd_per_hour` before starting evaluation sweeps.

## **Trajectory Analysis**

> **`sagiha replay` is active (Sprint 3a)**; `trajectory show`/`diff` are **Planned** ([STATUS.md](../STATUS.md)).

```bash
sagiha trajectory show <run-id>       # Detailed execution trace — planned
sagiha trajectory diff <id-a> <id-b>  # Execution path divergence — planned
sagiha replay <run-id> --verify       # Deterministic re-execution (zero API calls) — available now
```

Trajectories are recorded in SQLite-WAL using OTel GenAI semantic conventions.

## **Diagnostic Anomalies to Monitor**

* **High `tests_unmodified` Gate Failures**: Indicates the agent is attempting to modify grader tests; adjust prompt guidelines.
* **Discrepancies on Commit-Replay Split**: Indicates overfitting to public benchmark suites.
* **Escalating Costs at Constant Success Rates**: Indicates cache invalidation in context assembly.
