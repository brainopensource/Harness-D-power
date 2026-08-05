---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Auxiliary Optimization Intelligence (AOI) Co-processors**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

Lightweight non-LLM models for sample efficiency. **Advisory only**: they rank and filter, but hard gates remain deterministic.

## **Models**

* **Trajectory Failure Predictor (CatBoost)** — Predicts run failure/looping from early tool sequences and error patterns.
* **Step Process Reward Scorer (XGBoost / LightGBM)** — Scores steps from diffs, LSP diagnostic deltas, and test metrics without LLM calls.
* **Dynamic Context Budget Router** — Routes across model tiers based on task complexity and context length.

## **Prediction Schema & Calibration**

Domain contract defined in `src/sagiha/domain/work.py` (`Prediction`: `value`, `confidence`, `calibrated`, `shadow_mode`; port in `src/sagiha/ports/advisory.py`).

* Uncalibrated predictions cannot gate execution.
* Shadow mode (`predict-and-log`) is mandatory prior to activation.

## **Binding Constraints**

1. **Shadow Mode & Calibration** — Models require reliability diagrams and Brier score validation on held-out trajectories before promotion.
2. **Exploration vs. Selection Bias** — Fixed exploration fraction runs to completion regardless of predicted risk; censored runs are never trained as negative labels; uses inverse-propensity weighting on halted runs.
3. **OOD Fallback** — Reverts control to deterministic policies when confidence drops or repository structures are unfamiliar.

## **Cold-Start Strategy**

Initial execution relies on deterministic escalation ladders. Recorded trajectories form the training corpus for learned AOI models.

## **Outer Loop Integration & Observability**

* Pre-filters and ranks candidate mutations to minimize outer-loop evaluation costs.
* Predictions, model promotions, and performance metrics are logged to `TrajectoryStore` for auditing.
