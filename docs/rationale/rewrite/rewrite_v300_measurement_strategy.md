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

## 1c. The 2026 harness literature — and the one result that argues against part of this plan

Added in the Revision-A competitor review. Four papers were verified against arXiv rather than cited
from memory; two of them bear directly on decisions recorded in this document set, and one of them is
a **measured result that challenges our prefix design**.

| Paper | What it establishes | Bearing on AETHER |
| :--- | :--- | :--- |
| **arXiv 2605.26112** — *From Model Scaling to System Scaling: Scaling the Harness in Agentic AI* (Shangding Gu, UC Berkeley, May 2026) | Once models pass a capability threshold, further gains on long-horizon tasks depend increasingly on **how the system around the model is designed**. Three named bottlenecks: **context governance, trustworthy memory, dynamic skill routing**, plus the orchestration and governance that constrain them | The academic counter-thesis to *"less scaffolding, more model"*. It is the strongest external support for §1's lift framing — and the three bottlenecks it names are three of our own subsystems |
| **arXiv 2602.11988** — *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?* (Gloaguen, Mündler, Müller, Raychev, Vechev — SRI Lab, ETH Zürich) | Repository context files **do not generally improve task success rate** while increasing inference cost by **>20% on average**, across LLMs and agents. LLM-generated files *reduced* success ~3%; developer-written files improved it ~4% | **Directly challenges the always-on instruction layers** in our five-layer prefix. See §1c.1 |
| **arXiv 2604.18071** — *Architectural Design Decisions in AI Agent Harnesses* (Hu Wei, Apr 2026) | Protocol-guided study of **70 public agent-system projects**; five recurring design dimensions: **subagent architecture, context management, tool systems, safety mechanisms, orchestration** | An external taxonomy to check our port catalog against. Our eight core ports cover four of the five; orchestration is deliberately not a port ([A-010](./rewrite_v300_decisoes_adr.md)) |
| **arXiv 2605.18747** — *Code as Agent Harness* (Ning et al., May 2026) | Survey positioning code as the operational substrate for agent reasoning, action and verification. Organized as Harness Interface → Harness Mechanisms → Scaling the Harness | Supports code-mode orchestration ([autonomy §3](./rewrite_v300_autonomia_agi.md)) as a mechanism rather than a local optimization |

### 1c.1 The AGENTS.md result, and why it does not simply invalidate the prefix

This is the most consequential external finding in the set, and it deserves to be stated at full
strength rather than softened: a controlled study found that adding a repository context file **did
not improve resolve rate on average and cost more than 20% extra per task**. That is the opposite of
what almost every practitioner guide asserts, including the field guide this document set draws its
degradation figures from.

Three observations before it is used:

1. **The split matters more than the average.** Human-written files helped (~+4%); LLM-generated files
   hurt (~−3%). The result is therefore better read as *"generated context is negative-value"* than as
   *"context files are useless"* — which is a much more actionable claim, and it lands directly on any
   design where the harness auto-generates its own repo context.
2. **It measures a *static, always-on* context file.** AETHER's static repo layer is a tree-sitter
   skeleton plus a retrieval seed, constructed rather than authored, and the bulk of context arrives
   just-in-time through search and graph expansion. Those are different mechanisms and the result does
   not transfer to them without measurement.
3. **It is exactly the shape of claim §1 says we must re-measure.** It enters the backlog as a
   hypothesis with a named experiment, like every other third-party number here.

| Hypothesis from the literature | Our test |
| :--- | :--- |
| A static repository context file has zero or negative value at >20% cost | Ablate the static repo-context layer on/off at Tier 0; measure resolve rate, cost per resolved task, and cache hit rate separately |
| Generated context is worse than authored context | Two arms: tree-sitter-generated skeleton vs. a hand-authored brief of the same token budget |
| Gains concentrate in context governance, memory and skill routing (2605.26112) | These are M2/M3 subsystems; each already carries an ablation. The paper predicts where the lift comes from — recording the prediction *before* measuring is what makes the result meaningful |

**If arm 1 shows the static layer is negative-value on our suites, that is a finding worth publishing,
not a defect to hide** — and it would simplify the prefix rather than complicate it.

### 1c.2 Provenance corrections carried from the review

Recorded because a citation that drifts is worse than no citation:

- **arXiv 2605.18747 is titled *Code as Agent Harness*, not "Managed Agents 2026".** The tri-layer
  **Brain / Hands / Session Event Log** decomposition and the *Parity / Receptivity / Observability*
  invariants proposed in [the blueprint](./rewrite_v300_blueprint_arquitetura.md) are adopted **on
  their merits as an AETHER proposal**, not on that paper's authority. They should not be attributed
  to it.
- **The "Dumb Zone" figure (attention diffusion concentrated at 40–60% of the window) is unverified.**
  It does not come from 2602.11988. It enters as a hypothesis with the same standing as the ~70%
  cliff, and the compaction-trigger sweep in §1 tests both at once.
- **Latency figures for PyO3 (<50 ns C-ABI), IPC/gRPC (1.5–5.0 ms), CoW clone (<10 ms) and
  pre-warmed pool allocation (0 ms)** are plausible orders of magnitude and are **not our
  measurements**. They are recorded as *design targets with a named benchmark* in
  [runtime decisions](./rewrite_v300_decisoes_runtime.md), never as achieved figures.
- **The competitor corpus contains four teardowns, not six.** `src/codex_cli/` (62 MB) and
  `src/open_code/` (33 MB) are on disk and **unstudied**; OpenHands is not present in the tree. Any
  claim in this set attributed to Codex or OpenCode currently rests on the earlier
  [reference teardowns](./rewrite_v300_reference_teardowns.md), not on a dedicated audit.

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
| **Acceptance threshold** | **α = 0.05 after Holm–Bonferroni**, applied to the family of comparisons in the sweep — not per-test. A raw `p < 0.05` on the fifth of five arms is a 23% family-wise error rate |
| **Effect size reported alongside** | A significant result on a trivial delta is not a reason to ship. Paired difference in resolve rate with its CI, plus cost per resolved task |
| **Null results are recorded** | A mechanism that shows nothing at Tier 0 is recorded as *"no signal at this tier"* — a property of the measurement, not a verdict on the mechanism. It re-enters at Tier 1 |

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

## 5b. Track B cross-check — forks F3 and F4

### 5b.1 Fork F3 — the statistical protocol

Track B requires **p < 0.05 over N ≥ 50 instances, via Student's t or a two-tailed permutation test**,
with cost and latency held flat and `require_tests_unmodified` enforced. That is a stronger admission
rule than most plans carry and the instinct is right.

| | **Track A** | **Track B** |
| :--- | :--- | :--- |
| Floor | **A/A noise floor published before any regression rule is enforced** | Not established |
| Test | **Exact McNemar** (paired binary outcomes) | Student's t / permutation |
| Multiple comparisons | **Holm–Bonferroni across the gate family** | α = 0.05 per test |
| Sample | ≥2 passes per arm, more where budget allows; smoke tier 20–50 tasks | N ≥ 50 instances |
| Reported alongside | Effect size, CI, cost and wall-clock per resolved task, the floor it was measured against | Pass-rate increase, cost, latency |

Two of these are not preferences but correctness issues, offered as such:

- **Resolve/not-resolve is a paired binary outcome.** Student's t assumes continuous, roughly normal
  data; the appropriate test for "same task, two arms, pass or fail" is McNemar's, which conditions on
  the discordant pairs. On paired binary data a t-test is not merely less powerful — its p-value does
  not mean what it appears to mean.
- **α = 0.05 applied per-test across five arms is a ~23% family-wise error rate.** One in four sweeps
  produces a "significant" result by chance. Holm–Bonferroni is the cheap fix.

And the structural one: **without an A/A floor, "significant" has no denominator.** Two identical
configurations differ by some amount — sampling, test ordering, flaky upstream tests — and a paired
comparison cannot distinguish a real effect from that variance until it has been measured. This is
`PLANNING.md` risk **R6**, and it is why §3 produces the floor *before* any must-not-regress rule
exists rather than after.

**Track B's N ≥ 50 is the better half of its protocol and Track A should adopt it explicitly.** §3
says "≥2 passes per arm, more where budget allows", which is vaguer than it should be given that
Tier 0 makes passes free. A stated minimum instance count belongs in the protocol.

### 5b.2 Fork F4 — the targets

| | **Track A** | **Track B** |
| :--- | :--- | :--- |
| SWE-bench Pro | **≥ 80%** | ≥ 60% |
| SWE-bench Verified | **≥ 96%** | ≥ 90% |
| Terminal-Bench | secondary, no number | ≥ 75% |
| Framing | absolute + **lift**, published together, with R1 stated | absolute only |

Per §1 (August 2026, from web research — Track A's own claim, worth independent re-verification):
Pro's leader is ~80.3% with the top cluster at 79–80%; Verified saturates near 96% with the top tier
inside a point. If that holds, Track B's targets land ~20 points below the Pro leader and ~6 below the
Verified frontier, while being framed as *"liderança SOTA incontestável"*. They are consistent with
`PLANNING.md`'s stale snapshot (Pro leader 69.2%) — and even against that snapshot, 60% Pro is below
the leader.

**The argument for Track B's side, stated fairly:** a target you can hit is more useful than a target
you cannot, and Pro ≥80% is a stretch that depends on a model tier nobody has funded (Q3). A plan
whose headline gate is unreachable will either be missed or quietly re-baselined, and both are worse
than an honest 60%.

**The argument against:** the number is a commitment to what "success" means for two years, and 60%
Pro would place the finished product behind the current leader on the primary screen — which is a hard
position to defend commercially regardless of how honestly it was set.

**A reconciliation neither track proposed:** Track A already separates the two claims. *Lift* (≥+10
points, paired, on a fixed model, CI excluding the floor) is achievable at Tier 0 with no budget and
is tier-independent by construction; *absolute* is dominated by model tier and binds only at M4. If
the meeting adopts B's absolute numbers as the **committed** gate and keeps A's as the **stretch**
gate, both readings survive and nothing in the engineering plan changes — because the lift target,
which is what the harness work actually moves, is identical either way.

**Terminal-Bench should be taken from Track B regardless.** §1 lists it as "secondary, for shell and
environment capability" with no number. Given that PTY execution, sandboxing and the perimeter are all
on the roadmap, a stated Terminal-Bench target is a better fit for those mechanisms than SWE-bench is,
and B naming one is an improvement.

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
