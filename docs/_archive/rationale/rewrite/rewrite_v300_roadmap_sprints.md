---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Phased Roadmap

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§5.5](../reviews/review_project_rewrite_v300.md).

---

## 0. Three sequencing rules

**Instruments before capability.** The measurement layer for a phase ships before the capability that
phase exists to add. This is the one procedural rule that separates this attempt from the predecessor,
whose entire measurement history had to be discarded.

**Slices before components.** Every phase ships something end to end. No phase ships a component whose
value cannot yet be measured.

**Triggers before calendars.** `research`-tier work is gated on an empirical condition, never a date.
A learned component starved of data underperforms the heuristic it replaced.

No mechanism promotes to production without an ablation showing a real gain in resolve rate or a
substantial reduction in latency or cost (RFP §1.1). Phase durations are deliberately absent — the
exit gates are the schedule.

---

## M0 — Contracts

**Delivers.** `src/aether/` skeleton: `domain/`, `ports/` (the eight core boundaries), event catalog,
`.importlinter` contracts, the conformance suite, and a named CI job per invariant I1–I9 — **even
where the job is not yet implemented**.

**Plus `WorkflowStep[In, Out]` — the node and socket types only.** No memoization, no partial
re-execution, no graph editor. Just the typed boundary. See [A-024](./rewrite_v300_decisoes_adr.md)
for why this moved forward from M3: the node abstraction is nearly free to declare and expensive to
retrofit, and it is the one component in the system with no reference implementation, so it earns
early exposure in its most trivial form.

Schemas are **provisionally frozen**, ratified only after M1a round-trips them end to end.

| Exit gate |
| :--- |
| Every invariant I1–I9 maps to a named CI job |
| Reflection contract passes over all ports: async, wire-serializable, no untyped `dict`, no `Grant`, aware datetimes |
| import-linter: layer order, pure domain, pure ports, TCB isolation |
| `WorkflowStep` typed and conformance-tested; **no execution engine yet** |
| `docs_budget.py` and `check_links.py` green |
| `docs/STATUS.md` says **"nothing is implemented"** and is true |

---

## M1a — Walking skeleton

**Delivers.** One vertical slice, end to end, with deliberately dumb adapters:
`model → tool → worktree → test → gate → trajectory`, plus the **TUI MVP** and **streaming**
([A-011](./rewrite_v300_decisoes_adr.md) — required here because BoN cache sequencing and the TUI both
depend on it).

**The vertical slice is expressed as a four-node graph**, not a hand-written pipeline:

```
  retrieve ──► generate ──► apply ──► evaluate
```

A linear chain is a DAG with no branches. Running it through `WorkflowStep` from the first working
run means the abstraction is exercised by every subsequent phase instead of being introduced late over
code that already assumes a straight line. **No memoization in this phase** — nodes execute
unconditionally; the graph is a structure, not yet an optimizer.

Anthropic-native `ModelProvider` with explicit `cache_control` breakpoints. Cassette record/replay.
Cost accounting wired through `ResourceGovernor`.

**Measurement plumbing lands here; measurement results do not.** The smoke runner, cost accounting,
and replay all work at the end of M1a — and the runner honestly reports **zero**, because the
instruments that make a number interpretable are M1b. Shipping the plumbing early is what makes M1b a
one-week phase; reporting a number early is the predecessor's exact failure.

| Exit gate |
| :--- |
| A trivial task resolves end to end **through the graph executor** |
| **Schemas ratified** — the freeze becomes real; breaking changes need a version bump |
| Replay byte-equal (T8: 100%) |
| Cost accounting non-zero and correct against provider-reported usage |
| `cache_read_input_tokens` > 0 on a repeated-prefix run — proves caching works at all |
| TUI drives a run and renders the event stream; every surface tagged `LIVE`/`MOCK` honestly |

---

## M1b — Instruments

**The phase the predecessor never passed.** No capability work.

**Delivers.** The four blockers from [measurement strategy §2](./rewrite_v300_measurement_strategy.md):

| # | Work |
| :--- | :--- |
| **B1** | Upstream repo cache — clone and pin each SWE-bench task repository, keyed by URL, reused across runs and CI. Fixes `fatal: invalid reference:` on all 30 tasks |
| **B2** | Model endpoint and credentials. **Blocked on Q3 and Q8 — an external decision, not engineering** |
| **B3** | No editable install in the evaluation container; environment from the task's dependency spec; **canary test asserting a deliberately broken candidate fails** |
| **B4** | Typed distinction between *test failed* and *instrument failed*; instrument failures excluded from the denominator |

Plus: a can-fail test for every gate; `PASS_TO_PASS` regression checking (gap G2); the 20–50 task
smoke suite in CI.

| Exit gate |
| :--- |
| **A/A noise floor published** in `docs/rationale/benchmarks/noise-floor.md` with real numbers |
| Every gate has a test proving it can fail |
| Canary proves the gate can see the candidate |
| Smoke suite green in CI on every PR |
| A single-shot baseline measured — the denominator for every lift claim that follows |

**Nothing downstream is trustworthy until this gate is green.** A capability measured before M1b is a
capability measured on an unverified instrument, which is the predecessor's exact failure.

---

## M2 — Capability

**Delivers.** The mechanisms with the strongest evidence behind them, each shipped with its ablation.

| Mechanism | Rationale |
| :--- | :--- |
| **Retrieval + repo map + localization** | The largest lever. Agentless reaches ~45% on Verified with no agent loop at all; their entire edge is picking the right five files |
| **In-loop repair** | The second-largest. Gate verdict re-enters as a tool-result-shaped message, never a second system prompt |
| **Anchored edits** with `expected_occurrences` + anchor-sequence matching; tree-sitter validation | [A-013](./rewrite_v300_decisoes_adr.md), [A-014](./rewrite_v300_decisoes_adr.md) |
| **Container perimeter** + egress allowlist + TaintGate | Autonomy requires containment |
| **Exchange-granular compaction** | Long tasks exceed the window |
| **Cache economics** | Hit-rate metric with a CI floor |
| **Per-node memoization**, keyed by input digest | Now it pays for itself: an ablation re-runs one node's subtree instead of the pipeline. The economics of every row above depend on it |

| Exit gate |
| :--- |
| **T1: lift ≥ +10 points** vs. single-shot baseline, same model, paired, **CI excluding the noise floor** |
| Each mechanism above has a recorded ablation |
| First Pro baseline recorded (not yet targeted) |
| Cache hit rate above its floor |
| T4: cost per resolved task ≥30% better than baseline |

**Ablation gates in this phase:** retrieval on/off · repair on/off · compaction strategy · disposition
ladder per rung · anchor matching strict vs. tolerant.

---

## M3 — Scale and autonomy

**Delivers.** Hibernation (`FrozenRunState`, grants re-minted); **graph branching and fan-out** — the
point at which the DAG stops being a straight line and carries parallel candidates and conditional
paths; sub-agent delegation with scoped registries; skills and the curator; background review on the
parent's warm prefix; MCP; LSP diagnostics; long-term memory; the private held-out suite.

| Exit gate |
| :--- |
| **T5**: ≥8h unattended, resumable across process death |
| **T6**: <300 MB peak RSS, <1% idle CPU |
| **T7**: 1M-LOC repository indexed <10 min; incremental re-index <200 ms |
| **T3**: private held-out suite live; public↔private gap **<10 points** |
| Profiling gates in nightly CI |

**Risk checkpoint.** T6 and T7 are where [A-002](./rewrite_v300_decisoes_runtime.md)'s reversal
triggers RT-1/RT-2/RT-3 fire if they are going to. A Rust indexer sidecar, if justified, is scoped
here — behind the existing `Indexer` port, changing no caller.

---

## M4 — SOTA push

**Delivers.** Best-of-N with verifier-guided selection (cache-sequenced fan-out); hierarchical
localization; SBFL; model routing per role; ablation-gated Architect/Editor split; prompt tuning
against the measured baseline.

| Exit gate |
| :--- |
| **SWE-bench Pro ≥ 80%** ([A-006](./rewrite_v300_decisoes_adr.md)) |
| **SWE-bench Verified ≥ 96%** |
| Lift published alongside, with CI and noise floor |
| Independently reproducible: pinned suite, documented config, published cost |
| Public↔private gap still <10 points |

**Stated risk (PLANNING.md R1).** The absolute component of these targets is dominated by model tier.
Scaffold-attributable lift tops out around 10–20 points on a fixed model. If Q3 constrains the tier,
the absolute target moves with it and **the lift target does not** — which is why both are published
and why lift is the claim that survives.

---

## M5 — Meta-loop (RHI)

**Delivers.** Offline optimization over prompts, skills, tool schemas, and routing from the trajectory
corpus. DSPy/GEPA-class optimizer. Acceptance statistics; rejection log.

| Exit gate |
| :--- |
| **T9**: >0 accepted mutations beating the noise floor |
| **Zero TCB modifications admitted** |
| Rejection log published alongside the acceptance log |

The second row is the real test. An RHI that improves the score by weakening the evaluator has not
improved anything, and [I8](./rewrite_v300_blueprint_arquitetura.md) exists precisely because that is
the loop's most efficient available strategy.

---

## Velocity — where acceleration applies, and where it does not

Phase durations stay absent: **the exit gates are the schedule.** But *effort* distribution is
planning-relevant, and under AI-assisted development it is heavily skewed — which changes what the
binding constraint is.

**Much of the available speedup is already banked.** The twelve documents in this set removed the
design ambiguity that is where AI-assisted coding actually stalls. What remains compresses well on one
axis and not at all on the others.

| Axis | Compresses? | Why |
| :--- | :--- | :--- |
| Writing code against a settled contract | **Strongly** | Ports, adapters, tests, the graph executor, the TUI. Specified in advance; mechanical to produce |
| Integration debugging | Partly | Still bounded by how fast a failing run reproduces |
| **Benchmark execution** | **No** | A Pro or Verified run is API round-trips and container time. Money and wall-clock, not typing |
| **Ablation cycles** | **No** | Each is a paired run against the noise floor. Serial and compute-bound — which is exactly why M2 buys memoization |
| **Q3 / Q8 — model tier and compute budget** | **No** | Organizational. No engineering velocity touches it |

### The consequence — and why the commercial blocker is not one

At high coding velocity a project like this normally becomes money-and-decision-bound the moment the
engineering compresses. **The Tier 0 strategy removes that.**

Running on a **locally hosted open-weight model** ([measurement §1b](./rewrite_v300_measurement_strategy.md))
covers the A/A noise floor, the single-shot baseline, **T1 scaffold lift**, every ablation, and the
head-to-head against real competitor harnesses — all at zero marginal cost and unlimited runtime.
Lift is a *paired delta on a fixed model*, so it is tier-independent by construction; it does not need
a frontier model, it needs a **constant** one.

**Q3 and Q8 therefore move off the critical path and onto the M4 boundary.** M0 through M3 need no
budget approval, no vendor relationship, and no external decision. The one thing the budget buys is
the absolute headline number, and by then it is purchasing a claim rather than unblocking work.

What replaces the old blocker as the thing to watch:

1. **Do not let engineering velocity outrun measurement.** Shipping M2 capability before M1b's noise
   floor produces mechanisms that cannot be evaluated — and the standing rule that no mechanism
   promotes without an ablation then blocks the phase retroactively. Capability built ahead of its
   instruments is inventory, not progress. **M1b remains a hard serialization point**; it is simply no
   longer gated on anyone's signature.
2. **Signal compression on a weak model is the real Tier 0 risk.** If the floor resolves 2% and we
   resolve 4%, the delta is genuine but the interval is wide, and some mechanisms will show nothing
   until a stronger tier. Mitigation: run the strongest model the hardware supports, run more passes
   (free), and record a null result as a property of *the measurement* rather than of the mechanism.
3. **Front-load the slow parts.** The upstream repo cache (B1) and the smoke suite can be built and
   dry-run against cassettes during M0/M1a, so M1b is execution rather than construction.

---

## Revision-A amendments — proposed phase placement

From the competitor review ([synthesis](../../competitors_research/tech_lead_A/rewrite_v300_synthesis_amendments.md))
and the candidate records **A-026…A-034**. Ordered by the rule that governs everything else here:
cheap-now-expensive-later first, because deferring those is itself a decision.

| Phase | Proposed additions | Why here |
| :--- | :--- | :--- |
| **M0** | `RunOutcome` + `PauseKind` (A-026) · `replayed` flag (A-027) · tool `contract_version` (A-028) · `RunProfile` type (A-031) · composite-checkpoint type decision · one shared token estimator · stable wire strings on telemetry enums (A-034) · checkpoint-store layout decision · **CI ceiling on single-module line count** | All are domain types or layout decisions: near-free before the schema freeze, breaking changes after. A-028 additionally **cannot be retrofitted onto historical measurements** |
| **M1a** | `reserve`/`commit`/`release` on the governor (A-030) · task-typed turn caps · `assert_parity()` in the assembler and replay path (I10) · **a timer on worktree creation** · hard deadlines on every read that can block in native code | Budget correctness is cheap while the governor is three functions. The worktree timer is one instrument on an existing operation and decides whether §8b.4 is worth building at all |
| **M1b** | The **scaffolding-thesis ablation arm** · tool contract version in the manifest · noise floor established at a **representative trajectory length**, not a short one | The last is new and load-bearing: gate and judge models degrade with transcript length like generators do, so a floor measured on short runs understates the variance of the runs we care about |
| **M2** | Completion cascade + anti-ratchet (A-029) · prefire compaction (A-033) · **static repo-context layer as the first ablation** · rules-vs-skills + path scoping (A-031) · MMR diversity re-rank · deferred tool schemas as an ablation arm · auto-denial limits (A-032) | The repo-context ablation is first because arXiv 2602.11988 puts the burden of proof on us; the rest each ship with their ablation as usual |
| **M3** | Fail-closed drive state on thaw · atomic freeze + sidecar recovery · per-role scratch · CoW worktrees **if the M1a timer justified it** · PTY adapter · hunk authorship attribution · human-editable state index · OTel export adapter (A-034) | All are autonomy- or scale-shaped and land with hibernation and the private suite |
| **M5** | Objective metric ≠ acceptance metric · the constraint set as hard gates · rejection log published alongside acceptance | Recorded now so the meta-loop is not designed against the metric it optimizes — the failure the reference implementation shipped |

**One new risk row**, added to the table below in spirit: *"the verification gate ratchets and the loop
never terminates."* Mitigated by A-029's anti-ratchet property. It is a **T5-blocking failure**, not a
quality issue, and neither the progress signature nor the step cap prevents it.

---

## Track B cross-check — a calendar, and fork F2

### 5c.1 Adopt: an indicative calendar alongside the exit gates

This document refuses durations on the grounds that the exit gates are the schedule. That is
intellectually correct and operationally unhelpful when someone has to plan a quarter, and Track B is
right to carry a Gantt.

The two are reconcilable, and the reconciliation is worth stating: **the gate decides when a phase
ends; the calendar decides when to worry.** An indicative duration is a tripwire, not a commitment —
if a phase runs 50% over its indicative window, that is a signal to re-scope, not a reason to skip its
gate.

| Phase | Indicative window | Tripwire at | What overrun most likely means |
| :--- | :--- | :--- | :--- |
| **M0** Contracts | ~1–2 weeks | 3 weeks | The port surface is being designed against imagined adapters (A-010) |
| **M1a** Walking skeleton | ~2–3 weeks | 5 weeks | Adapters are not deliberately dumb enough; scope crept into M2 |
| **M1b** Instruments | ~1–2 weeks | 4 weeks | B1's upstream repo cache is harder than it looks — the most likely real overrun |
| **M2** Capability | ~4–6 weeks | 10 weeks | Ablation cycles are serial and compute-bound; this is the phase memoization exists to pay down |
| **M3** Scale | ~4–6 weeks | — | T6/T7 are where RT-1/2/3 fire if they fire |
| **M4** SOTA push | gated on Q3/Q8 | — | Commercial, not engineering |
| **M5** Meta-loop | — | — | Trigger-gated on corpus size |

**These are planning figures, not commitments**, and they carry the same standing as every other
third-party number in this set: useful for a calendar, never a gate. The exit gates in the phase
tables above remain the only thing that ends a phase.

Track B's sprints map onto these cleanly enough to compare: B's Sprint 0 ≈ M0 + parts of M1a + the
Rust core; B's Sprints 1–3 ≈ M2; B's Sprint 4 ≈ M3 + M5. **B has no M1b.** That is fork F2.

### 5c.2 Fork F2 — instruments before capability, or build first

| | **Track A** | **Track B** |
| :--- | :--- | :--- |
| First phase | M0 contracts, then M1a walking skeleton reporting an **honest zero** | Sprint 0 builds the hexagonal foundation **and** the Rust core |
| Instrument phase | **M1b is a hard serialization point.** B1/B3/B4 fixed; A/A floor published; canary proves the gate can see the candidate | None |
| First number | After M1b, against a published floor | Sprint 0 acceptance gate (worktree <10 ms), Sprint 2 gate (cache hit >92%) |
| Baseline | Measured at M1b, or reported as zero | Stated as ~68% Verified / ~38% Pro / ~50% cache hit |

**The argument for Track B's side, stated fairly:** an instrument phase that ships no capability is
hard to justify to a stakeholder, it delays every downstream signal, and a team that builds nothing
for two weeks loses momentum. B's plan produces observable progress from week one.

**The argument against, stated concretely rather than as principle.** Three defects are documented and
reproduced in this repository, and none is fixed by Sprint 0:

- **B1** — the runner runs `git worktree add <base_commit>` against the *local* repo while SWE-bench
  base commits live in twelve never-cloned upstream repositories. This is why the 2026-08-01 A/A run
  failed on **all 30 tasks** and `noise-floor.md` still reads *"still not populated"*.
- **B3** — the editable install's `.pth` leaks the live `src/` into every isolated worktree, so
  **candidate diffs are invisible to the gates scoring them**. This one produced numbers.
- **B4** — exit-127 "command not found" scored as a test failure rather than an instrument error, so
  instrument failures enter the denominator and widen every interval unpredictably.

The asymmetry that makes this fork not a simple speed-versus-rigour trade: a number taken over B3 is
not a *slower path to the same place*, it is work that has to be discarded — and discarded
retroactively, along with every decision made on it. This project has already paid that bill once;
`s1_honest_baseline.md` records the correction that took the measured pass rate to 0.0%, and *the drop
was the fix*.

**A reconciliation worth putting to the meeting.** M1b is described here as a phase, which makes it
look like a two-week stop. Most of it is not: the upstream repo cache (B1) and the smoke suite can be
built and dry-run against cassettes **during M0/M1a**, in parallel with capability work, so M1b
becomes execution rather than construction. That is already written into the velocity section above —
"front-load the slow parts" — and it is the version of this plan that answers B's momentum objection
without giving up the serialization point.

### 5c.3 What F2 is *not* — a misreading this document has already caused twice

Two independent reviewers read the F2 fork and concluded that Track A proposes *"a hard stop to fix
B1/B3/B4 before starting Sprint 0."* **It does not, and that reading is not implementable.** Recording
the correction here, because when two readers make the same error the wording is the defect.

**What Track A actually claims:** no *capability number* is trusted until the A/A floor is published.
Code starts at M0. The walking skeleton ships at M1a, **before** M1b, and deliberately reports an
honest zero. The serialization point is on **interpreting measurements**, not on writing software.

**Why the stronger reading is not implementable.** The three blockers have different earliest-possible
dates, and treating them as one gate produces a plan that cannot start:

| Blocker | Earliest it can be fixed | Why |
| :--- | :--- | :--- |
| **B1** — upstream repo cache | **Immediately**, before any AETHER code | It is a standalone clone-and-pin utility with no dependency on the harness. This is the one to front-load |
| **B3** — no editable install in the evaluation container; canary proves the gate sees the candidate | **After the evaluation container exists** | You cannot fix the isolation of a container you have not built |
| **B4** — typed *test failed* vs *instrument failed* | **After the gate exists** | The distinction lives in the evaluator's return type |

So the sequencing rule is narrower and sharper than "instruments first": **B1 now; B3 and B4 arrive
with the components they isolate; no number is published before the floor.** A plan that blocks all
construction on B3 is waiting for a component to exist before building it.

**Why this matters for v300 specifically.** When the prototype ends and final development starts, the
temptation will be to read "instruments before capability" as permission to spend a sprint building
measurement scaffolding with nothing to measure. That is the opposite failure from the predecessor's
and it wastes the same time. The rule earns its place only in its precise form.

**One thing to take from Track B unconditionally:** its per-sprint acceptance gates are concrete and
checkable (*"0 ms de espera no alocador de containers e 100% de bloqueio em testes de invasão
TaintGate"*). Several of Track A's exit gates are prose. Converting each to a named CI job or a named
measurement, in the style B uses, would be an improvement independent of how F2 lands.

---

## Dependency graph

```
M0 Contracts ── ports · WorkflowStep types · CI jobs per invariant
   │
   └─> M1a Walking skeleton ── 4-node graph · streaming · TUI MVP
   │        schemas ratified · replay byte-equal · reports honest zero
   │
   │        ── TIER 0: local open-weight model · free · unlimited ──
   │
   └─> M1b Instruments ── B1 B3 B4 · NOISE FLOOR PUBLISHED
   │        four-arm head-to-head: floor · AETHER · Hermes · +1
   │
   └─> M2 Capability ── memoization · T1 lift ≥ +10 · AETHER ≥ Hermes
          │
          ├─> M3 Scale ── graph branching · T5 T6 T7 T3
          │      │        ── TIER 1: OpenRouter, stratified samples ──
          │      │
          │      └─> M4 SOTA ── TIER 2 spot checks · Pro ≥80 · Verified ≥96
          │             │      ┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐
          │             │      ╎ Q3 tier · Q8 budget ── COMMERCIAL  ╎
          │             │◄╌╌╌╌╌╎ needed HERE only, for the absolute ╎
          │             │      └╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘
          │             └─> M5 RHI ── T9
          └─> (Phase 4) Conductor — gated on L1–L3 measured
```

**M1b is the single serialization point.** Every downstream claim depends on it, and B2 depends on an
external commercial decision (Q3, Q8) rather than on engineering. That is the schedule's critical
path, and it should be resolved in parallel with M0 rather than discovered at M1b.

---

## Standing rules

| Rule | Enforcement |
| :--- | :--- |
| No mechanism ships without an ablation clearing the noise floor | Ablation harness; recorded in `docs/rationale/benchmarks/` |
| Every gate has a test proving it can fail | CI |
| Every port arrives with its first adapter and conformance test | Conformance meta-test ([A-010](./rewrite_v300_decisoes_adr.md)) |
| Stubs raise; they never return a plausible value | `check_loud_stubs.py` |
| `docs/STATUS.md` makes zero claims unsupported by a line-level code read | Review |
| No surface claims `LIVE` without a backing capability | `LIVE_VS_MOCK.md` |
| A PR adding N normative words deletes N elsewhere | `docs_budget.py` ratchet |
| TCB paths are unmodifiable by the agent | CI `tcb-check` |
| Contested mechanisms ship **off**, behind a config flag, until a number says otherwise | Config default |

---

## Highest-risk items

| Risk | Phase | Mitigation |
| :--- | :--- | :--- |
| ~~Q3/Q8 unresolved blocks M1b~~ | ~~M1b~~ | **Retired.** Tier 0 (local model) covers the noise floor, the baseline, T1 lift, every ablation, and the head-to-head. The commercial decision binds only at M4 |
| **Weak-model signal compression** | M1b–M2 | The Tier 0 replacement risk: small resolve rates widen every interval. Strongest local model available, more passes (free), and a null result recorded as a property of the measurement |
| **Competitor arms drift** | M1b onward | Hermes and the other reference harnesses are pinned by commit in the benchmark definition, like the tasks. An unpinned competitor arm is not a baseline |
| Model tier caps the absolute target (R1) | M4 | Contract on lift; state R1 in writing before committing to absolutes |
| Benchmark saturation or migration (R2) | M4 | `Evaluator` stays a port — a new suite is a new adapter, not a rewrite |
| Contamination inflates the number (R3) | M3 | T3 private suite, gap published with every public number |
| Premature Rust rewrite (R4) | M3 | Profile first; port only measured hot paths behind an existing port |
| Measuring on lying instruments (R5) | M1b | The whole phase |
| Chasing noise (R6) | M2 | Noise floor before any "must not regress" rule |
| Full benchmark per commit (R7) | M2 | Smoke tier per PR; full suite nightly |
| Research components on a calendar (R8) | M4–M5 | Empirical triggers only |
| Scope sprawl from reference mining (R9) | All | The **reject** column in [reference teardowns](./rewrite_v300_reference_teardowns.md) is binding |
| Doc drift (R10) | All | One owner per topic; code wins for contracts; budget ratchet |
| **Workflow DAG has no reference implementation** | M0–M3 | Original to AETHER. **Mitigated by moving it forward, not back** ([A-024](./rewrite_v300_decisoes_adr.md)): types in M0, a 4-node linear graph in M1a, memoization in M2, branching in M3. Each step is small and load-bearing; the escape hatch to a plain pipeline stays open until M2 |
| **Velocity outruns measurement** | M1a→M2 | Capability built ahead of its instruments cannot be promoted and becomes inventory. M1b is a hard serialization point, not a suggestion |
