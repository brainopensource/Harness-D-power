---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Running Benchmarks & Evaluating Trajectories**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Establish the Noise Floor First**

Before comparing anything to anything, run the **unmodified** harness twice against the suite and measure the score-delta distribution:

> **Planned — Block 2 (E0-lite)** ([STATUS.md](../STATUS.md)). The methodology below is the target measurement contract; the `sagiha bench` CLI is not available yet.

```bash
sagiha bench --suite internal --runs 2 --mode aa
```

This is the A/A test, and it is the prerequisite for every other number in this document. Most harness changes produce effects smaller than run-to-run variance; without knowing the floor, "the score went up" is indistinguishable from noise, and accepting on that basis ratchets the system permanently onto randomness.

Re-measure the floor whenever the model version changes.

## **The Suites**

### Commit-Replay (primary)

Harvest real commits from the target repository's history, revert them, and pose them as tasks with the original diff and tests as ground truth:

> **Planned — Block 2**. Harvester and suite runner land with E0-lite.

```bash
sagiha bench harvest --repo /path/to/repo --since 2024-01-01 --limit 200
sagiha bench --suite commit-replay
```

Unbounded, uncontaminated, in-distribution, and self-maintaining as the repository evolves. Strictly better than hand-authored synthetic bugs on realism, volume, maintenance cost, and contamination resistance.

### Public (smoke test only)

**SWE-bench Lite is not a primary screen**: contaminated across frontier models, Python-only, and shaped as single-repo issue resolution rather than the long-horizon multi-file target. Optimizing against it tunes the harness for a distribution nobody wants. Prefer SWE-bench Verified or Multi-SWE-bench when public comparison is needed, and treat the result as a sanity check rather than the objective.

### Retrieval (measured separately)

> **Planned — Block 4** (retrieval) after Block 2 measurement substrate exists.

```bash
sagiha bench retrieval --labelled-set queries.jsonl   # recall@k
```

Reported separately from task success so retrieval regressions are attributable rather than buried in end-to-end noise. **LongMemEval is not used** — it measures conversational memory, not code retrieval.

## **Reporting Rules**

1. **Never report a point estimate.** k ≥ 3 runs per task, with variance.
2. **Judge against the noise floor.** A delta inside it is not a result.
3. **Correct for multiple comparisons.** Screening many candidates against one uncorrected threshold manufactures winners.
4. **Pair your runs.** Same tasks, same seeds, same model version. Unpaired comparisons across model updates measure the provider, not your harness.
5. **Report cost and cache hit rate alongside success.** A token-reduction claim that ignores cache economics measures the wrong quantity.

## **Budget**

A few hundred tasks × several dollars × k repetitions × many candidates puts a full outer-loop iteration in the thousands of dollars. Use the AOI pre-filter to rank candidates before spending, run the loop on a schedule rather than continuously, and set `governor.max_spend_usd_per_hour` before starting a long sweep.

## **Trajectory Analysis**

> **`sagiha replay` is available now (Sprint 3a closed)**; `trajectory show`/`diff` remain **Planned**
> ([STATUS.md](../STATUS.md)).

```bash
sagiha trajectory show <run-id>       # steps, tool calls, diagnostics, scores — planned
sagiha trajectory diff <id-a> <id-b>  # where two runs diverged — planned
sagiha replay <run-id> --verify       # deterministic re-execution, zero API calls — available now
```

Trajectories are stored append-only in SQLite-WAL and instrumented with OTel GenAI semantic conventions, so standard tracing tooling works on them directly.

## **Watch For**

* **Gate failures clustering on `tests_unmodified`** — the agent is trying to edit its grader. Investigate the prompt, not the gate.
* **Improvements that vanish on the commit-replay split** — overfitting to the public suite.
* **Cost rising while success holds** — usually a cache-invalidating change to context assembly.
