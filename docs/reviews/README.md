---
status: historical
updated: 2026-07-29
---

# **Reviews** [DEPRECATED]

> [!NOTE]
> **Advisory, not normative.** Reviews record an external assessment at a point in time. They do not override the modular docs (`01`–`07`) or the [ADR log](../08-decisions/README.md). Where a review recommends a change, that change becomes binding only when it lands in a normative doc or a new ADR.

Adversarial reviews of the architecture and documentation. Each is dated, scoped, and carries stable finding IDs so individual items can be accepted, rejected, or tracked without re-reading the whole report.

## **Log**

| Date | Review | Scope | Headline |
| :--- | :--- | :--- | :--- |
| 2026-07-28 | [Architecture & Documentation Review](./2026-07-28-architecture-and-documentation-review.md) | Full tree — 56 modular docs, 2 reference blueprints, ~5,000 lines. No code existed at review time. | 16 defects (5 critical/high in the port contracts), 10 gaps, 11 stack/architecture changes, 7 documentation changes. Verdict: the reasoning is ready, the contracts are not, and the next commit should be `src/`. |
| 2026-07-29 | [Foundation Review](./2026-07-29-foundation-review.md) | Full tree — 74 docs, `src/` (~2,800 lines), 16 tests, CI, sprint plan. Mid–Sprint 2. | 11 code-verified defects (incl. dead tool-dispatch branch, request-blind replay), 9 gaps, 5 unproven assumptions. Verdict: coherent and disciplined but demonstration-poor; close one measured loop before growing surface. Drives [Sprint 3](../sprints/sprint-3.md). |

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
4. **Re-run the verification commands** in the review's appendix after remediation. Every cross-document contradiction was confirmed mechanically and can be re-confirmed the same way.

## **Cross-References**

* [ADR Log](../08-decisions/README.md) — where accepted findings become binding decisions.
* [CI & Quality Gates](../06-guides-and-patterns/ci-and-quality-gates.md) — where findings that can be checked mechanically should end up.
* [Phased Migration Matrix](../07-roadmap/phased-migration-matrix.md) — the plan a review's sequencing recommendations would amend.
