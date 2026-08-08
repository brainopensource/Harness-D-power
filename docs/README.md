---
status: normative
updated: 2026-08-05
---

# AETHER Documentation

## Start here

| You are | Read, in order |
| :--- | :--- |
| **New to the project** | [`vision.md`](./vision.md) → [`PHASE-0-LOCK.md`](./PHASE-0-LOCK.md) → [`spec.md`](./spec.md) → [`STATUS.md`](./STATUS.md) · **~40 minutes** |
| **Asking "what is this, really?"** | [`vision.md`](./vision.md) §1 (three horizons) → [ADR-0019](./decisions/0019-three-horizons-harness-framework-metaloop.md) → [`architecture/task_types_and_verdicts.md`](./architecture/task_types_and_verdicts.md) |
| **About to write code** | [`architecture/coding_guidelines.md`](architecture/coding_guidelines.md) → the dev prompt for the current sprint → the `TASK-0xx` entries it names |
| **Planning** | [`agile/roadmap.md`](./agile/roadmap.md) → [`agile/milestones.md`](./agile/milestones.md) → [`agile/backlog.md`](./agile/backlog.md#scheduling-ledger) |
| **An AI agent working here** | [`PHASE-0-LOCK.md`](./PHASE-0-LOCK.md) is the constraint set. Never contradict it without an ADR |

## The map

| Where | Tier | What it owns |
| :--- | :--- | :--- |
| [`vision.md`](./vision.md) | 1 | Mission and architecture at altitude. Orientation, ~10 min |
| [`PHASE-0-LOCK.md`](./PHASE-0-LOCK.md) | **1** | **Normative.** What is settled, what is a known gap, what Phase 1 may and may not change |
| [`spec.md`](./spec.md) | 2 | **Normative.** Invariants I1–I11, the lattice, the ports, the TCB |
| [`measurement.md`](./measurement.md) | 2 | **Normative.** Instrument protocol, the A/A floor, gate design |
| [`decisions/`](decisions/README.md) | 2 | **21 ADRs** (20 Accepted, ADR-0018 Proposed), each with a reversal condition |
| [`STATUS.md`](./STATUS.md) | — | What is *actually* implemented. No claim without pasted command output |
| [`architecture/`](./architecture/capability_layer.md) | 3 | **What the system is.** Capability layer · task types & verdicts · knowledge & memory · extension contract · self-improvement · skeletons · schemas · diagrams. Deep on purpose |
| [`architecture/`](architecture/coding_guidelines.md) | 3 | **How you work on it.** Coding guidelines, patterns to adopt and refuse, tech stack |
| [`agile/`](agile/README.md) | 3 | Roadmap, gates, backlog, sprints, release arc. Gate tables `normative`, the rest `rationale` |

| [`proposals/`](./proposals/) | 3 | **Undecided proposals only.** Ratified ones are deleted — see the lifecycle rule below |
| [`benchmarks/`](./benchmarks/README.md) | 3 | Task samples in; **`results/`** is where measured numbers land — empty until the floor runs |
| [`concepts/`](concepts/README.md) | — | Phase 0 decision trail. History, `retrieval: excluded` |

## The shape

Six folders, one purpose each. If a document does not obviously belong to one of them, that is
a signal it duplicates something — which is exactly what happened to the seventh, `overview/`.

```
docs/
├── *.md              WHAT IS TRUE — vision · PHASE-0-LOCK · spec · measurement · STATUS
├── decisions/        WHAT WAS DECIDED, and what reverses it  (21 ADRs)
├── architecture/     HOW THE SYSTEM WORKS  (10 docs, indexed by question)
├── agile/            WHAT WE ARE DOING  — roadmap · milestones · backlog · sprints/
├── benchmarks/       EVIDENCE — samples in, results/ out
├── concepts/         HISTORY — the Phase 0 trail, `retrieval: excluded`
└── proposals/        UNDECIDED — deleted on ratification (see the lifecycle rule below)

    overview/         QUARANTINED — a hand-written second copy of five of the folders
                      above, added outside this shape and already drifted. Tagged
                      `historical` + `retrieval: excluded`; not authoritative, not
                      maintained, not checked by the link gate. `TASK-084` decides
                      whether it is deleted or generated. It is listed here because
                      an undeclared folder is how the duplication rule got broken.
```

## Who owns which fact

**Every fact has exactly one authoritative home.** If you find the same thing stated in two
places, the second one is the bug — fix it by deleting and linking, never by keeping both in
sync.

| Fact | Lives in |
| :--- | :--- |
| Invariants, the lattice, port rules, TCB residency | `spec.md` |
| Instrument protocol, splits, what a claim needs | `measurement.md` |
| Why a decision went that way, and what reverses it | `decisions/` |
| What is settled and may not drift | `PHASE-0-LOCK.md` |
| What is built, verified by command | `STATUS.md` |
| Port shapes and pseudocode | `architecture/core_skeletons_and_protocols.md` |
| Schema fields and validator wiring | `architecture/schemas_and_contracts.md` |
| The capability layer, `ModelNode`, strategies, fragments, sidecars | `architecture/capability_layer.md` |
| House rules, patterns to adopt and refuse, DoD | `architecture/coding_guidelines.md` |
| Runtime, dependencies, sandbox, cost model | `architecture/tech_stack_and_infra.md` |
| System diagrams | `architecture/architecture_diagrams.md` |
| Measured results | `benchmarks/results/` |
| Tasks, exit criteria, scheduled vs pool | `agile/backlog.md` |
| Phase sequencing and dependency edges | `agile/roadmap.md` · `agile/milestones.md` |
| How a sprint is executed | `agile/sprints/` |

---

## Rules this tree is held to

**Code wins.** Contracts live in `src/aether/ports/`. Documents navigate; they do not define.
When a document and the code disagree, **the document is the bug**.

**If it can be a contract in code, it is not prose here.** The event catalog is generated
from `domain/events.py` with a CI drift check. Port shapes are asserted by reflection. Nothing
in this tree restates something a test already enforces.

**Normative words are budgeted.** `scripts/docs_budget.py` enforces a **15,000-word ceiling**
in CI. A PR adding N normative words deletes N. ADRs are exempt — they are short, and each one
*replaces* long-form derivation elsewhere.

**Every document declares a `status:`** — `normative`, `rationale`, or `historical`. Untagged
fails the gate: an untagged file is invisible to the budget, which would make "no frontmatter"
a way to add normative words for free.

**Binding content declares itself binding.** `status:` is not a budget dial. If a table
constrains what may ship, it is `normative` and it counts — which is why
[`agile/milestones.md`](./agile/milestones.md) and [`agile/roadmap.md`](./agile/roadmap.md)
carry `normative` despite living in a management directory: their exit gates decide when a
phase ends. Tagging gate-bearing content `rationale` to stay under the ceiling is the one
evasion this budget cannot detect, so it is named here and forbidden rather than left to
judgement.

**Both docs gates ship with a test proving they can fail.** `tests/unit/test_docs_gates.py`
plants a dead link and an untagged file and asserts each gate returns non-zero. Before it
existed, `STATUS.md` reported both gates green while both were red.

**Diagrams live in one file.** [`architecture/architecture_diagrams.md`](architecture/architecture_diagrams.md) holds
four: orchestration · inner loop · outer loop · dispatch lifecycle. A diagram whose only content
is a second rendering of a normative table is a drift risk, not an aid — those were deleted
rather than merged. Beyond a handful they rot faster than they inform.

**A proposal is transient.** This is the rule whose absence let `fixes/` grow to a quarter of
the tree before it was renamed `proposals/`.

> A proposal is a **pre-decision** artifact. When it is ratified its content moves to the two
> places that bind — an **ADR** with a reversal condition, and **backlog tasks** with exit
> criteria — plus a reference under `architecture/` if it carries durable design detail. **Then
> the proposal is deleted.** Git keeps the trail.
>
> A proposal older than two sprints is either ratified (delete it) or rejected (delete it).
> `proposals/` holds only what is still undecided.

**Detail is welcome; duplication is not.** This project is complex enough that a junior
developer should be able to execute a senior-level task from the documents alone, so
`architecture/` is deliberately deep — contracts, pseudocode, protocols, guidelines. What is
forbidden is stating the same fact twice, because the second copy drifts and nobody knows which
one is current. See *Who owns which fact* above.

---

## On `_archive/`

Superseded. Everything under `docs/_archive/` is tagged `historical` and
`retrieval: excluded`: it costs nothing against the budget, and no retrieval surfaces it.

**This tree does not depend on it.** Anything load-bearing was carried forward into the
documents above — the decisions into [`decisions/`](decisions/README.md), the measurement
history into [`measurement.md`](./measurement.md), the Phase 0 adjudication into
[`concepts/`](concepts/README.md). The archive can be deleted without breaking a link or
losing a binding claim.

Read it as history, never as instructions. It audits `src/sagiha/`, which is retired.
