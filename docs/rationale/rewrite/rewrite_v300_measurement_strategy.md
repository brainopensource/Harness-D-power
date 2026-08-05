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

### Third-party field numbers are hypotheses, not baselines

Several design documents in this set cite practitioner and community figures — the ~70% context cliff,
the ~150-instruction ceiling, blast-radius success rates, session-degradation thresholds. They are
useful and they are load-bearing for *design*, but they are governed by one rule:

**A number we did not measure on our own instruments never appears in a result, a claim, or a
regression gate.** It may set a default, motivate an ablation, or bound a design — nothing more. Each
one enters the backlog as a hypothesis with a named experiment.

| Field claim | Our test |
| :--- | :--- |
| Quality drops non-linearly near ~70% of context budget | Sweep the compaction trigger; measure resolve rate and cost per resolved task at each setting |
| Adherence degrades past ~150 always-on rules | Ablate system-prompt and skill-corpus size against instruction-following on a fixed suite |
| Success falls from ~85% (1–3 files) to ~40% (8+) | Stratify our own resolve rate by files-touched; it is already recoverable from trajectories |
| Repeated failures dilute task intent | Ablate intent re-injection on/off across repair attempts |
| Judge models degrade on long transcripts | Vary judge context budget in Best-of-N; measure selection accuracy against gate outcomes |

The last row is the one most likely to be quietly wrong in a scaffold: a degraded judge silently
selects worse candidates, and the failure looks like the *generator* underperforming.

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

## 1b. The benchmark ladder — free first, premium last

The absolute targets in §1 need a frontier model. Almost everything else does not, and building the
measurement practice on a **free local model** removes the commercial decision from the critical path
entirely.

### Tier 0 — free, local, head-to-head

Run on a locally hosted open-weight model (Ollama on local GPU). Unlimited runtime, zero marginal
cost, many passes affordable.

**The design that makes this powerful is running the competitors on the same model.** Not comparing
against their published numbers — *running their harness, on our model, on our tasks, on our
hardware*:

| Arm | What it establishes |
| :--- | :--- |
| **Pure LLM, single shot** | The **floor**. Everything a harness adds must beat this |
| **AETHER** | Us |
| **Hermes** on the same model | The **target**. A real, reproducible scaffold ceiling |
| Aider · OpenHands · SWE-agent on the same model | Additional reference points at the same tier |

This is strictly stronger evidence than the literature comparison §1 describes. A published leaderboard
number comes from a different model, a different tool budget, a different retry policy, and a task pool
with an estimated 30% defect rate — three of those confounds vanish when every arm runs the same model
on the same tasks on the same machine. **The gap between "pure LLM" and "Hermes" is the scaffold's
contribution, isolated.** Our job is to close it and then exceed it.

**Practical constraint, stated because it shapes the design:** harnesses that speak an
OpenAI-compatible endpoint (Hermes, Aider, OpenHands, SWE-agent) can be pointed at a local server.
Vendor CLIs generally cannot — they authenticate to their own provider and are interactive
subscription products, not programmable endpoints. **Claude Code and Gemini CLI therefore cannot be
part of Tier 0**; they appear at Tier 2, on their own terms.

**What Tier 0 fully validates:** every instrument, the A/A noise floor, the single-shot baseline,
**T1 scaffold lift** (a paired delta on a fixed model — tier-independent by construction), every
ablation, and the head-to-head standing versus real competitors.

**What Tier 0 cannot give:** an absolute SOTA number. A weak model also compresses the signal — if the
floor resolves 2% and we resolve 4%, the delta is real but the interval is wide. Use the strongest
model the hardware runs, expect some mechanisms to show no signal until a stronger model is used, and
record that as a property of the measurement rather than of the mechanism.

### Tier 1 — sampled API

Once Tier 0 shows AETHER at or above the Hermes arm, add an OpenRouter adapter and run **stratified
samples**, not full suites: enough tasks for an intermediate signal at a fraction of a full run's
cost. This is where mechanisms that were signal-less on a weak model get a second look.

### Tier 2 — premium spot checks

Small, isolated, deliberately non-statistical. Take a handful of concrete tasks, run them through a
vendor CLI, and compare the artifact — the actual `.py` output — against ours on quality, wall-clock,
cost, and tokens/second. These are **qualitative calibration**, never a headline: the sample is small,
the harness is theirs, and the pool is not controlled. They answer "are we close to premium?", not
"what is our score".

### Only then: the full absolute run

SWE-bench Pro at frontier tier ([A-006](./rewrite_v300_decisoes_adr.md)) — the one step that genuinely
needs the budget decision, and by then it is buying a headline number rather than unblocking work.

**Sequencing consequence.** The commercial decision (Q3/Q8) moves off the critical path and onto the
M4 boundary. Tiers 0 and 1 need no approval, no budget, and no vendor relationship.

---

## 2. The blockers — what must be fixed before any number exists

`docs/rationale/benchmarks/noise-floor.md` still reads **"Status: still not populated."** The A/A run
attempted 2026-08-01 failed on all 30 tasks × 2 passes. The printed `mean_delta: 0.000` and
`Pass rate: 0.0%` are quoted in that file *only so nobody mistakes them for a result*.

| # | Blocker | Fix |
| :--- | :--- | :--- |
| **B1** | The runner executes `git worktree add <base_commit>` against the **local** repository, while SWE-bench base commits live in **twelve upstream repositories that were never cloned** → `fatal: invalid reference:` on every task | An upstream repo cache: clone (mirror, shallow-by-commit) each task repo once, keyed by URL, pinned by SHA, reused across runs and across CI. This is the first real component built in M1b |
| **B2** | ~~No model endpoint~~ → **resolved by Tier 0** (§1b): a local OpenAI-compatible server on local GPU. Free, unlimited, sufficient for the noise floor, the baseline, T1 lift, and every ablation | Point the `ModelProvider` adapter at the local endpoint. The API budget decision (Q3/Q8) moves to the M4 boundary and no longer gates M1b |
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

**Pre-MVP posture: CI stays minimal.** While the MVP is still being designed there are no deploys and
no production surface, so CI carries only the cheap correctness gates — lint, type check, import
contracts, port conformance, loud-stub check, replay, and the docs frontmatter/link checks. **Heavy
gates arrive with the capability they guard**: the container perimeter suite when the perimeter
exists, coverage thresholds when there is code worth covering, benchmark tiers when the instruments
are honest. Adding a gate before its subject exists produces either a permanently skipped job or a
permanently red one, and both teach the team to ignore CI — which is the same failure as a gate that
cannot fail, arriving from the opposite direction.

What must **never** be dropped in the name of minimalism: the loud-stub check, the port conformance
suite, and replay determinism. Those three are what prevent the predecessor's failure mode, and they
cost seconds.

| Tier | Trigger | Content | Gate |
| :--- | :--- | :--- | :--- |
| **Replay** | Every PR | Cassette record/replay, zero network | Byte-equal step sequences (T8: 100%) |
| **Contracts** | Every PR | Port shape, adapter conformance, import contracts, loud-stub check | All green |
| **Smoke** | Every PR | 20–50 curated tasks | No regression beyond the noise floor |
| **Full** | Nightly / pre-release | Full Verified and Pro suites | Recorded, not gating |
| **Ablation** | On demand | One mechanism on/off, paired | CI excludes the noise floor |
| **Profiling** | Nightly | RSS, idle CPU, index time, **cache hit rate** | T6 / T7 ceilings; hit-rate floor |

**One canonical trajectory format, three consumers.** `src/hermes_agent` composes its evaluation
stack around a single format: a SWE runner over local / Docker / Modal environments emits it, a batch
runner consumes it, and a trajectory compressor post-processes it for training. AETHER's runner,
harvester, reporter and SFT/DPO exporter should share one format for the same reason — a separate
"eval format" and "training format" guarantees they drift, and the export pipeline then re-derives
what the runner already knew.

**Compression for training data has different invariants than compression for runtime context.** The
same reference protects the first turns and the last N, compresses only the middle starting from the
second tool response, and — the non-obvious constraint — **keeps the remaining tool calls intact so
the model continues working after the summary**. A training corpus compressed with runtime rules
teaches the model to stop after a summary, which is precisely the behavior a long-horizon agent must
not learn. Two compressors, one format.

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
| **M1b** | **B1–B4 fixed** on **Tier 0**; gate-can-fail tests; smoke suite in CI; **A/A noise floor published**; the four-arm head-to-head standing up (floor · AETHER · Hermes · one more) | The gate the predecessor never passed — reached with zero budget |
| **M2** | Ablation harness; paired comparison tooling; cache-hit-rate floor. All on Tier 0 | Lift ≥ +10 pts, CI excluding the floor; **AETHER ≥ Hermes on the same model** |
| **M3** | Profiling gates (T6, T7); private held-out suite (T3); Tier 1 OpenRouter adapter + stratified samples | Footprint and contamination measured; mechanisms re-checked at a stronger tier |
| **M4** | Tier 2 spot checks vs vendor CLIs; full Pro and Verified runs; independent reproducibility package | Pro ≥ 80%, Verified ≥ 96% |
| **M5** | RHI acceptance statistics | T9: >0 accepted, zero TCB modifications |

**Instruments before capability, in every phase.** The measurement layer for a phase ships before the
capability that phase exists to add — which is the single procedural rule that separates this attempt
from the last one.
