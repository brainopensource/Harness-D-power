---
status: rationale
updated: 2026-08-07
---

# Self-Improvement — The Meta-Loop, Designed

**Design of record for M6 (H3).** Ratified in principle by
[ADR-0019](../decisions/0019-three-horizons-harness-framework-metaloop.md); the safety spine is
[ADR-0020](../decisions/0020-verdict-capability-and-judge-integrity.md).

Four ADRs reference a meta-loop — [0006](../decisions/0006-tcb-boundary-and-meta-loop-authority.md)
(its authority), [0013](../decisions/0013-workflow-dag-phased.md) (its phasing),
[0014](../decisions/0014-workflow-topology-is-data.md) (its stated *raison d'être*),
[0017](../decisions/0017-subagent-capability-attenuation.md) (its attenuation) — and none
designs it. This document does.

---

## 1. Why nobody has closed this loop

The survey is unambiguous, and the pattern is the finding:

| System | Self-improvement machinery | Why it stops |
| :--- | :--- | :--- |
| **Hermes** | A **real** GEPA/DSPy loop: synthetic + mined eval sets, `FitnessScore(correctness, procedure, conciseness, length_penalty, feedback)`, hard constraint gates before promotion | Phase 5 "continuous loop" is a **one-line empty file**. It never opens a PR. Scope is skill *text* only |
| **Grok** | `/dream` — auto-consolidates memory, gated on hours + session count | Reorganises memory content; modifies **no** prompt, skill or config |
| **OpenHands** | Critic scores, `/goal` judge loop, versioned agent-profile revisions, `enable_iterative_refinement` | Every loop is **within-run** (redo this task), never **across-run** (change how you do tasks) |
| **Kimi** | None | — |

Every one has the *primitives*. None has the loop. **The missing piece is the same in all four:
a judge they can trust enough to let it promote a change.**

Hermes is the sharpest illustration — it ships an LLM `FitnessScore` with **no constraint
preventing it from promoting a variant on its own score.** That is a system that can drift into
grading itself, and it is why its authors stopped at Phase 1.

**This project is built around that judge.** ADR-0002, the A/A floor, derived N, the family
gatekeeper, I7, I9 — the whole apparatus that has looked like overhead for four sprints is the
precondition for H3. The meta-loop is not a new subsystem; it is the payoff.

---

## 2. What the meta-loop is

**A proposer over data, and nothing else.** It emits candidate mutations of T0–T2 artifacts
(`extension_contract.md` §1) — parameters, roles, topologies. Those are exactly the artifacts
that **cannot widen capability**, because registries are frozen at composition (I6).

```
              ┌──────────────────────────────────────────────────────────┐
              │ TRAJECTORY STORE  (already built, append-only, replayable)│
              └───────────────────────────┬──────────────────────────────┘
                                          ▼
   ┌── PROPOSE ────────────────────────────────────────────────────────────┐
   │  mutate a role / topology / prompt · record `ancestry.parent_hash`     │
   │  MAY NOT: touch TCB · edit a rubric · change a manifest · self-admit   │
   └───────────────────────────┬───────────────────────────────────────────┘
                               ▼
   ┌── SCREEN (cheap, DEV) ────────────────────────────────────────────────┐
   │  validator (5 static checks) · smoke N · memoized subtrees             │
   │  most candidates die here, for free                                    │
   └───────────────────────────┬───────────────────────────────────────────┘
                               ▼
   ┌── ADMIT (expensive, HOLDOUT) ─────────────────────────────────────────┐
   │  family DECLARED FIRST · derived N ≥0.80 power · exact McNemar         │
   │  Holm–Bonferroni · cost per resolved task · ADMITTING verdict required │
   └───────────────────────────┬───────────────────────────────────────────┘
                               ▼
                    ADMIT ──► pin, record ancestry
                    REJECT ─► DELETE. Never "keep, disabled"
```

**The four constraints, in order of how badly each fails if dropped:**

1. **It may never admit its own variant.** Admission runs through the same statistics gatekeeper
   as a human proposal — family declared before any arm runs, derived N, Holm-corrected. The
   proposer does not get a vote.
2. **It may never edit a judge.** Rubrics, judge model fingerprints, judge prompts, manifests and
   split assignments are TCB data pinned by hash. `judge_unmodified` (ADR-0020 §2) applies to
   the meta-loop exactly as it applies to a task candidate.
3. **A rubric verdict may not admit alone** (I9 rev. 2). Where a variant's outcome is
   LLM-judged, promotion additionally requires a deterministic or human admitter. **A
   self-improving system whose judge is an LLM it also influences has no fixed point.**
4. **Rejected variants are deleted, not disabled.** `TASK-025`'s rule — *a disabled code path
   nobody measures is debt, not optionality* — and it matters more here, because a proposer
   generating variants faster than humans read them turns a graveyard into the codebase.

---

## 3. The autonomy ladder, and what each rung already costs

| Rung | Mutation | Form | Authority | Built by |
| :---: | :--- | :--- | :--- | :--- |
| 4 | New capability implementation | **CODE** | Human PR + TCB review | — |
| 3 | New role — sources, parser, prompt | DATA | Meta-loop, ancestry-tracked | M1b + M5 |
| 2 | New topology / fragment | DATA | Meta-loop (ADR-0014) | ✅ M1a |
| 1 | New prompt / retrieval params | DATA | Meta-loop (ADR-0006) | ✅ partly |
| 0 | New arm — routes, manifest, seed | DATA | Meta-loop, admission-gated | M4 |

ADR-0014 stated the problem this ladder solves: *"the only mechanical path from where we are to
machine self-redesign runs through arbitrary code modification — the most dangerous grant in the
system, and the first one we would be forced to hand out. The intermediate rung is missing."*
Rungs 0–3 **are** those intermediate rungs, and each is data.

**Rung 4 stays human, permanently.** Not because machine-written capabilities are unimaginable,
but because a system that can write its own capability implementations can write one that reads
the rubric — and every guarantee below collapses at once.

---

## 4. What it proposes, cheapest-first

| # | Mutation | Search space | Screen cost | Precondition |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Prompt / role-text | Large, continuous | Smoke N on DEV | `RoleSpec` as data (M1b) |
| 2 | Source list in a role | Combinatorial, small | Smoke N | `ContextSource` registry (M5) |
| 3 | Retrieval params (hops, budgets, k) | Continuous, bounded | Smoke N | `TASK-064` |
| 4 | Topology structure | Discrete, validator-constrained | Validator, then smoke | ✅ ADR-0014 |
| 5 | Per-node model routing | Small, priced | Smoke + cost | `TASK-042/043` |

**Start at 1 and 2.** They have the largest effect per unit of risk, they are pure text and id
lists, and Hermes's evidence is that prompt-level optimisation with a feedback-carrying fitness
signal genuinely works (its `FitnessScore.feedback` field exists specifically to drive GEPA's
reflective mutation — worth adopting; it is what makes mutation directed rather than random).

**Structural mutation (4) comes last** even though it is the most exciting, because the search
space is where the validator's five static checks do the most work and the failure modes are
least understood.

---

## 5. What it never touches

```
NEVER MUTABLE, at any rung:
  kernel/ · measurement/evaluator.py · workflow/{executor,validator}.py
  workflow/schemas/ · measurement/schemas/ · .importlinter · .github/workflows/
  benchmarks/manifests/ · measurement/families/ · every rubric and judge prompt
```

Enforced by three mechanisms that already exist: `tcb-isolation` (import direction),
`TCB_PATHS` + the drift test (file set), and `judge_unmodified` (content). **Three, because one
is a policy, two is a policy with a backup, and three is an invariant.**

`evolution/` is declared in `spec.md` §3 as *offline only, never imported by anything*, with its
own contract entry — and `aether.evolution` is currently a `tcb-isolation` target **that does not
exist**, making that contract target vacuous. Creating the package is therefore both the first
M6 task and the closing of a known gap.

---

## 6. Prerequisites, and why each is not negotiable

| Needs | Why |
| :--- | :--- |
| **A/A floor** (Sprint 4) | Without it "improved" has no denominator |
| **Capability layer** (Sprint 5) | Rung 3 needs roles to *be* data before they can be mutated |
| **Memoization** (`TASK-032`) | A proposer generates variants faster than a full re-run can score them; unchanged subtrees must skip |
| **Cassettes** (`TASK-006`) | Deterministic replay is what makes screening cheap enough to be worth doing |
| **Extension contract** (M5) | Defines the T0–T2 surface the proposer may write to |
| **Framework verdicts** (M5) | A proposer over `code_fix` alone can only optimise one task type into a local maximum |

**Note what is on that list: the entire roadmap.** M6 is not a bolt-on. Every earlier milestone
is a precondition, which is why H3 is third and why attempting it earlier is a violation of
ADR-0019 rather than an acceleration of it.

---

## 7. Exit gates (M6)

1. `evolution/` exists, imports no higher than `ports/`, is imported by nothing, and the
   `tcb-isolation` target is **no longer vacuous**.
2. The proposer emits a valid T1/T2 mutation with `ancestry.parent_hash` recorded — the schema
   field already exists in `workflow_schema.yaml`, written for exactly this.
3. **Negative test: a proposed mutation touching any path in §5 is refused**, and removing the
   check makes the suite go red.
4. **Negative test: a proposer-generated variant cannot be admitted by the proposer.** An
   admission attempt without a declared family and derived N is refused.
5. **Negative test: a rubric-only family cannot admit** (I9 rev. 2).
6. One variant completes the full cycle — propose → screen → admit-or-delete — with its family,
   derived N, Holm-corrected p-value, cost per resolved task and ancestry all recorded.
7. A rejected variant is **absent from the tree**, not present and disabled.

**Four of seven gates are negative tests.** That ratio is the point: at H3 the interesting
question is not whether the loop can improve something, it is whether it can be stopped from
improving the wrong thing.

---

## 8. What this does not claim

- **No capability claim.** No variant has been proposed, screened or admitted.
- **No timeline.** M6 follows M5 follows the floor; ADR-0009 forbids turning an unmeasured
  duration into a schedule.
- **No AGI claim.** This is a bounded optimiser over four declarative artifact types with a
  human-only rung 4 and a judge it cannot touch. That is the honest description, and the
  ambition is served better by it than by a larger word.
- **It does not make rung 4 safe.** It makes rung 4 *unnecessary* for the mutations worth
  making — which is a different and achievable thing.
