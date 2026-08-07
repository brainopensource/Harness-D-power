---
status: rationale
updated: 2026-08-07
---

# Coverage Audit — Is the Plan Complete?

**Question asked:** after Sprints 1, 2, 3 and 3.5, and with Sprints 4 and 5 planned, is that
enough to finish development?

**Answer: no, and it was never designed to be.** Sprints 4–5 take the project to **M1b**.
`roadmap.md` still has M2-eng, M2-abl, B3 and M3 ahead, and `sprints/README.md` deliberately
refuses to plan them until the floor reports per-task wall-clock. That is working as
intended.

The useful question is the other one: **does anything normative have no task at all?** This
document runs that check in the direction `backlog.md` says matters — *"a gate with no task is
a tripwire guaranteed to fire"* — plus three directions it does not currently run: invariant →
mechanism, spec package → task, and mission → milestone.

**Six gaps found.** Four are real holes; two are bookkeeping that hides a hole.

---

## 0. Summary

| # | Gap | Severity | Evidence |
| :--- | :--- | :--- | :--- |
| **G1** | **The mission has no milestone, no gate, and no task.** Nothing produces a SWE-bench number | **Critical** | `milestones.md` ends at M3. No task builds a SWE-bench manifest, runs a SWE-bench floor, or executes a publication run |
| **G2** | **`TASK-006` (mock adapters + cassettes) was never built and is unmarked** | **High** | `src/aether/adapters/mock/` and `tests/fixtures/cassettes/` do not exist. It is an **M0** task and the precondition for affordable M2 ablations |
| **G3** | **I9 has no mechanism** | **High** | `spec.md` §2 claims *"Type-level `rank()`/`admit()` separation"*. `grep -rn "def rank\|def admit\|class Rank" src/aether/` → nothing |
| **G4** | **M1a++, M1a++R and M1b have no exit gates** | **Medium** | `milestones.md` covers B1–B4, M0, M1a, M1a+, M2, M3 only. Three roadmap milestones are ungated |
| **G5** | **No client task.** `spec.md` §8 is "Clients"; §3 declares `tui/`; `vision.md`'s diagram shows TUI/CLI/GUI | **Medium** | Zero tasks in `backlog.md`. `TASK-063` says *"lands with the first client that renders it"* — there is no task for one |
| **G6** | **No `evolution/` task and no meta-loop task** | **Medium** | `spec.md` §3 declares `evolution/`; ADR-0006 defines its authority; ADR-0014's stated rationale is the self-redesign ladder; ADR-0017 is subagent attenuation. Zero tasks |

Two further items are **marked DONE with unmet exit criteria**, which is how G2's class of
defect hides: `TASK-018` (tool container — *"its own container image remains open"*) and
`TASK-015` (comparative rig — *"OpenHands arm still out of scope"*). Both are honest in their
prose and both read as ✅ in a scan.

---

## 1. G1 — The mission is unfunded

`vision.md` §1: *"Build an autonomous coding agent harness that competes at the top of the
public leaderboards… The targets are SWE-bench Pro and SWE-bench Verified."*
`measurement.md` §4 commits to **≥90% Verified / ≥60% Pro** and lift ≥ +10 points.

Trace the chain from here to that number:

```
  TASK-036  SWE-bench per-instance images        → deferred, unmarked
  TASK-064  localization ContextSource           → Sprint 5+   (without it the harness
                                                                cannot choose which files
                                                                to open on a real repo)
  ???       build + pin a SWE-bench manifest     → NO TASK
  ???       take the A/A floor on THAT manifest  → NO TASK
  ???       run the paired lift arms             → NO TASK
  ???       publication run on SEALED            → NO TASK
```

The A/A floor scheduled in Sprint 4 runs against `benchmarks/manifests/internal-floor-01.yaml`
— 84 **synthetic** tasks (`suite: internal`, one `mod.py` each). That floor is correct and
necessary: it characterises instrument variance and derives N. **It is not the SWE-bench
floor**, and its discordance rates are not transferable to a different suite with different
repositories, different test runners and different flakiness.

`measurement.md` §6 already specifies what a publication needs — seven numbered conditions.
Nothing in `backlog.md` implements them. `milestones.md` ends at M3, so there is no gate to
fund.

**This is the D15 defect class the gate-coverage map exists to catch, one level up**: the map
checks *milestone gate → task*, and the mission is not a milestone, so it is invisible to the
check.

**Proposed: `M4 — Benchmark Delivery`**, with gates and tasks:

| Task | Title |
| :--- | :--- |
| `TASK-071` | SWE-bench manifest build + bidirectional validity canary at scale (reuses `TASK-014`'s tooling; expect a real exclusion list — ~30% of public Pro tasks were estimated broken) |
| `TASK-072` | SWE-bench A/A floor — its own discordance rates, its own derived N |
| `TASK-073` | Paired lift run: bare-model arm vs AETHER arm, same model, same manifest, `measurement.md` §4.1's pre-registered baseline |
| `TASK-074` | Publication run on SEALED, satisfying all seven of `measurement.md` §6 |
| `TASK-015b` | The OpenHands arm — the only admissible route to the competitive claim |

---

## 2. G2 — `TASK-006` is an unbuilt M0 task

```bash
ls src/aether/adapters/mock      # No such file or directory
ls tests/fixtures/cassettes      # No such file or directory
```

`tests/fixtures/replay_smoke/cassette.json` exists but belongs to the retiring tree —
`scripts/gen_replay_fixture.py` references `sagiha replay`, `RunLoop` and
`composition.build_kernel`, none of which exist in `src/aether/`.

`tests/aether/mocks.py` provides in-memory fakes (`FakeModelProvider`, `InMemoryWorkspace`,
…) and those carry the conformance suite. What is missing is the **cassette replay engine**
and its exit criterion: *"100 turns in under 50 ms with no API call and no container. Replay
is byte-for-byte deterministic."*

**Why it matters now rather than at M0.** That criterion is what makes the ablation cadence
from M2 onward *practically runnable rather than aspirational* — the backlog says so in its
own complexity note. Every M2 ablation re-runs N ≥ derived-N tasks across arms; without
deterministic replay, iterating on the harness means paying inference every time. It is also
the substrate `TASK-057`'s golden-prompt equivalence test and `TASK-056`'s prefix-stability
floor both need — *"over a fixed recorded replay"* presumes a recording.

**Recommendation:** schedule in **Sprint 5**, beside `TASK-057`, which needs a recording
provider anyway.

---

## 3. G3 — I9 is enforced by nothing

`spec.md` §2 lists eleven invariants under the heading *"Each has a mechanical enforcement.
An invariant enforced by discipline is a wish."* I9's stated mechanism is **"Type-level
`rank()` / `admit()` separation"**. There is no `rank()`, no `admit()`, and no type that
separates them.

`workflow_schema.yaml:105-108` carries the constraint in prose — *"Rankers ORDER candidates
and may never ADMIT one (I9) — admission is the evaluate node, always"* — and a schema comment
is documentation, not a type.

This is **exactly the I7 situation Sprint 4 exists to fix**: an invariant that reads as
enforced, whose named mechanism returns nothing under grep. The difference is that I9 is not
yet load-bearing — no ranker exists — so the correct move is to build the type separation
*with* the first ranker (`TASK-067`) rather than retrofit it after.

**Recommendation:** fold the type-level separation into `TASK-067`'s exit criteria, and
until then record I9 in `STATUS.md`'s deviations section as *mechanism pending, no ranker
exists*. An invariant table that overstates enforcement is the same defect as a contract
selecting zero files.

---

## 4. G4 — Three milestones have no gates

`milestones.md` is `normative` and opens with ADR-0009's rule: *"a milestone is complete only
when all its exit gates pass cleanly in CI."* It contains gates for B1, B2, B3, B4, M0, M1a,
M1a+, M2, M3.

`roadmap.md` now also contains **M1a++**, **M1a++R** and **M1b**. None has an exit gate.
M1a++ is currently marked *"Code complete; gate open"* — accurate, and the gate it is open on
does not exist as a gate.

The gates are already written; they are just in the wrong file. Sprint 4's and Sprint 5's
DoD sections are the M1a++R and M1b gates. Promote them into `milestones.md`, where they
bind, and the coverage map picks them up automatically.

---

## 5. G5 — No client, anywhere

`spec.md` §8 is titled *Clients*; §3's tree declares `tui/`; `vision.md`'s architecture
diagram shows TUI, CLI and GUI as the three consumers of the event stream; `TASK-022`'s
rationale is *"the one stream every client in the system reads from."*

**`backlog.md` has no client task.** `scripts/run_local_check.py` and
`scripts/run_aa_floor.py` are the de facto clients, and they are scripts in `scripts/`, not
a surface in the lattice.

This is defensible as sequencing — a benchmark harness needs no GUI to produce a number — but
it is currently invisible rather than deferred. Two consequences: `TASK-063` (live log
telemetry) is scheduled to *"land with the first client that renders it"* and therefore has
no landing site; and `TASK-058`'s claim that CLI/TUI/GUI forms generate from
`RunConfig.model_json_schema()` has nothing to demonstrate it.

**Recommendation:** one task — `TASK-075`, a **read-only TUI** over the event bus, after
`TASK-058`. Read-only keeps it out of the authority question entirely (a client with no
privileged access is `spec.md` §8's own requirement) and it is what makes `TASK-063` and
`TASK-058` demonstrable.

---

## 6. G6 — `evolution/` and the meta-loop have no tasks

Four ratified ADRs describe machinery that has no task:

- **ADR-0006** defines the meta-loop's mutable surface and TCB authority boundary.
- **ADR-0014**'s entire stated rationale is that without topology-as-data, *"the only
  mechanical path from where we are to machine self-redesign runs through arbitrary code
  modification — the most dangerous grant in the system."*
- **ADR-0017** specifies subagent capability attenuation.
- **`spec.md` §3** declares `src/aether/evolution/` — *"offline only — never imported by
  anything"* — with its own import contract.

`sprints/README.md` lists **"M4+: Meta-loop, workflow self-redesign, self-modification"** with
tasks: **"—"**.

`.importlinter`'s `aether-tcb-isolation` already names `aether.evolution` as a forbidden
importer, so that contract is **currently vacuous for one of its five targets** — the package
does not exist. That is the D15 shape again: a contract naming a module that is not there
passes green and forbids nothing.

**Recommendation:** this is genuinely post-M3 and should stay there. But record it as
*deferred with a named milestone* rather than as a dash, and note the vacuous contract target
in `STATUS.md`. `PHASE-0-LOCK.md` and
`concepts/rewrite_v300_agi_path_after_all_milestones_are_delivered.md` already hold the
thinking; they are not backlog entries.

---

## 7. What "finished" actually requires

Sequenced, with what is planned today marked:

```
  ✅ Sprints 1–3.5   M0 · B1 · B2 · B4 · M1a · M1a+ · M1a++ · B3
  📋 Sprint 4        M1a++R + the internal A/A floor          ← planned
  📋 Sprint 5        M1b (agency/, ModelNode, RunConfig)      ← planned
  ⬜ Sprint 6        M2-eng: TASK-032 memoization + TASK-006  ← sized off Sprint 4's wall-clock
  ⬜ Sprint 7+       M2-abl: repair · context · Architect/Editor ablations
  ⬜ Sprint N        M3: TASK-035 branching · TASK-033 sequencing · TASK-067 ranker
  ⬜ Sprint N+1      M4 — BENCHMARK DELIVERY  ← G1, currently unfunded
                       TASK-036 images · TASK-064 localization
                       TASK-071 manifest · TASK-072 SWE floor
                       TASK-073 lift · TASK-074 publication · TASK-015b OpenHands
  ⬜ post-M4         M5: evolution/ + meta-loop  ← G6, deliberately deferred
```

**Two sprints are planned out of roughly eight.** That is not a planning failure —
`roadmap.md` and `sprints/README.md` both state, with reasons, that M2-abl onward cannot be
sized until the floor reports per-task wall-clock. What *is* a planning failure is that the
final phase, the one the whole project exists for, has no milestone to be sized against.

## 8. Recommended backlog additions

| Task | Title | Cx | When |
| :--- | :--- | :---: | :--- |
| `TASK-006` | *(exists, unbuilt)* Mock adapters + cassette replay | **3** | **Sprint 5** — `TASK-056`/`TASK-057` both presume a recording |
| `TASK-071` | SWE-bench manifest + validity canary at scale | **3** | M4 |
| `TASK-072` | SWE-bench A/A floor | **4** | M4 |
| `TASK-073` | Paired lift run (bare-model vs AETHER) | **4** | M4 |
| `TASK-074` | Publication run on SEALED, `measurement.md` §6 ×7 | **3** | M4 |
| `TASK-015b` | OpenHands arm through our evaluator | **5** | M4 |
| `TASK-075` | Read-only TUI over the event bus | **2** | after `TASK-058` |

Plus three documentation corrections, none of which needs a sprint:

1. **Promote Sprint 4's and Sprint 5's DoD into `milestones.md`** as the M1a++R and M1b exit
   gates (G4).
2. **Record I9's missing mechanism in `STATUS.md`'s deviations**, and fold the type-level
   `rank()`/`admit()` separation into `TASK-067` (G3).
3. **Add an `M4` and `M5` row to `sprints/README.md`'s shape table** with named contents
   instead of a dash (G1, G6), and note `aether.evolution`'s vacuous contract target.

---

## 9. What this audit does not claim

- **No schedule.** Sprint counts past Sprint 5 are not estimated here, for the reason
  `roadmap.md` gives: an ablation's wall-clock is dominated by inference across derived N,
  and nobody has measured per-task wall-clock yet.
- **No criticism of the deferrals.** M2-abl, M3 and the meta-loop being unplanned is a
  ratified decision ([ADR-0009](../decisions/0009-gates-are-the-schedule.md)), not an
  oversight. G1 is different: it is not deferred, it is absent.
- **G5 and G6 are sequencing, not defects.** They are recorded because *invisible* deferral
  and *decided* deferral look identical in a backlog, and only one of them survives a
  handover.
