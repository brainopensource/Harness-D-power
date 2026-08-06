---
status: normative
updated: 2026-08-05
---

# Measurement Protocol

**The governing rule, and the reason this document exists before any capability document:**

> Instruments are built and verified before the capability they measure.
> Every gate ships with a test proving it can fail.

The prototype phase sequenced measurement last. Capability shipped without proof of value,
and **every number taken had to be discarded**. This document is the mechanism that prevents
a repeat; [`concepts/`](./concepts/README.md) is the evidence that it happened.

---

## 1. The current state, stated plainly

**AETHER has never produced a valid benchmark number.** Not a low one — none.

On day one that is the correct content for a results section, and it stays until the A/A
floor exists. A project that reports zero honestly is in a better position than one
reporting a comfortable estimate over a broken instrument, because the second has to discard
the estimate *and* every decision made on it.

---

## 2. Instrument blockers

Four, all reproduced. They are numbered as they were found; the numbering is preserved so
the historical record stays greppable.

| # | Defect | Effect | When fixed |
| :--- | :--- | :--- | :--- |
| **B1** | The runner resolves task base commits against the **local** repository; SWE-bench base commits live in upstream repositories that were never cloned | Every task fails `fatal: invalid reference:`. This is why the 2026-08-01 A/A run produced nothing | **Now.** Standalone utility, no AETHER dependency. It unblocks every number |
| **B2a** | No model endpoint | Nothing to run | **Resolved.** A local OpenAI-compatible endpoint is sufficient for the floor, the baseline and every ablation |
| **B2b** | No `ModelProvider` adapter behind it | The endpoint is unreachable from the harness | **Open.** `src/aether/` is empty, so this gate has never run. Closes with the adapter and its conformance suite |
| **B3** | An editable install's `.pth` leaks live `src/` into every supposedly-isolated worktree | **Candidate diffs invisible to the gates scoring them.** This one produced numbers | With the evaluation container. Ships with a **canary asserting a deliberately broken candidate fails** |
| **B4** | Exit-127 (command not found) scored as a test failure | Instrument failures enter the denominator | **Before the A/A floor.** It is a pure domain type — a tri-state `GateReport` and a result-mapping rule |

**B1 is manifest-driven, not a repo list.** The cache clones the distinct repositories named by
the **pinned task manifest**, per suite. Verified spans 12; Pro spans materially more, and Pro
is the primary screen — a cache hard-coded to 12 defers the primary battlefield by a milestone.
The repo set is derived at pin time and verified there.

**B2 was one blocker doing two jobs.** "Resolved" was true of the endpoint and false of the
adapter, and the roadmap listed it as pending while this document called it closed. Splitting
it makes both claims checkable. B2b's gate is `None` — *unmeasured* — until an adapter exists.

**B4 precedes the floor.** If exit-127 and uncollectable-test events are still scored as
failures when the floor is taken, the floor measures instrument noise **plus instrument error**
and every later admission inherits a polluted denominator. B4 is cheap and has no dependency on
anything downstream, so nothing is bought by deferring it.

**B3 and B4 are the same class of bug as a hard-coded gate:** the instrument produced numbers
while not measuring what it claimed. An instrument failure is never a data point.

**B3 may follow the floor, conditionally.** In an A/A run both arms carry the leak identically,
so the variance estimate may survive — *if* the leak is arm-symmetric and does not interact with
task identity. That is an assumption about an instrument, and assumptions about instruments get
canaries here: **the B3 canary runs in the floor environment before the floor run.** If a
deliberately broken candidate passes there, the floor is blocked on B3.

**This is not "fix everything before writing code."** B1 starts now; B3 arrives with the
component it isolates. Two independent reviewers made the stronger reading, and it is not
implementable.

---

## 3. The A/A variance floor

Two identical configurations run against each other. Any observed difference is variance —
sampling, test order, timing, flaky tests in the task repositories.

| Element | Choice |
| :--- | :--- |
| Design | Paired: same tasks, same order, same seeds where seeds exist |
| Statistic | **Exact McNemar** — the outcome is paired and binary |
| Multiple comparisons | **Holm–Bonferroni** across a pre-declared gate family |
| Threshold | **α = 0.05 family-wise**, not per-test |
| Sample | **Derived** — see below. Tier floors: 50 smoke · 150 admission · 300 publication |
| Primary outcome | **pass@1 on the first seeded pass** |
| Intervals | Seeded bootstrap CI, 2000 iterations |
| Effect size | Paired difference in resolve rate with CI, plus cost per resolved task |
| Implementation | `measurement/statistics.py` — pure stdlib, pinned JSON fixtures |

**Why not a t-test.** Resolve/not-resolve is paired binary. Student's t assumes continuous,
roughly normal data; on paired binary outcomes its p-value does not mean what it appears to
mean. And α applied per-test across five arms is a **~23% family-wise error rate** — five
arms, `1 − 0.95⁵`.

**Why N is derived and not fixed at 50.** At N = 50, exact McNemar detects a true +10-point
lift — the committed target — in **12–32% of cases**, and at Holm's most conservative step in a
five-hypothesis family (α = 0.01) in **4–11%**. A protocol that discards nine true improvements
in ten is not conservative; it is an instrument that cannot see the thing it was built to
measure, and its modal output — *"nothing clears the floor"* — is indistinguishable from a
harness that does not work.

**N is therefore computed per family** from a pre-registered discordance assumption (taken from
this floor run), the minimal effect of interest, target power ≥ 0.80, and the Holm-adjusted α at
that hypothesis's rank. The tier names denote a role and a floor, never a value:
**smoke (≥50, DEV, never admits) · admission (≥150, HOLDOUT) · publication (≥300, SEALED)**.
Full protocol and the power table: [ADR-0003](./decisions/0003-statistical-admission-protocol.md).

**Passes do not aggregate.** Primary outcome is pass@1 on the first seeded pass; further passes
estimate within-arm flakiness and are reported separately. Merging passes after seeing results
is the p-hacking surface a diligence review probes first.

**The family is declared mechanically.** A committed YAML in the TCB, merged before any arm
runs; `statistics.py` refuses to compute corrected p-values for an undeclared family.

**Why the floor comes first.** Without it, "significant" has no denominator — and now also no
sample size, since the floor's discordance estimate is the input to every later N.

**Null results are recorded as "no signal at this tier"** — a property of the measurement,
not a verdict on the mechanism. They re-enter at a higher tier.

---

## 4. Targets

**Lift is the committed target.** Lift ≥ **+10 points**: the resolve-rate delta between a
bare model call and the same model inside AETHER, on identical tasks, same model both sides.
It is what the harness work actually moves, and it survives a model swap, a leaderboard
reshuffle and a diligence review.

**Absolute targets are provisional** (ADR-0004) — the leaderboard re-baselining behind them
has not been independently verified.

| Suite | Committed | Stretch | Instrument |
| :--- | :--- | :--- | :--- |
| SWE-bench Verified | ≥ 90% | ≥ 96% | B1–B4 |
| SWE-bench Pro | ≥ 60% | ≥ 80% | B1–B4 |
| Terminal-Bench | *aspirational* | — | **None. Not a gate** |

**Terminal-Bench carries no instrument** — no blocker, no task, no milestone anywhere in this
tree. A number we cannot measure cannot function as a commitment (§6), so it is recorded as an
aspiration until an instrument track exists, at which point it is re-adopted as a gate.

**An absolute number is never published without its lift.**

### 4.1 The baseline is part of the instrument

Lift is only as defensible as the arm it is measured against, and "a bare model call" admits a
family of baselines. A weak one manufactures the lift. Pre-registered, therefore:

- **Baseline arm**: one completion · official SWE-bench inference template, **template hash
  recorded** · no execution feedback · no retrieval beyond benchmark-provided context ·
  temperature and seed pinned · **identical model fingerprint to the harness arm**.
- **Harness arm**: AETHER at a hash-pinned config and topology.
- Both arms over the same manifest, paired by task, outcome pass@1.
- **Reported together**: lift with CI · both absolutes · cost per resolved task per arm ·
  token totals · instrument-error rate per arm.

### 4.2 Splits, and why they are pinned

Overfitting the benchmark is the standard attack on any leaderboard claim, and iteration speed
makes it easy to do accidentally. Every suite is partitioned in the manifest, and **the split
assignment is TCB** so it cannot drift per run:

| Split | Use | Constraint |
| :--- | :--- | :--- |
| **DEV** | Ablations, loop engineering | Burn freely |
| **HOLDOUT** | Admission decisions | ≤ 1 evaluation per candidate mechanism |
| **SEALED** | Publication runs | Every touch logged; ≥ 2 mechanisms admitted between touches |

### 4.3 Contamination and task validity

- **Task-validity canary, per task, bidirectional**: a task enters a manifest only if the **gold
  patch passes and the empty patch fails on our instrument**. Roughly 30% of public Pro tasks
  were estimated broken in a mid-2026 audit, so this is not a formality.
- **Exclusions are published** with a reason. Silent exclusion is the overfitting vector.
- **Perturbed-task indicator**: a small set of semantically equivalent, surface-rewritten issues.
  Frontier models have seen these repositories in training; for *lift* that largely cancels
  (both arms share the model), but for absolutes the original-vs-perturbed delta is reported as
  a contamination indicator.

---

## 5. Gate design

- Tri-state `GateReport`: `True` / `False` / **`None`**. `None` means *unmeasured* and never
  silently passes.
- Every gate ships with a test proving it **can fail**. A gate that cannot fail is the most
  expensive bug this project can have.
- **Hard gates admit; learned proxies rank** (I9). A learned scorer may order candidates and
  may never admit one.
- A gate keyed to a path must select something. A contract that matches no file forbids
  nothing and passes green — `tests/unit/test_path_constant_drift.py` enforces this, and
  `tests/unit/test_docs_gates.py` does the same for the two documentation gates.
- **The I10 cache metric is harness-side prefix stability** — the byte-identical-prefix rate
  over a fixed recorded replay — not a provider-reported hit rate. `cache_control` semantics
  are provider-specific and the B2 local endpoint may expose none, so a gate keyed to a
  provider metric would be unmeasurable on the reference instrument. Provider-reported hit rate
  is a secondary metric where it exists.

---

## 6. What a claim needs before it is published

1. The instrument's blockers are closed for the thing being claimed.
2. The A/A floor exists and is published.
3. The gate family was **declared before any arm ran**, and N was **derived for ≥ 0.80 power**
   at the declared minimal effect.
4. The effect clears the floor with its CI, under Holm–Bonferroni across that family.
5. **Cost per resolved task** is reported alongside, and is non-inferior within the declared
   margin.
6. Lift is reported alongside any absolute.
7. The run names its instrument: manifest hash, split, model fingerprint, topology hash,
   container digests, lockfile hash, seed.

**The task manifest and its split assignment are TCB artifacts** — immutable once pinned;
a change is a new manifest with a new hash, never an edit. So are the gate-family declarations.
The predecessor's `s0-core.json` was documented as committed and pinned while the directory was
empty and untracked, which made its `bench-aa` job a permanent silent no-op. A benchmark
definition that can be edited by the thing being benchmarked is not a definition.

**A number we did not measure on our own instruments never appears in a result, a claim, or
a regression gate.** It may set a default, motivate an ablation, or bound a design — nothing
more. Third-party figures enter as hypotheses with a named experiment, never as evidence.

**The competitive claim needs its own instrument.** The mission is to beat other harnesses, and
the rule above forbids citing their published numbers as evidence — so the claim is
unsubstantiable until a **comparative-lift rig** exists: a `HarnessUnderTest` seam running
(harness, model, manifest) arms — bare model, AETHER, OpenHands — through **our** evaluator.
Same model, same manifest, same judge is the only apples-to-apples comparison available in this
space. It is measurement tooling, not a port (`TASK-015`), and it is scheduled after the floor
and before any public claim.
