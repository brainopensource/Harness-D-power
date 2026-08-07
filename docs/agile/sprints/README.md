---
status: rationale
updated: 2026-08-06
---

# Sprint Map

**What is planned, what is only shaped, and why the line falls where it does.**

Sprints allocate people to tasks. They do not decide when a phase ends — [`../milestones.md`](../milestones.md) does that, and its gates are `normative` while this file is not. A sprint boundary is an administrative convenience; a gate is a commitment.

---

## The planning horizon ends at the A/A floor

**Sprints 01–05 are planned in full. M2-abl onward is shape only, deliberately.**

The original rule was "01–03 planned, 04 onward shape only," and its reasoning still binds — it
is reproduced below and unchanged. Sprints 04 and 05 were written anyway, on a narrow exception:
**neither is sized by inference wall-clock.** Sprint 04 is instrument repair plus the floor run
itself; Sprint 05 is a refactor that produces no number and calls no model in anger. The three
reasons below are all about *ablation* wall-clock and derived N, and neither sprint has either.
M2-abl remains unsized, and writing it today would still be a forecast wearing a task list.

Three reasons, each traceable to a ratified decision:

1. **[`roadmap.md`](../roadmap.md) leaves M2-abl unsized**, because an ablation's wall-clock is dominated by inference across N paired tasks and nobody has measured per-task wall-clock yet. Publishing a duration for it would be an unmeasured number used as a commitment — [ADR-0009](../../decisions/0009-gates-are-the-schedule.md) forbids exactly that.
2. **The floor sets N.** Under [ADR-0003](../../decisions/0003-statistical-admission-protocol.md) rev. 2, sample size is *derived* from the discordance the floor measures. Until the floor runs, nobody knows whether an admission run is 150 tasks or 400 — so nobody knows how many sprints M2 is.
3. **Three ADRs have reversal conditions that change what later sprints contain.** If the repair ablation loses, `TASK-023` is deleted rather than extended. If the generated-context layer loses, [ADR-0010](../../decisions/0010-context-prefix-layers.md) says it is **deleted, not demoted**. If a timer crosses an RT threshold, [ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md) promotes that one component to a sidecar. Writing those sprints now means writing them twice.

Writing `sprint-06.md` today is not planning. It is a forecast wearing a task list.

---

## Planned in full

| Sprint | Goal | Milestones / blockers closed | Tasks |
| :--- | :--- | :--- | :--- |
| [**01**](./sprint-01.md) | Enforcement migration, pure domain, kernel choke point, ports behind mocks, repo cache | M0 · B1 · B2a · B4 | `000` `001` `002` `003` `004` `005` `006` `010` `013` |
| [**02**](./sprint-02.md) | Real adapters, walking skeleton, the two F1 timers | M1a · B2b | `011` `017` `018` `019` `020` `021` `022` `026` `034` |
| [**03**](./sprint-03.md) | Repair edge, evaluation container, manifests, **the floor run** | M1a+ · B3 · **A/A floor** | `012` `014` `015` `016` `023` |
| **03.5** *(unplanned; retro-recorded in [`backlog.md`](../backlog.md) and [`STATUS.md`](../../STATUS.md))* | Inner-loop context lift: edit-format seam, node registry by kind, repair re-reading, architect/reflector | M1a++ | `037`–`041` |
| [**04**](./sprint-04.md) | **Instrument restoration** and the floor run Sprint 3 deferred | M1a++R · **A/A floor** | `049` `049b` `050` `051` `052` |
| [**05**](./sprint-05.md) | The capability layer: `agency/`, `ModelNode`, `RunConfig` | M1b | `053`–`058` |

**Sprint 3.5 happened without a sprint file.** It is listed here because it is the one sprint
that changed measurement semantics, and it is the one with no plan document — which is how its
instrument debt went unrecorded until an audit found it. The debt is Sprint 4's Tasks 1–3.

**Sprint-03 is the one that matters.** Until its floor run lands a real number in [`docs/rationale/benchmarks/noise-floor.md`](../../rationale/benchmarks/README.md), [ADR-0002](../../decisions/0002-no-number-before-the-floor.md) means the project publishes **no capability number at all**. Everything before it is instrument construction; everything after it is measurable.

---

## Shape only — content set at planning time, after the floor

These are not sprint files and should not become sprint files until the sprint before them starts. The **order** is fixed by the roadmap DAG; the **contents and count** are not.

| Phase | Shape | Tasks in scope | Unknown until |
| :--- | :--- | :--- | :--- |
| **M2-eng** | Per-node memoization | `032` | — (this one is sized: 5d) |
| **M2-abl** | Three ablations, repair first | `023` `025` `031` `024` | **The floor.** Per-task wall-clock × derived N sets the sprint count |
| **M3** | Branching, fan-out, statistical admission | `035` `033` `012` `034` | Whether M2's ablations admit or delete their mechanisms |
| **M4+** | Meta-loop, workflow self-redesign, self-modification | — | The autonomy ladder in [ADR-0014](../../decisions/0014-workflow-topology-is-data.md) and [ADR-0017](../../decisions/0017-subagent-capability-attenuation.md); gates drafted in [`../../fixes/proposal_agile_benchmarkings_refinement.md`](../../fixes/proposal_agile_benchmarkings_refinement.md) §3 but **not ratified as milestones** |

**M2-abl's sprint count is a genuine unknown, not a gap in this document.** Naming a number would be the defect, not the fix.

---

## Two tracks, run in parallel

[`roadmap.md`](../roadmap.md) splits work into **Track 1 — Execution Architecture** and **Track 2 — Measurement & Instrumentation**, and the split is load-bearing rather than cosmetic: Track 2's B1 has no dependency on anything in Track 1, and the whole point of [ADR-0002](../../decisions/0002-no-number-before-the-floor.md) is that instruments are built *alongside* capability rather than after it.

| Sprint | Track 1 — architecture | Track 2 — instrument |
| :--- | :--- | :--- |
| **01** | `000` `001` `002` `003` `004` `005` `006` (~3d) | `010` `013` (~3d) |
| **02** | `017` `018` `020` `022` `026` `034` | `011` `019` `021` |
| **03** | `023` | `012` `014` `015` `016` + the floor run |

**Serially, Sprint-01's tripwires sum to ~7 days against a 5-day window.** With both tracks staffed it fits; with one developer it trips the ADR-0009 tripwire immediately. That is the tripwire doing its job on day one — the correct response is to split the work or re-scope, never to compress the estimate.

---

## Writing the next sprint file

Copy the shape of [`sprint-01.md`](./sprint-01.md). It is a **pointer document**: every task links to its `TASK-0xx` entry in [`../backlog.md`](../backlog.md) and to the normative section that binds it. Per [`../README.md`](../README.md) guideline 1, sprint files stay `status: rationale` — they allocate, they do not define.

Three checks before a sprint file is done:

1. **Every task's dependencies exist in an earlier sprint or this one.** This is the check that caught `TASK-021` sitting in Sprint-01 with no git adapter and no indexer under it.
2. **Every acceptance criterion is mechanical.** If a criterion is prose, it is not a gate.
3. **The sprint closes at least one milestone gate**, and that gate's task appears in [the coverage map](../backlog.md#gate-coverage-map). A sprint that closes no gate is motion without progress.
