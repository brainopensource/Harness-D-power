# **Running Benchmarks & Evaluating Trajectories**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Evaluation Pipeline**
1. **Public Screening Runs**: Execute harness test suites against public SWE-bench Lite task subsets.
2. **Private Verification Splits**: Run candidate harness mutations against private synthetic codebases to evaluate generalization and prevent reward hacking.
3. **Trajectory & PRM Analysis**: Inspect OTel-instrumented step-wise PRM scores and trajectory logs stored in SQLite/WAL.
