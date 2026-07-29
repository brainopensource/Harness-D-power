# **Recursive Harness Self-Improvement (RHI) Outer Loop**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Outer-Loop Self-Evolution Framework**
The outer loop operates continuously to optimize system prompts, context compaction policies, and tool scaffolding:

1. **Trajectory Ingestion**: Execution traces, command outputs, and PRM step scores are logged to an append-only OTel Trajectory Store.
2. **Mutation Proposal**: Meta-Improver agent reviews trajectory failure patterns and proposes targeted harness code or prompt mutations.
3. **Multi-Tier Verification Gates**:
   * **Tier 1 (Public Screening):** Rapid evaluation against public SWE-bench Lite subsets.
   * **Tier 2 (Private Synthetic Split):** Evaluation against private synthetic codebases with injected logic flaws to prevent reward hacking.
   * **Tier 3 (Regression Gate):** Requires zero LSP errors, clean linter reports, and higher task pass rates without token inflation.
4. **Deployment**: Validated harness mutations automatically commit to production baseline.
