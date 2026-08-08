---
status: normative
updated: 2026-08-07
---

# Phase 0 — Lock Record

**Phase 0 is closed as of 2026-08-07.** It covers Sprints 1, 2, 3 and 3.5: the skeleton, the
instrument, and the decisions that govern both. Phase 1 begins at Sprint 4.

**What a lock means here.** Everything below is settled and is not reopened by ordinary work. A
locked decision changes only through its own reversal condition, or through a new ADR that
supersedes it explicitly. **Drift from this list is a defect, not a design choice** — if a task
requires breaking something here, that is a signal to write an ADR, not to proceed.

---

## 1. Locked — architecture

| # | Locked | Enforced by |
| :--- | :--- | :--- |
| **L1** | The import lattice `engine > (agency \| workflow) > measurement > kernel > adapters > ports > domain` | `.importlinter`, 10 contracts, 0 broken (4 AETHER + 5 retiring `sagiha` + 1 new) |
| **L1 note** | `agency` and `workflow` are **siblings**. Revisions before 2026-08-07 stated `workflow > agency` — that is [ADR-0018](./decisions/0018-agency-below-workflow.md)'s *proposed* lattice, not the enforced one, and a lock stating an unenforced constraint is the failure mode the lock exists to prevent. Becomes true when ADR-0018 ratifies with `TASK-053` | ADR-0018 (**Proposed**) |
| **L2** | Invariants **I1–I11** as stated in [`spec.md`](./spec.md) §2 | Per-invariant mechanisms; **four** have known gaps (I7, I9, I10, I11) — §4 |
| **L3** | **Eight port areas, nine protocols.** A port arrives with its first adapter | ADR-0005 rev. 2; conformance meta-suite |
| **L4** | Ports are **wire-serializable**: every method `async`, no `Path`/handle/callable/generator/live object | Reflection contract over all ports (I3) |
| **L5** | **One dispatch choke point.** `authorize → verify grant → acquire lease → dispatch → release`, verified at effect time | `kernel/dispatch.py`; architecture test proves no bypass |
| **L6** | **TCB residency**: `PolicyEngine` in `kernel/`, `Evaluator` in `measurement/`, never `adapters/` | `tcb-isolation`; residency is what makes the contract select them |
| **L7** | **Topologies are data**, node implementations are code | ADR-0014; validator + 5 static checks, no `--force`; `aether-workflow-tcb-isolation` selects the validator and executor |
| **L8** | The DAG stays **acyclic**; every loop is **statically bounded** | ADR-0013; `check_bounded_iteration`, bound ∈ [1,16] |
| **L9** | **Python 3.13, monoglot.** Compiled sidecars per component on a measured trigger, never speculatively | ADR-0001; F1 timers published |
| **L10** | **Explicit wiring, no DI container, no runtime registration** | `spec.md` §3; I6 composition test |

## 2. Locked — measurement

| # | Locked | Enforced by |
| :--- | :--- | :--- |
| **L11** | **No number before the floor.** No capability number is published until `noise-floor.md` holds one | ADR-0002 — **reversal conditions: none** |
| **L12** | Tri-state `GateReport`; `NONE` is *unmeasured*, excluded from the denominator | B4; `_report_from_exit` is the single mapping |
| **L13** | **Exact McNemar + Holm–Bonferroni**, α = 0.05 family-wise, **N derived** for ≥0.80 power | ADR-0003 rev. 2; the module refuses corrected p-values for an undeclared family |
| **L14** | The gate family is declared **before any arm runs** | `require_declared_family()` |
| **L15** | Manifests and split assignment are **TCB data**: a change is a new hash, never an edit | `manifest_schema.yaml`; canonical-JSON sha256 |
| **L16** | Task validity is **bidirectional**: gold passes *and* empty fails, per task, on our instrument. Exclusions published with a typed reason | TASK-014 |
| **L17** | **Lift and absolute are published together**, never one without the other | `vision.md` §1, `measurement.md` §4 |
| **L18** | A competitor's published number is **never** evidence. The comparative claim needs our own rig | `spec.md` §9; TASK-015 |
| **L19** | Every gate ships with a test proving it **can fail** | `measurement.md` §5 |

## 3. Locked — what is built and green

Verified by command, not memory. See [`STATUS.md`](./STATUS.md) for the full table.

| Component | State |
| :--- | :--- |
| `domain/` · `ports/` · `kernel/` · `adapters/` · `measurement/` · `workflow/` | Implemented — 6,320 lines |
| Walking skeleton `retrieve → generate → apply → evaluate` | Runs end to end from a validated topology |
| Bounded repair edge, statically unrolled | `NONE` never routes into repair; per-iteration budget |
| Evaluation container + B3 canary | 7/7 green, including two negative tests |
| Pinned manifest `internal-floor-01` | `sha256:7c2c2467…`, 84 tasks, bidirectionally screened. **Predates `problem_statement` (§4) — must be rebuilt before it carries a measured run** |
| Statistics engine | Verbatim port green; derived-N reproduces ADR-0003's table in 12/12 cells |
| Edit-format seam, node registry by kind | 7 topologies validate |
| `pyright` · `lint-imports` · tests | 0 errors · 10/10 contracts · 402 tests |

## 4. Locked as **known gaps** — recorded, not hidden

These are Phase 0 outcomes too. Locking them means they are scheduled, not forgotten, and none
may be quietly rediscovered as a surprise.

| Gap | Reality | Closed by |
| :--- | :--- | :--- |
| **I7 unenforced** | `grep -rn "tests_unmodified" src/aether/` → nothing | `TASK-049`, Sprint 4 — **blocks the floor** |
| **I10 unenforced** | `spec.md` §2 names a CI floor on byte-identical-prefix rate. No assembler, no declared breakpoints, no such job — one frozen `system` message is the whole of L1. **Added 2026-08-07: three of eleven invariants are enforced by nothing and only two were on this list** | `TASK-056` |
| **No problem statement** | `TaskCandidate` had no issue-text field; `runner.py` substituted the `instance_id`, so the baseline was posed `django__django-11099`. **Fixed 2026-08-07**; the consequence is that `internal-floor-01` predates the field and must be rebuilt | `TASK-076`, rebuild — **blocks the floor** |
| **The rig has one arm** | `PairedRunner` is used by neither floor script and has no AETHER arm, so it cannot compute lift. `run_aa_floor.py` calls `engine.run()` directly | `TASK-083` |
| **Baseline contaminated** | `run_local_check.py` injects `run_tests.py` into the prompt | `TASK-049b`, Sprint 4 — **blocks the floor** |
| **I9 unenforced** | `spec.md` claims type-level `rank()`/`admit()` separation; neither exists | `TASK-067`, M3 — built with the first ranker |
| **I11 not enforced on the model path** | The predicate is correct; nothing there produces untrusted spans, and repo content is labelled `AGENT` so the tool loop works | `TASK-030a`/`030b` |
| **Tool execution uncontained** | `BuiltinToolRegistry` uses `create_subprocess_shell` on the host while the evaluator is contained | `TASK-018` second half + `TASK-062` |
| **A/A floor not taken** | Instrument complete and rehearsed; arms cost real spend | Sprint 4 Task 5 |
| **No localization** | `RetrieveStep` reads files a topology *names*; SWE-bench needs discovery | `TASK-064` |
| **No client** | `spec.md` §8 declares Clients; zero tasks existed | `TASK-075` |
| **`evolution/` absent** | A `tcb-isolation` target that does not exist, therefore vacuous | Post-M4 |

**Where these came from.** This table is the merged output of the Phase 0 coverage audit —
gate→task, invariant→mechanism, spec-package→task, and mission→milestone. The last of those
found the largest gap: the mission had no milestone, so the gate-coverage map (which checks
*milestone gate → task*) could not see it. Closed by
[ADR-0019](./decisions/0019-three-horizons-harness-framework-metaloop.md) and M5/M6.

**`TASK-018` and `TASK-015` are marked ✅ with unmet exit criteria** (tool container; OpenHands
arm). Honest in their own prose, and they scan as done — recorded here so the next reader is not
misled.

## 5. Locked — governance

- **`status:` taxonomy**: `normative` · `rationale` · `historical`. Untagged fails the gate.
- **Normative ceiling 15,000 words**, ADRs exempt. `docs_budget.py` gates on its bare invocation.
- **Code wins.** When a document and `src/aether/ports/` disagree, the document is the bug.
- **A proposal is transient.** Ratified ⇒ it becomes an ADR plus backlog tasks, and the proposal
  is deleted. `proposals/` holds only what is still undecided.
- **21 ADRs, 20 ratified**, each with a reversal condition. ADR-0018 is Proposed and ratifies at
  Sprint 5 Task 1.

## 6. What Phase 1 may change without an ADR

So the lock does not read as a freeze on work:

- Node implementations, prompts, roles, retrieval parameters, topologies — **all mutable**.
- New adapters behind existing ports.
- New capability implementations in `agency/`.
- Additive schema fields within a minor version (`spec.md` §4's port-versioning rule).
- Anything in `agile/` — the plan is `rationale` and is expected to move.

**What Phase 1 may not change without an ADR:** the lattice, the invariants, port shapes that
break an adapter, the TCB boundary, the admission protocol, or anything in §1–§2 above.

---

## 7. Entering Phase 1

Phase 1 is **Sprint 4 → Sprint 5** ([`roadmap.md`](./agile/roadmap.md) M1a++R → A/A floor → M1b).
Its entry condition is this file. Its exit condition is a real number in
`benchmarks/results/noise-floor.md` and `agency/` existing with the lattice still 9/9.

Read next: [`vision.md`](./vision.md) → [`spec.md`](./spec.md) →
[`agile/sprints/sprint-04-dev-prompt.md`](./agile/sprints/sprint-04-dev-prompt.md).
