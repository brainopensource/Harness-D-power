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
| [`00/`](./00/) | 3 | Phase 0 trail — the audit, the fork adjudication, the decision record. History |

---

## Rules this tree is held to

**Code wins.** Contracts live in `src/aether/ports/`. Documents navigate; they do not define.
When a document and the code disagree, **the document is the bug**.

**If it can be a contract in code, it is not prose here.** The event catalog is generated
from `domain/events.py` with a CI drift check. Port shapes are asserted by reflection. Nothing
in this tree restates something a test already enforces.

**Normative words are budgeted.** `scripts/docs_budget.py` enforces a ceiling in CI. A PR
adding N normative words deletes N. ADRs are exempt — they are short, and each one *replaces*
long-form derivation elsewhere.

**Every document declares a `status:`** — `normative`, `rationale`, or `historical`. Untagged
fails the gate: an untagged file is invisible to the budget, which would make "no frontmatter"
a way to add normative words for free.

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
[`00/`](./00/). The archive can be deleted without breaking a link or losing a binding claim.

Read it as history, never as instructions. It audits `src/sagiha/`, which is retired.
