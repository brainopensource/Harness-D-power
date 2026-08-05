---
status: historical
updated: 2026-07-29
---
# **Recursive Harness Self-Improvement (RHI) Outer Loop**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

The outer loop optimizes harness scaffolding under held-out validation. It is **scheduled, not continuous**.

## **The Trusted Computing Base (TCB)**

To prevent optimizer gaming (editing graders/evaluators to force high scores), the TCB is immutable:

* **Non-writable surface**: Policy engine, autonomy config, evaluators, gate definitions, benchmark tasks, deployment gates, secret handling, sandbox boundaries. Enforced via `MutationProposal.targets` path allowlist, read-only branches, and CI diff checks.
* **Mutable surface**: Prompts, retrieval/compaction parameters, tool descriptions, routing heuristics, non-Control adapters.

## **Cycle**

1. **Trajectory Ingestion** — Log traces, tool outputs, and step scores via OTel GenAI conventions to an append-only store ([Microkernel & Bus](../02-architecture/microkernel-and-bus.md)).
2. **Mutation Proposal** — Meta-Improver proposes mutable surface changes; AOI ranks candidates before full evaluation.
3. **Verification** — Execute Tiers 0–3 verification gates.
4. **Deployment** — Staged for human sign-off; self-deployment is prohibited.

## **Verification Gates**

* **Tier 0 — A/A Noise Floor**: Run unmodified harness twice to establish stochastic noise floor. Candidates must exceed this delta.
* **Tier 1 — Screening**: Smoke test against held-out split (prefer SWE-bench Verified / Multi-SWE-bench over Lite).
* **Tier 2 — Commit-Replay Private Split**: Harvested real historical repository commits posed as tasks with original diffs and tests as ground truth.
* **Tier 3 — Paired Regression & Statistics**: Paired evaluation ($k \ge 3$ runs/task, fixed seeds), reporting variance and multiple-comparison corrected significance.

## **Economic Tiers (A/B/C)**

Mutation search costs thousands of dollars per iteration. The loop is structured by economic return (see [STATUS.md](../STATUS.md), [ADR-0022](../08-decisions/0022-rhi-economic-refounding.md)):

| Tier | Activity | Cost Profile | Schedule |
| :--- | :--- | :--- | :--- |
| **A** | **Trajectory Ingestion & Measurement**: A/A noise floor, paired stats, cost/latency/cache tracking, failure patterns. | Near-zero (piggybacks on standard runs) | **Always on** |
| **B** | **Distillation & Dataset Export**: Export admitted trajectories to SFT/DPO datasets; human-authored prompt/policy updates. | Bounded & predictable | **Scheduled** (phase close) |
| **C** | **Mutation Search**: Meta-Improver proposals, AOI ranking, Tiers 0–3 gate execution. | High ($k\text{k}+/iter$) | **Dormant** (explicit manual trigger only) |

* Port reference: `ports/meta_improver.py` governed by [ADR-0023](../08-decisions/0023-port-rent-rule.md).
* Implements `docs/rationale/reviews/agi_evolution_path.md` and `critical_gaps_analysis.md`.
