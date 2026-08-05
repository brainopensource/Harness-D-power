---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Measurement Strategy

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Satisfies **D-17** of the [Phase-0 charter](../reference/PLANNING.md) and RFP
[§1.1](../reviews/review_project_rewrite_v300.md) ("facts over opinions"). Supersedes PLANNING.md §1,
whose leaderboard figures are stale.

---

## 0. The rule this document exists to enforce

**Instruments are built and verified before the capability they measure.**

The predecessor shipped four gates hardcoded to `return True`, dead cost accounting, and stubs that
fabricated success. Every measurement taken over those instruments was uninterpretable and had to be
discarded — `docs/rationale/benchmarks/s1_before_baseline.md` records the state, and
`s1_honest_baseline.md` records the fix: the measured pass rate went to **0.0%**, and *the drop was
the fix*.

A gate that cannot fail is a bug, and it is the most expensive class of bug this project can have,
because it is retroactive: it does not break the current run, it invalidates every number ever taken
over it.

**Every gate ships with a test proving it can fail.** No exceptions, no "obviously it works".

---

## 1. Re-baselined landscape (August 2026)

PLANNING.md §1 records SWE-bench Pro's leader at 69.2% (Opus 4.8), dated 2026-08-03. That figure is
already stale.

| Benchmark | State, Aug 2026 | Role for AETHER |
| :--- | :--- | :--- |
| **SWE-bench Pro** | Leader ~**80.3%** (Claude Mythos 5); Claude Fable 5 ~80%; Claude Opus 5 ~79.2% | **Primary headline.** Target: **≥ 80%** |
| **SWE-bench Verified** | Saturating; frontier ~**96%**, with the top tier clustered within ~1 point | Secondary. Target: **≥ 96%**. Below that we are *losing* points a bare model call already has |
| **SWE-bench Lite** | Small, cheap, heavily contaminated by age | Fast CI smoke signal only. **Never a headline claim** |
| **Terminal-Bench** | Active | Secondary, for shell and environment capability |
| **Aider Polyglot** | Active | Secondary, for multi-language edit accuracy |

Three facts about these numbers that shape the entire protocol:

1. **Almost nothing is independently verified.** Of roughly a hundred models on public leaderboards,
   approximately **one** carries an independent verification badge. Everything else is vendor
   self-reported — including, unless we do the work, ours.
2. **The pools are not comparable.** Public, held-out, and commercial task sets are different pools,
   and scaffold, tool budget, retry policy, and token budget all move pass rates. Two numbers from
   two vendors are frequently not measuring the same thing.
3. **Roughly 30% of the public Pro tasks were estimated broken** in an OpenAI audit published July
   2026. A public-set number carries that error bar whether or not it is stated.

### The targets, and the honest framing

The user's decision is **real SOTA**: Pro ≥ 80%, Verified ≥ 96%. Recorded plainly, with the risk
stated plainly:

> **PLANNING.md R1 — model tier dominates absolute score.** Scaffold-attributable lift is documented
> at roughly 10–20 points on a fixed model. That is the ceiling of what harness engineering itself can
> buy. Whichever model we are permitted to call sets the absolute number; our work moves it by up to
> twenty points.

So both numbers get published, and neither substitutes for the other:

- **Absolute** (Pro ≥80%, Verified ≥96%) — the headline. Reported with the model, the effort setting,
  the tool budget, the retry policy, and the pool.
- **Lift** — resolve-rate delta versus a single-shot baseline **on the identical model**, paired, with
  a confidence interval that excludes the A/A noise floor, plus cost and wall-clock per resolved task.

Lift is the claim that survives a model swap, a leaderboard reshuffle, and a hostile diligence review.
Absolute is the claim that sells. **Sell the lift, report the absolute** — and never report one
without the other.

The comparison set that actually matters for a scaffold is other **open scaffolds at the same model
tier** — OpenHands, SWE-agent, Aider, Confucius Code Agent (74.6% on Verified with Claude 4 Sonnet,
the strongest open result at its tier). A vendor's number for its own model with its own private
harness is not a peer comparison.

---

## 2. The blockers — what must be fixed before any number exists

`docs/rationale/benchmarks/noise-floor.md` still reads **"Status: still not populated."** The A/A run
attempted 2026-08-01 failed on all 30 tasks × 2 passes. The printed `mean_delta: 0.000` and
`Pass rate: 0.0%` are quoted in that file *only so nobody mistakes them for a result*.

| # | Blocker | Fix |
| :--- | :--- | :--- |
| **B1** | The runner executes `git worktree add <base_commit>` against the **local** repository, while SWE-bench base commits live in **twelve upstream repositories that were never cloned** → `fatal: invalid reference:` on every task | An upstream repo cache: clone (mirror, shallow-by-commit) each task repo once, keyed by URL, pinned by SHA, reused across runs and across CI. This is the first real component built in M1b |
| **B2** | No model endpoint and no API keys → nothing to measure even with a working runner | Provider credentials and a documented cost budget. A **commercial decision**, flagged as open in [the ADRs](./rewrite_v300_decisoes_adr.md) (Q8) |
| **B3** | The editable install's `.pth` leaked the live `src/` into every isolated worktree → candidate diffs invisible to the gates scoring them (`s4-harvest-findings.md` D3) | No editable install inside an evaluation container; environment built from the task's own dependency spec; **canary test asserting a deliberately broken candidate fails** |
| **B4** | pytest-uncollectable files in `failing_test_cmd` (D1); exit-127 "command not found" scored as a test failure rather than an instrument error (D2) | Typed distinction between *test failed* and *instrument failed*. An instrument failure is never a data point |

**B3 and B4 are the same class of bug as the hardcoded gates:** the instrument produced numbers while
not measuring what it claimed. That is why they are blockers rather than backlog items.

Consequence today: `search.enabled` and `retrieval.enabled` both ship `false`, because no measurement
ever justified turning them on. AETHER inherits that discipline — a mechanism ships on when a number
says so.

---

## 3. The A/A noise floor

Two identical configurations run against each other. Any observed difference is variance: LLM
sampling, test-order effects, timing, flaky tests in the task repositories.

**Nothing may be called an improvement until it exceeds this floor.** Without it, the project accepts
random variation as progress — PLANNING.md risk **R6**, and the reason the floor is produced *before*
any "must not regress" rule is enforced rather than after.

| Element | Choice |
| :--- | :--- |
| Design | Paired — same tasks, same order, same seeds where seeds exist |
| Runs | ≥ 2 passes per arm; more where budget allows |
| Statistic | **Exact McNemar** for paired binary outcomes |
| Multiple comparisons | **Holm–Bonferroni** across the gate family |
| Intervals | Seeded bootstrap CI |
| Implementation | `e0/statistics.py` — pure stdlib, pinned JSON fixtures. **Ports verbatim** |

Published to `docs/rationale/benchmarks/noise-floor.md` as the M1b exit gate. Until that file
contains a real number, **the project reports no results at all** — which is the current, correct
state.

---

## 4. Contamination control

Public benchmark solutions are in training data. A number taken purely on public tasks is partly a
memorization measurement, and nothing in the harness can tell the two apart.

**Target T3: a private held-out suite, with the public-vs-private gap reported alongside every public
number. A gap above 10 points means we are measuring memorization.**

Construction: commit-replay over repositories that are not public, or whose relevant commits postdate
the model's cutoff. Requirements — never published, never committed to this repository, regenerated as
models advance, and **licensed for the purpose**. Which repository is an open commercial decision (Q6).

The gap itself is the deliverable. A project that reports only public numbers has not measured
contamination; it has declined to.

---

## 5. Gate design

| Property | Rule |
| :--- | :--- |
| Tri-state | `True` / `False` / **`None`**. `None` means *not measured* — never silently `True` |
| Falsifiability | **Every gate has a test proving it can fail.** Non-negotiable |
| Hard vs. proxy | Hard gates **admit**. Learned scorers **rank** and may never admit or override a failure (I9, type-level separation) |
| `tests_unmodified` | Hard gate. Tests injected read-only from the base commit |
| `PASS_TO_PASS` | Regression check — previously-passing tests must still pass. `planning_final_sprint_rev2.md` records this as gap **G2** |
| Attribution | Deterministic failure-attribution order, so the same failure is always attributed to the same gate |
| Instrument failures | Typed and excluded from the denominator. Never scored as a task failure |

That last row is worth stating twice: an instrument failure counted as a task failure understates the
system and, worse, understates it *unpredictably* — which makes every delta noisier and the noise
floor wider.

---

## 6. CI tiering

A full benchmark run per commit is unusable on cost and latency (PLANNING.md **R7**).

| Tier | Trigger | Content | Gate |
| :--- | :--- | :--- | :--- |
| **Replay** | Every PR | Cassette record/replay, zero network | Byte-equal step sequences (T8: 100%) |
| **Contracts** | Every PR | Port shape, adapter conformance, import contracts, loud-stub check | All green |
| **Smoke** | Every PR | 20–50 curated tasks | No regression beyond the noise floor |
| **Full** | Nightly / pre-release | Full Verified and Pro suites | Recorded, not gating |
| **Ablation** | On demand | One mechanism on/off, paired | CI excludes the noise floor |
| **Profiling** | Nightly | RSS, idle CPU, index time, **cache hit rate** | T6 / T7 ceilings; hit-rate floor |

**Deterministic replay is what makes the PR tier possible at all.** Digest-keyed cassettes with
byte-equal step sequences and zero network give a fast, free, fully deterministic signal on every
commit — and no reference harness in the set has it, which makes it a genuine differentiator as well
as a convenience.

The profiling row carries the cache-hit-rate floor from
[context & cache §1.6](./rewrite_v300_contexto_memoria.md), because a cache regression is a pure cost
regression that produces no test failure and no behavioral change. Without a floor it is invisible
until the invoice arrives.

---

## 7. What gets published, and how

Every reported number carries, without exception:

- Model id, effort setting, thinking configuration
- Tool budget, retry policy, max steps
- Suite id and commit-pinned task list
- Pool (public / held-out / private)
- Cost and wall-clock per resolved task
- The A/A noise floor it is measured against
- Confidence interval and the test used

A number without these is not reproducible, and an unreproducible number is worth nothing in
diligence — including our own. `docs/STATUS.md` makes **zero** claims unsupported by a line-level read
of the code; on day one of AETHER it says *nothing is implemented*, and that is the correct content.

---

## 8. Sequence

| Phase | Instrument work | Exit |
| :--- | :--- | :--- |
| **M1a** | Cassette replay; trajectory store; cost accounting wired end to end | Replay byte-equal |
| **M1b** | **B1–B4 fixed**; gate-can-fail tests; smoke suite in CI; **A/A noise floor published** | The gate the predecessor never passed |
| **M2** | Ablation harness; paired comparison tooling; cache-hit-rate floor | Lift ≥ +10 pts, CI excluding the floor |
| **M3** | Profiling gates (T6, T7); private held-out suite (T3) | Footprint and contamination measured |
| **M4** | Full Pro and Verified runs; independent reproducibility package | Pro ≥ 80%, Verified ≥ 96% |
| **M5** | RHI acceptance statistics | T9: >0 accepted, zero TCB modifications |

**Instruments before capability, in every phase.** The measurement layer for a phase ships before the
capability that phase exists to add — which is the single procedural rule that separates this attempt
from the last one.
