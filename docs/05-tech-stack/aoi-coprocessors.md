# **Auxiliary Optimization Intelligence (AOI) Co-processors**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Local Machine Learning Co-processors**
Lightweight non-LLM models operating alongside frontier LLMs for sample-efficient optimization:

* **Trajectory Failure Predictor (CatBoost Classifier)**: Predicts early failure probabilities based on tool call error patterns; halts execution if risk exceeds 0.85 to conserve tokens.
* **Step Process Reward Scorer (XGBoost / LightGBM Regressor)**: Evaluates file diffs, LSP error diagnostic deltas, and test coverage to score steps without invoking LLM judges.
* **Dynamic Context Budget Router**: Evaluates task complexity and context length to route requests to appropriate model tiers.
