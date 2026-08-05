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

Schemas are **provisionally frozen**, ratified only after M1a round-trips them end to end.

| Exit gate |
| :--- |
| Every invariant I1–I9 maps to a named CI job |
| Reflection contract passes over all ports: async, wire-serializable, no untyped `dict`, no `Grant`, aware datetimes |
| import-linter: layer order, pure domain, pure ports, TCB isolation |
| `docs_budget.py` and `check_links.py` green |
| `docs/STATUS.md` says **"nothing is implemented"** and is true |

---

## M1a — Walking skeleton

**Delivers.** One vertical slice, end to end, with deliberately dumb adapters:
`model → tool → worktree → test → gate → trajectory`, plus the **TUI MVP** and **streaming**
([A-011](./rewrite_v300_decisoes_adr.md) — required here because BoN cache sequencing and the TUI both
depend on it).

Anthropic-native `ModelProvider` with explicit `cache_control` breakpoints. Cassette record/replay.
Cost accounting wired through `ResourceGovernor`.

| Exit gate |
| :--- |
| A trivial task resolves end to end |
| **Schemas ratified** — the freeze becomes real; breaking changes need a version bump |
| Replay byte-equal (T8: 100%) |
| Cost accounting non-zero and correct against provider-reported usage |
| `cache_read_input_tokens` > 0 on a repeated-prefix run — proves caching works at all |
| TUI drives a run and renders the event stream |

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

**Delivers.** Hibernation (`FrozenRunState`, grants re-minted); the workflow DAG with per-node
memoization; sub-agent delegation with scoped registries; skills; MCP; LSP diagnostics; long-term
memory; the private held-out suite.

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

## Dependency graph

```
M0 Contracts
   └─> M1a Walking skeleton  ── schemas ratified · streaming · TUI MVP
          └─> M1b Instruments ── B1 B2 B3 B4 · NOISE FLOOR PUBLISHED
                 └─> M2 Capability ── T1 lift ≥ +10 · T4 cost
                        ├─> M3 Scale ── T5 T6 T7 T3
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
| **Workflow DAG has no reference implementation** | M3 | Original to AETHER — higher risk than the ported components. Prototype early, keep the escape hatch to a linear pipeline |
