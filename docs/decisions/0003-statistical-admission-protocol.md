---
status: normative
updated: 2026-08-06
---
# ADR-0003: Exact McNemar, Holm–Bonferroni, Derived N

**Status**: Accepted · **Date**: 2026-08-05 · **Revised**: 2026-08-06 (rev. 2) · **Fork**: F3

## Context

One proposal specified an A/A floor, exact McNemar and Holm–Bonferroni. The other specified
`p < 0.05`, `N ≥ 50` and Student's t / two-tailed permutation. Each held half of the right
answer.

Two of the objections are correctness issues, not preferences:

- **Resolve/not-resolve is a paired binary outcome.** Student's t assumes continuous,
  roughly normal data. On paired binary outcomes its p-value does not mean what it appears
  to mean.
- **α = 0.05 applied per-test across five arms is a ~23% family-wise error rate**
  (`1 − 0.95⁵`). A raw `p < 0.05` on the fifth of five arms is close to meaningless.

And structurally: **without an A/A floor, "significant" has no denominator.**

### What rev. 2 corrects

Rev. 1 adopted `N ≥ 50` as a fixed sample size. **At N = 50 the protocol cannot see its own
committed target.** Monte-Carlo simulation of exact McNemar against a true +10-point lift
(seeded, stdlib-only, re-runnable):

| Discordance (p₀₁ / p₁₀) | N=50 | N=100 | N=200 | N=300 |
| :--- | :--- | :--- | :--- | :--- |
| clean (.12/.02) | 0.32 | 0.73 | 0.97 | 1.00 |
| noisy (.20/.10) | 0.18 | 0.38 | 0.70 | 0.88 |
| very noisy (.30/.20) | 0.12 | 0.25 | 0.48 | 0.66 |

*(α = 0.05, 20,000 Monte-Carlo iterations, `seed=7`, stdlib only. Re-derivable from those
four parameters and nothing else.)*

Those are **before** the Holm–Bonferroni penalty. Holm tests the smallest p-value against
`α/m`; in a five-hypothesis family the first comparison faces α = 0.01, where N = 50 yields
**0.04–0.11 power**.

A protocol that rejects nine true improvements in ten is not conservative. It is an engine
for discarding real work, and its modal output — *"nothing clears the floor"* — is
indistinguishable from a harness that does not work. That is the same failure class as a
gate that cannot fail, pointed the other way, and it would have been ratified as rigour.

**N was the wrong thing to fix.** Power depends on the discordance rate, which is a property
of the instrument and is not known until the A/A floor and baseline runs have been taken. A
number chosen before that evidence exists is exactly the kind of number this project does
not admit.

## Decision

| Element | Choice |
| :--- | :--- |
| Design | Paired — same tasks, same order, same seeds where seeds exist |
| Statistic | **Exact McNemar** |
| Multiple comparisons | **Holm–Bonferroni** across the pre-declared gate family |
| Threshold | **α = 0.05 family-wise**, not per-test |
| Sample | **Derived, not asserted** — see below |
| Primary outcome | **pass@1 on the first seeded pass** |
| Intervals | Seeded bootstrap CI, 2000 iterations |
| Effect size | Paired difference in resolve rate with CI, plus cost per resolved task |
| Cost criterion | **Cost per resolved task non-inferior within a declared margin** |

### 1. N is derived

N is computed, per family, from four pre-registered quantities: the **discordance assumption**
(p₀₁, p₁₀, taken from the A/A floor and baseline runs, cited in the PR), the **minimal effect
of interest**, **target power ≥ 0.80**, and the **Holm-adjusted α at that hypothesis's rank in
its family**. The power simulation is seeded and re-runnable from the family file alone.

Tiers name a **role and a floor**, never a value. The derived N governs:

| Tier | Floor | Split | Admits? |
| :--- | :--- | :--- | :--- |
| **Smoke** | N ≥ 50 | DEV | **Never.** Directional signal only |
| **Admission** | N ≥ 150 | HOLDOUT | Yes, at ≥ 0.80 derived power |
| **Publication** | N ≥ 300 | SEALED | Yes, with the full report |

A sweep whose derived N exceeds its budget may use a **group-sequential design** with an
α-spending function (O'Brien–Fleming or Pocock), which stops early on a large true effect and
is cheaper in expectation than fixed-N. It may not lower the target power instead.

### 2. Passes do not aggregate

The primary outcome is **pass@1 on the first seeded pass**. Additional passes estimate
**within-arm flakiness**, are reported separately, and are **never merged into the primary
outcome**. Tasks discordant within an arm are marked `flaky` in the manifest and analysed with
and without. Rev. 1's *"≥ 2 passes per arm"* named no aggregation rule, which left pass@1 /
pass@k / majority open to selection after seeing results — the p-hacking surface a diligence
review probes first.

### 3. The family is declared mechanically, not by discipline

The gate family is a **committed YAML file in the TCB** (`measurement/families/<id>.yaml`,
schema in [`../development/schemas_and_contracts.md`](../development/schemas_and_contracts.md) §3)
merged **before any arm runs**, with `registered_commit` proving it. `statistics.py` **refuses
to compute corrected p-values for an undeclared family**. Adding a hypothesis after
registration produces a new family file with a new hash; there is no amend.

### 4. Cost is measured per resolved task

Admission requires **cost per resolved task non-inferior within a pre-declared margin
(default ≤ +20%)**, evaluated on the same paired runs. Rev. 1 required raw cost *"held flat or
reduced"*, which contradicted [ADR-0007](./0007-architect-editor-seam.md) — the Architect/Editor
seam roughly doubles per-task cost and is admitted on an *"acceptable cost delta."* Under the
old wording a mechanism that doubled cost while tripling resolves was inadmissible. Cost per
resolved task is the economically meaningful unit and reconciles both ADRs.

### 5. Implementation

Ported **verbatim** from the predecessor's `e0/statistics.py` — 259 LOC, pure stdlib, pinned
JSON fixtures, provenance in the module docstring per [`../spec.md`](../spec.md) §9. It is the
one component whose claimed properties verify line by line. The rev. 2 additions — derived-N
simulation and the family gatekeeper — are new code around it, not edits to it.

**Null results are recorded as "no signal at this tier"** — a property of the measurement, not
a verdict on the mechanism. They re-enter at a higher tier.

## Consequences

- **The A/A floor must be taken before any admission N can be computed.** The floor is not
  only the denominator for significance; it is the input to the sample-size calculation. This
  strengthens [ADR-0002](./0002-no-number-before-the-floor.md) rather than complicating it.
- Admission runs are materially more expensive than rev. 1 implied. That cost was always
  there — rev. 1 simply did not buy the power it appeared to.
- The declared family is a TCB artifact, so **the meta-loop cannot widen its own family**
  ([ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md)).

## Reversal Conditions

If a benchmark's outcome type stops being binary — partial credit, graded rubrics — McNemar no
longer applies and the statistic is reselected for the new outcome type. Holm–Bonferroni and
the family-wise α survive that change.

**On the derived-N rule specifically: none.** Reverting to a fixed N re-creates a protocol
whose power is unknown at the moment it is used, which is the defect rev. 2 exists to close.
The tier floors (50/150/300) are revisable by measurement; the requirement that N be *derived
and its power stated* is not.
