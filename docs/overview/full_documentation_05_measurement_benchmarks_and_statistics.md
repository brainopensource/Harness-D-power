# AETHER Full Documentation — Part 5: Measurement Doctrine, Benchmarks & Statistical Protocols

> **Original Source Documents:** [`docs/measurement.md`](../measurement.md), [`docs/rationale/benchmarks/noise-floor.md`](../rationale/benchmarks/noise-floor.md), [`docs/rationale/benchmarks/performance_timers.md`](../rationale/benchmarks/performance_timers.md), and [`docs/benchmarks/`](../benchmarks/).  
> **Purpose:** A complete, condensed specification of AETHER's measurement protocol, instrument blockers (B1–B4), A/A noise floor statistical design, benchmark targets, and pre-publication verification gates.

---

## 1. The Core Measurement Doctrine

The foundational law of AETHER engineering:

> **Instruments are built and verified before the capability they measure.**  
> **Every gate ships with a test proving it can fail.**

A harness capability developed without a verified measurement instrument produces uncalibrated noise. All published claims must be mathematically backed by AETHER's statistical admission pipeline.

---

## 2. Instrument Blockers (B1 – B4)

Before capability numbers can be taken, 4 critical instrument defects must be resolved:

| # | Instrument Defect | Impact on Measurement | Resolution |
| :--- | :--- | :--- | :--- |
| **B1** | Base commits resolved against local directory instead of upstream git repos. | Benchmark runs fail with `fatal: invalid reference:`. | Resolved via manifest-driven upstream repository cache. |
| **B2a/b** | Model endpoint & `ModelProvider` adapter conformance. | Unreachable inference API. | Resolved local OpenAI-compatible endpoint + conformance test. |
| **B3** | Editable install `.pth` leaks live `src/` into worktrees. | Candidate diffs invisible to scoring gates. | Isolated Podman container sandbox + canary test. |
| **B4** | Exit-127 (command not found) scored as test failure. | Instrument errors corrupt failure statistics. | Typed `GateReport` tri-state (`PASSED`, `FAILED`, `NONE`). |

* **Canary Assertion (B3)**: Before the floor run executes, a canary asserting that a **deliberately broken candidate fails evaluation** runs in the test environment. If the broken candidate passes, the floor run is blocked.

---

## 3. The A/A Variance Floor Protocol

The A/A floor executes two identical harness configurations against each other across identical tasks, orders, and seeds to measure baseline instrument noise:

```
+-----------------------------------------------------------------------------------+
|                           A/A FLOOR STATISTICAL ENGINE                            |
+-----------------------------------------------------------------------------------+
|  Statistic            --> Exact McNemar Test (paired binary outcomes)             |
|  Multiple Testing     --> Holm-Bonferroni correction across pre-declared family   |
|  Significance         --> alpha = 0.05 family-wise error rate                     |
|  Sample Size (N)      --> Derived dynamically for Power >= 0.80 (never fixed)    |
|  Primary Outcome      --> Pass@1 on first seeded pass                             |
|  Confidence Intervals --> Seeded bootstrap CI (2000 iterations)                  |
|  Cost Margin          --> Cost per resolved task <= +20% margin                  |
+-----------------------------------------------------------------------------------+
```

### Derived Sample Size Tiers ($N$)
1. **Smoke Tier ($N \ge 50$)**: Evaluated on `DEV` split; used for rapid dev checks; **never admits mechanisms**.
2. **Admission Tier ($N \ge 150$)**: Evaluated on `HOLDOUT` split; admits candidate mechanisms into production topologies.
3. **Publication Tier ($N \ge 300$)**: Evaluated on `SEALED` split; required for public benchmark claims.

---

## 4. Benchmark Targets & Harness Lift

AETHER prioritizes **Harness Lift ($\Delta$)** over absolute scores:
$$\text{Harness Lift } (\Delta) = \text{ResolveRate}(\text{Harness} + \text{Model}) - \text{ResolveRate}(\text{Bare Model})$$

| Suite | Committed Target | Stretch Target | Instrument |
| :--- | :--- | :--- | :--- |
| **SWE-bench Verified** | Lift $\ge +10\%$ (Absolutes $\ge 90\%$) | Absolutes $\ge 96\%$ | B1–B4 |
| **SWE-bench Pro** | Lift $\ge +10\%$ (Absolutes $\ge 60\%$) | Absolutes $\ge 80\%$ | B1–B4 |

### Baseline Arm Requirements (§4.1)
The unassisted baseline arm against which lift is measured must use:
* Single completion via official SWE-bench inference template.
* No execution feedback and no retrieval beyond benchmark context.
* Identical model fingerprint, pinned temperature, and pinned random seed.

---

## 5. TCB Split Isolation

To prevent overfitting, tasks are partitioned into 3 immutable TCB splits:
* **DEV Split**: Used for prompt engineering and iterative node development (unlimited runs).
* **HOLDOUT Split**: Used for formal mechanism admission decisions ($\le 1$ evaluation per mechanism).
* **SEALED Split**: Reserved for final publication runs; every touch is logged and requires $\ge 2$ admitted mechanisms between touches.

---

## 6. Pre-Publication Checklist

Before any benchmark claim or resolve-rate number is published:
1. Instrument blockers B1–B4 are closed and verified.
2. The A/A noise floor run is executed and published.
3. Gate family is declared in TCB YAML before the run; $N$ is derived for power $\ge 0.80$.
4. Resolve-rate lift clears the floor under Holm–Bonferroni correction ($\alpha = 0.05$).
5. Cost per resolved task is non-inferior ($\le +20\%$ margin).
6. Harness Lift ($\Delta$) is reported alongside every absolute score.
7. Run artifact names complete instrument tuple: `sha256(manifest, split, model_fingerprint, topology_hash, container_digests, lockfile_hash, seed)`.
