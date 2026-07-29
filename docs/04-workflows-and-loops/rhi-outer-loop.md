---
status: normative
updated: 2026-07-29
---

# **Recursive Harness Self-Improvement (RHI) Outer Loop**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

The outer loop optimizes harness scaffolding under held-out validation. It is **scheduled, not continuous** — see the cost note at the end.

## **The Trusted Computing Base**

A self-improving system able to edit its own evaluator has a trivial optimum: edit the evaluator. Any design that lists policy or grading code as mutable, or that auto-commits validated mutations to the production baseline, makes rewriting the grader the cheapest available path to a higher score — and an optimizer will find it before it finds a real improvement.

**Never writable by the agent:**

* Policy engine and autonomy configuration
* Evaluator, gate definitions, benchmark task definitions
* The deployment gate itself, and this list
* Secret handling and the sandbox boundary

Enforced three ways: path allowlist in `MutationProposal.targets`, residence on a branch the agent cannot push, and CI rejection of any diff touching a TCB path.

**Mutable surface**: prompts, retrieval and compaction parameters, tool descriptions, routing heuristics, non-Control adapter code.

## **Cycle**

1. **Trajectory Ingestion** — traces, tool logs, and step scores to an append-only store instrumented with **OTel GenAI semantic conventions**, so ecosystem tooling works without bespoke adapters. The EventBus is the single source of truth; the TrajectoryStore and the OTel span log are independent subscribers — neither is derived from the other (see [Microkernel & Bus](../02-architecture/microkernel-and-bus.md)).
2. **Mutation Proposal** — the Meta-Improver reviews failure patterns and proposes targeted changes within the mutable surface. AOI ranks candidates so only promising ones reach expensive evaluation.
3. **Verification** — the four gates below.
4. **Deployment** — staged for **human sign-off**. Mutations do not self-deploy.

## **Verification Gates**

### Tier 0 — A/A Noise Floor (run first, always)

Run the **unmodified** harness twice against the suite and measure the score-delta distribution under pure stochasticity. This is the noise floor, and any candidate that fails to beat it is not an improvement no matter how much its score moved.

This gate is the most important addition to the loop. Most harness mutations produce effects smaller than run-to-run variance, so "accept if the score improved" **ratchets permanently on noise** — accumulating changes that are individually meaningless and collectively a random walk away from the baseline. Without an A/A measurement there is no way to tell the difference.

### Tier 1 — Screening

A held-out split, treated as a smoke test rather than the objective.

**SWE-bench Lite is unsuitable as the primary screen**: contaminated across frontier models, Python-only, and shaped as single-repo issue resolution — which is not the long-horizon multi-file target. Optimizing harness mutations against it tunes the system for a distribution nobody wants. Prefer SWE-bench Verified and Multi-SWE-bench where public comparison is desired.

### Tier 2 — Commit-Replay Private Split

The private split is **harvested, not authored**: mine real commits from target repository history, revert them, pose them as tasks with the original diff and tests as ground truth.

This yields an unbounded, uncontaminated, in-distribution benchmark that stays current as the repository evolves — and it removes the need to hand-write synthetic bugs whose distribution nobody can defend. It is strictly better than the previous "private synthetic mutation split" on every axis: realism, volume, maintenance cost, and contamination resistance.

### Tier 3 — Paired Regression & Statistics

* Paired evaluation on identical task sets with fixed seeds
* **k ≥ 3 runs per task**, reporting variance rather than a point estimate
* Acceptance threshold **corrected for multiple comparisons** — screening many candidates against one uncorrected threshold manufactures winners from noise
* No increase in token consumption or latency; cache hit rate reported alongside

## **Cost Reality**

A few hundred tasks × several dollars × k repetitions × many candidates puts a single outer-loop iteration in the **thousands of dollars**. Two consequences: the AOI pre-filter exists specifically to keep this tractable, and the loop runs on a deliberate schedule rather than continuously. An outer loop that cannot pay for itself is a research project, not a feature.
