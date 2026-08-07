---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# Phase 0 — The Decision Trail

**History. Not instructions.** These documents record *how* the v3.0.0 architecture was
decided. What was decided is [`docs/decisions/`](../decisions/README.md); what is true is
[`docs/spec.md`](../spec.md).

**Nothing here is maintained.** Two live registers of the same decisions is how the workflow
DAG went three implementation plans without a vote.

| Document | What it is |
| :--- | :--- |
| [`rewrite_v300_project_vision.md`](../vision.md) | The original onboarding brief. Superseded by [`../vision.md`](../vision.md) |
| [`rewrite_v300_context.md`](./rewrite_v300_context.md) | The Project Lead's charge: read first, then audit, then spec |
| [`rewrite_v300_documentation_guide_references.md`](README.md) | What the prototype taught us, mapped onto the contested forks |
| [`rewrite_v300_decision_brief.md`](./rewrite_v300_decision_brief.md) | The meeting agenda. **Revised** — three fork rows were corrected against Track B's text |
| [`rewrite_v300_phase0_audit_register.md`](./rewrite_v300_phase0_audit_register.md) | **The load-bearing document.** Every contradiction between the two proposals and every untraceable number, with citations |
| [`rewrite_v300_decision_record.md`](./rewrite_v300_decision_record.md) | The ratification: twelve forks plus the DAG, and how each was reached |
| [`rewrite_v300_agi_path_after_all_milestones_are_delivered.md`](./rewrite_v300_agi_path_after_all_milestones_are_delivered.md) | The Executive Leadership directive commissioning the long-horizon specs. Its three deliverables landed as [`../development/`](../development/core_skeletons_and_protocols.md); the autonomy ladder it sketches is ratified in [ADR-0014](../decisions/0014-workflow-topology-is-data.md) and [ADR-0017](../decisions/0017-subagent-capability-attenuation.md) |

## Read this first if you read nothing else

Two findings from the audit outlived the meeting and are worth carrying forward as habits:

**Three of twelve fork rows misstated the opposing proposal** — two of them among the three
flagged as most urgent. The cause was mundane: the comparison document reviewed a revision
of the other proposal that had been superseded twenty minutes earlier, and everything was
squashed into one commit so there was no history to diff against. Verification discipline was
applied honestly to text that had already changed.

**A significance gate cited as competitor evidence did not exist in that competitor's code.**
The study asserted `p < 0.05` across ≥50 instances; the actual holdout was roughly five
examples with no significance test anywhere. This appeared inside the research meant to
inform the fork about whether numbers can be trusted before the instrument is verified —
which is the argument for [ADR-0002](../decisions/0002-no-number-before-the-floor.md), made
accidentally.

## On citations into `docs/_archive/`

The audit register cites archived documents by path and line. Those citations are written as
**plain paths rather than links**, deliberately: `docs/_archive/` is superseded and slated for
deletion, and this trail must not break when it goes.

**The citations stay re-derivable after deletion** — the archive is committed, so
`git show <commit>:docs/_archive/<path>` recovers any cited file. Deleting a directory from
the working tree does not delete it from history.
