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

### The consequence

**At high coding velocity the project stops being engineering-bound almost immediately and becomes
money-and-decision-bound.** M0 and M1a are the two phases that compress most, and they are the two
phases *before* the blocker. The result is that **B2 arrives sooner and hits harder**, not that it
goes away.

This does not change the critical path identified below — it sharpens the deadline on it:

> **Resolve Q3 and Q8 in parallel with M0, not when M1b reaches them.** The failure mode of ignoring
> this is a complete, well-tested walking skeleton with no way to know whether it is any good. That is
> where the predecessor stopped — the difference is that at this velocity you arrive there in days
> rather than months, with the same amount of nothing to report.

Two scheduling consequences follow:

1. **Front-load the compute-bound work.** The upstream repo cache (B1) and the smoke suite can be
   built and dry-run against cassettes during M0/M1a, so that the moment credentials exist, M1b is
   execution rather than construction.
2. **Do not let engineering velocity outrun measurement.** Shipping M2 capability before M1b's noise
   floor produces mechanisms that cannot be evaluated — and the standing rule that no mechanism
   promotes without an ablation then blocks the entire phase retroactively. Capability built ahead of
   its instruments is inventory, not progress.

---

## Dependency graph

```
M0 Contracts ── ports · WorkflowStep types · CI jobs per invariant
   │
   └─> M1a Walking skeleton ── 4-node graph · streaming · TUI MVP
   │        schemas ratified · replay byte-equal · reports honest zero
   │
   │   ┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐
   │   ╎  Q3 model tier · Q8 compute budget  ── COMMERCIAL ╎
   │   ╎  run in parallel with M0. Gates B2, gates M1b.    ╎
   │   └╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┬╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘
   └─────────────────────►│
          └─> M1b Instruments ── B1 B2 B3 B4 · NOISE FLOOR PUBLISHED
                 └─> M2 Capability ── memoization · T1 lift ≥ +10 · T4 cost
                        ├─> M3 Scale ── graph branching · T5 T6 T7 T3
                        │      └─> M4 SOTA ── Pro ≥80 · Verified ≥96
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
| **Q3/Q8 unresolved → B2 blocked → M1b cannot exit** | M1b | Escalate now, in parallel with M0. This is the critical path |
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
