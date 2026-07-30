---
status: normative
updated: 2026-07-29
---

# **Auxiliary Optimization Intelligence (AOI) Co-processors**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Lightweight non-LLM models that make the harness sample-efficient. **Advisory only**: they rank and filter; they never admit or reject. Hard gates remain deterministic.

## **Models**

* **Trajectory Failure Predictor (CatBoost)** — estimates the probability a run fails or enters an unrecoverable loop, from early tool-call sequences and error patterns.
* **Step Process Reward Scorer (XGBoost / LightGBM)** — scores steps from diffs, diagnostic deltas, and test metrics without an expensive LLM judge.
* **Dynamic Context Budget Router** — routes across local, mid-tier, and frontier models by task complexity and context length.

## **Every Prediction Is Calibrated, Never a Bare Float**

The contract lives in **`src/sagiha/domain/work.py`** (`Prediction`: `value`, `confidence`,
`calibrated`, `shadow_mode` — all required, no defaults; the port surface is
`src/sagiha/ports/advisory.py`). Uncalibrated predictions may never gate; shadow mode means
predict-and-log, never act.

A scalar carries no way to express uncertainty, and therefore no basis for deciding whether it may be acted upon.

## **Three Binding Constraints**

Each closes a specific way that learned advisory models go wrong in practice.

### 1. Shadow mode before gating

Every model ships predicting-and-logging, and is promoted to acting only when a reliability diagram and Brier score on held-out runs justify it. **No fixed halt threshold is specified anywhere in this tree**, deliberately: a threshold chosen before calibration data exists is not a decision rule, it is a guess with a decimal point. The number comes from the reliability diagram or it does not exist.

### 2. Exploration against self-confirmation

A failure predictor that halts runs it expects to fail **destroys its own training signal**: halted runs never produce success labels, so its false positives are never observed and the model confirms itself indefinitely. This is the standard selection-bias trap in learned early stopping.

* A **fixed exploration fraction always runs to completion**, regardless of predicted risk.
* Censored outcomes are **never trained as negatives**.
* Where halting occurs, training corrects the selection with inverse-propensity weighting.

### 3. Out-of-distribution fallback

On unfamiliar repository layouts, the model abstains and control reverts to deterministic policy. Degradation is always toward the safe default — an unavailable or low-confidence model must never stall a run.

## **The Cold Start**

AOI needs trajectories it does not have on day one. The bootstrap is the **deterministic escalation ladder**: hand-written routing policy runs first, and its decisions plus their outcomes become the labelled dataset the learned router later trains on. Hand-written policy first, learned policy second, is the only ordering that resolves this.

## **Interaction With the Outer Loop**

AOI ranks candidate mutations so that only promising ones reach expensive held-out evaluation — which is what keeps an outer-loop iteration affordable. Evaluation results feed back into training, with a portion of data **never** used to train models that influence the loop, preserving evaluation integrity.

## **Observability**

Every prediction, promotion, and update is logged to the Trajectory Store, so a model's real-world hit rate is auditable after the fact rather than assumed from its validation score.
