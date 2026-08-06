---
status: normative
updated: 2026-08-05
---
# ADR-0006: The TCB Boundary, and What the Meta-Loop May Commit

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F6

## Context

The governing argument is short and survives everything below: **an optimizer whose mutable
surface includes its evaluator has one strictly dominant strategy — weaken the judge.** No
downstream statistical rigour detects it, because the statistics are computed by the thing
being weakened, and the failure is retroactive.

The fork as framed was much wider than the fork as it existed. The audit established:

- Both proposals define a TCB. The opposing one labels its kernel "Trusted Computing Base",
  states the Generator ≠ Evaluator and Immutable TCB invariants verbatim, and adopts a
  `tcb-isolation` import-linter contract.
- The "auto-commits to production" position attributed to it **is not in its text**.
- The competitor evidence cited for auto-commit **inverted its source**: that system ships
  `create_pr: bool = True` and documents "all changes go through human review, never direct
  commit". The same study asserted a `p < 0.05 / N ≥ 50` significance gate that **does not
  exist in that system's code** — its actual holdout is roughly five examples.

**What genuinely remained:** neither proposal bound the self-improvement loop to the
boundary. `evolution/` appeared in no contract, and no commit policy was stated anywhere.

## Decision

**The boundary, settled first. The commit policy follows from it.**

| | Contents |
| :--- | :--- |
| **Immutable (TCB)** | Policy engine · evaluator · gates · benchmark definitions · CI configuration · `.importlinter` |
| **Mutable by the meta-loop** | Prompts · skills · instructions · retrieval parameters |

**Commit policy.** Auto-commit is permitted **within the mutable surface**. Everything else
opens a **PR**. The loop may rewrite a prompt automatically precisely because it structurally
cannot rewrite the gate.

**Enforcement — this is the decision, not a footnote:**

1. `evolution/` is a **forbidden importer of the TCB** by named `import-linter` contract,
   landed in the same change that creates the package.
2. CI `tcb-check` rejects TCB modifications from agent-authored branches.
3. `tests/unit/test_path_constant_drift.py` fails when a TCB path constant selects nothing.

## Consequences

- Autonomy work is unblocked with a mechanically enforced ceiling rather than a policy
  document.
- Auto-commit within a bounded surface is genuinely low-risk, so this is not a conservative
  decision — it buys more autonomy than a blanket PR rule, at lower risk.

## The trap this ADR must not fall into

`.importlinter` and `ci.yml` `TCB_PATHS` currently name `src/sagiha/…`. **At the migration to
`src/aether/` neither fails — both pass vacuously**, and this ADR's guarantee evaporates
while CI stays green. The migration must land in the same change as the first `src/aether/`
commit. A contract that selects no files forbids nothing.

## Reversal Conditions

If enforcement degrades from mechanism to convention — a contract that selects nothing, an
exemption nobody re-reads, a `tcb-check` that warns instead of failing — **revert to
PR-for-everything** until the mechanism is restored. The auto-commit permission is
conditional on the enforcement being real, and is withdrawn automatically when it is not.
