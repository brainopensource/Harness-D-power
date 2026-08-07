---
status: normative
updated: 2026-08-05
---

# AETHER Documentation

**Start at [`vision.md`](./vision.md)** if you are new. **Go to [`spec.md`](./spec.md)** if
you need to know what is true.

| Document | Tier | What it is |
| :--- | :--- | :--- |
| [`vision.md`](./vision.md) | 1 | The mission and the architecture at altitude. Orientation, ~10 minutes |
| [`spec.md`](./spec.md) | 2 | **Normative.** The minimal statement of what is true. Everything binding is here or in code |
| [`measurement.md`](./measurement.md) | 2 | **Normative.** The instrument protocol, the A/A floor, gate design |
| [`decisions/`](./decisions/README.md) | 2 | ADRs. Every decision with its reversal condition |
| [`STATUS.md`](./STATUS.md) | — | What is actually implemented. No claim without a line-level code read |
| [`agile/`](./agile/README.md) | 3 | Roadmap, milestone exit gates, backlog, sprints, coverage audit, release plan. Gate tables are `normative`; the rest is `rationale` |
| [`architecture_diagrams.md`](./architecture_diagrams.md) | 3 | Four Mermaid diagrams: orchestration, inner loop, outer loop, dispatch lifecycle. **Shows the target architecture — parts are unbuilt** |
| [`development/`](./development/core_skeletons_and_protocols.md) | 3 | Pre-Phase 1 engineering specs — skeletons, schemas, stack. Superseded by code as it lands |
| [`fixes/`](./fixes/proposal_abstraction_and_harness_composition.md) | 3 | Design proposals and audits. The largest directory: read the one your task names, not the folder |
| [`rationale/benchmarks/`](./rationale/benchmarks/README.md) | 3 | Where measured results land — the noise floor, the F1 timers. Empty of numbers until the floor runs |
| [`benchmarks/`](./benchmarks/README.md) | 3 | SWE-bench task samples with pinned base commits |
| [`concepts/`](./concepts/README.md) | — | Phase 0 trail — the audit, the fork adjudication, the decision record. History, `retrieval: excluded` |

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

**Five diagrams, total.** Layer graph · run-loop sequence · dispatch choke point · context
prefix layout · phase dependency graph. Each encodes something a previous attempt got wrong.
Beyond five they rot faster than they inform.

---

## On `_archive/`

Superseded. Everything under `docs/_archive/` is tagged `historical` and
`retrieval: excluded`: it costs nothing against the budget, and no retrieval surfaces it.

**This tree does not depend on it.** Anything load-bearing was carried forward into the
documents above — the decisions into [`decisions/`](./decisions/README.md), the measurement
history into [`measurement.md`](./measurement.md), the Phase 0 adjudication into
[`concepts/`](./concepts/README.md). The archive can be deleted without breaking a link or
losing a binding claim.

Read it as history, never as instructions. It audits `src/sagiha/`, which is retired.
