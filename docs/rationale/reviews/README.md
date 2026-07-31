---
status: historical
updated: 2026-07-30
retrieval: excluded
---
# **Reviews**

> [!NOTE]
> **Advisory audits, not normative docs.** Reviews record an external assessment at a point in
> time. They do **not** override modular docs (`01`–`07`) or the [ADR log](../../08-decisions/README.md).
> Where a review recommends a change, that change becomes binding only when it lands in a
> normative doc, [STATUS.md](../../STATUS.md), or a sprint plan.

Reviews are **not deprecated**. They are the audit trail. Accepted remediation is tracked in
normative docs and sprints; open items until Sprint 3 closes are summarized below.

## **Log**

| Date | Review | Scope | Headline |
| :--- | :--- | :--- | :--- |
| 2026-07-28 | [Architecture & Documentation Review](2026-07-28-architecture-and-documentation-review.md) | Full tree — 56 modular docs, 2 reference blueprints, ~5,000 lines. No code existed at review time. | 16 defects (5 critical/high in the port contracts), 10 gaps, 11 stack/architecture changes, 7 documentation changes. Verdict: the reasoning is ready, the contracts are not, and the next commit should be `src/`. |
| 2026-07-29 | [Foundation Review & Deep Audit](2026-07-29-foundation-review.md) | Full tree — 74 docs, `src/` (~2,800 lines), 16 tests, CI, config, sprint plan. Mid–Sprint 2. | 18 code-verified defects, 10 gaps, 11 doc findings. Verdict: coherent but demonstration-poor; close one measured loop before growing surface. **Current audit of record** until Sprint 3 closes. Drives Sprint 3. |

## **Remediation (doc findings)**

| Finding | Status |
| :--- | :--- |
| X1–X5, X11 (dense-deferral, trace ownership in RHI, markdown contracts, dispatch pseudocode, sandbox timing, event catalog) | Done in normative docs |
| X8 (reference retrieval hazard) | Done — strengthened banners; exclude `reference/` + `reviews/` from agent retrieval |
| X9 (runnable CLI claims) | Done — Planned banners + [STATUS.md](../../STATUS.md) |
| X10 (inert config) | Done — consumption table in [configuration-reference.md](../../05-tech-stack/configuration-reference.md) |
| X6 / X7 (sequencing / historical remediation table) | Addressed in STATUS + Sprint 3; 2026-07-28 table left historical |
| Code defects D1–D18, gaps G1–G10 | **Open — Sprint 3 / later blocks** (not doc work) |

## **Finding ID Convention**

| Prefix | Meaning |
| :--- | :--- |
| `D<n>` | **Defect** — a contradiction, self-violation, or contract that cannot be implemented as written. Always carries a `file:line` citation verified at review time. |
| `G<n>` | **Gap** — something absent that the project's stated ambition requires. |
| `C<n>` | **Change** — a decision the reviewer would make differently on stack or architecture. |
| `X<n>` | **Documentation remediation** — a change to the docs themselves. |

IDs are stable within a review and prefixed by its date when referenced across reviews (e.g. `2026-07-28/D1`).

## **How to Act on a Review**

1. **Triage by tier**, not by ID order. Each review ends with a prioritized action plan; that ordering reflects dependency and cost, and the ID numbering does not.
2. **Defects that touch a contract get fixed in code, not in prose.** A `Protocol` corrected in a markdown file is a correction that will drift again.
3. **A rejected finding is recorded, not deleted.** Note the rejection and the reasoning in the relevant ADR — the same discipline as the `Reversal Conditions` section, applied in the other direction.
4. **Track open work in [STATUS.md](../../STATUS.md) and Sprint 3** until the audit of record is superseded by a newer review or Sprint 3 exit.

## **Cross-References**

* [STATUS.md](../../STATUS.md) — implementation truth.
* [ADR Log](../../08-decisions/README.md) — where accepted findings become binding decisions.
* [CI & Quality Gates](../../06-guides-and-patterns/ci-and-quality-gates.md) — where findings that can be checked mechanically should end up.
* [Phased Migration Matrix](../../07-roadmap/phased-migration-matrix.md) — the plan a review's sequencing recommendations would amend.
