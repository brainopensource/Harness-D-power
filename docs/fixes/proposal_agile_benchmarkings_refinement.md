---
status: rationale
retrieval: excluded
updated: 2026-08-06
---

# PROPOSAL — Agile & Benchmark Refinement (`docs/agile/`, `measurement.md`)

Companion to [`proposal_architecture_audit.md`](./proposal_architecture_audit.md) (defect IDs D1–D21 referenced throughout). This document does two things: critiques the M0–M3 plan as scheduled, and proposes the amended measurement protocol in ratifiable form.

---

## 1. Critique of the M0–M3 DAG and sprint plan

### 1.1 What is right

Gate-driven scheduling with tripwires (ADR-0009) is the correct synthesis and rarely executed this cleanly. The instrument track running parallel to the architecture track is correct. Sprint-01's task set is small, mechanical, and each item has a falsifiable acceptance criterion — the "if a gate is prose it is not a gate" rule is genuinely applied.

### 1.2 Structural defects, in dependency order

**(a) B4 must precede the A/A floor (D2 — the one that invalidates numbers).**
The floor's purpose is to characterize instrument variance. If exit-127 and uncollectable-test events are still scored as failures when the floor is run, the floor measures *instrument noise plus instrument error*, and every later admission decision inherits a polluted denominator. B4 is cheap — a typed `GateReport` tri-state and a result-mapping rule — and has no dependency on M2. Move it:

```
B1 ──►┐
B2 ──►├──► B4 (typed instrument error) ──► A/A floor ──► M2 ablations
      │
M0 ───┴──► M1a ─────────────────────────────► M2 ──► B3 ──► M3
```

**(b) B3's position needs a written justification, or B3 also moves.**
The `.pth` leak (B3) made candidate diffs invisible to gates. In an A/A run both arms are affected identically, so the *variance* estimate may survive — but only if the leak is arm-symmetric and does not interact with task identity. That is an assumption, and the tree's own doctrine says assumptions about instruments get canaries. Minimum fix: before the floor run, execute the B3 canary (deliberately broken candidate must fail) in the floor environment. If it passes (i.e., the broken candidate "succeeds"), the floor is blocked on B3 regardless of the roadmap.

**(c) M1a Gate 3 is unreachable from the current backlog (D15).**
Eight conformance-passing ports require eight adapters plus the conformance meta-suite plus the mock-adapter set; the backlog funds one adapter and no suite. Either the gate is re-scoped ("ModelProvider + Workspace/WorktreeManager + Evaluator conformance; remaining ports enter per ADR-0005 as their adapters land") or six adapter tasks plus TASK-005 (conformance harness) and TASK-006 (mock adapters + record/replay cassettes) are added. Recommendation: re-scope the gate *and* add the harness tasks — the walking skeleton needs only four boundaries to walk.

**(d) The pipeline has no repair edge (D7 — the competitive one).**
`retrieve → generate → apply → evaluate` terminates on first evaluation. The vision names the failing-test→context repair edge the single largest lever; every serious competitor's lift comes primarily from it. Two options:

- **M1a+**: add `evaluate →(fail, budget k)→ repair → apply` as a bounded iteration construct in the workflow model (a cycle with a static unroll bound is still expressible as a DAG: `repair₁ … repair_k`).
- **M2 gate**: "Repair loop v1 enabled; ablation repair-on vs repair-off clears the floor" becomes M2 Exit Gate 4. This is almost certainly the largest single lift contribution the project will ever measure — it should be the *first* capability ablation, ahead of the Architect/Editor seam and arguably ahead of the generated-context layer.

**(e) Tripwire arithmetic is optimistic but acceptably so.** Sum of tripwires B1→M3 ≈ 30 working days to fan-out + statistical admission. The risky entries: M2 at 7 days contains *two full ablations* (each requiring N≥floor runs on a local endpoint — wall-clock dominated by inference, not engineering) plus memoization. Recommendation: split M2's tripwire into M2-eng (memoization, 5d) and M2-abl (ablation execution, sized after the floor run reveals per-task wall-clock). A tripwire on a quantity dominated by unmeasured inference latency is itself an unmeasured number used as a gate-adjacent commitment.

**(f) Missing zeroth task (D4).** TASK-000: migrate `.importlinter` `tcb-isolation` targets and CI `TCB_PATHS` to `src/aether/…` in the same PR that creates the first `src/aether/` file; path-constant drift test must demonstrate failure on the old selection. Blocking; first PR of the sprint.

### 1.3 Sprint-01 line edits

| Item | Issue | Fix |
|:--|:--|:--|
| Task 2 | Violates ADR-0005 (D3) | Either mock adapters land in the same change per port (amend ADR-0005 to say mocks count, with the real adapter named), or Task 2 shrinks to the ports whose adapters exist this sprint |
| Task 3 gate | "zero network errors" is environment-luck, not capability | Gate: "resolves 100% of base commits for the pinned manifest of the floor task set; cache is content-addressed and offline-replayable" |
| DoD item 4 | `--max 54000` (D6) | Correct ceiling; record the change |
| Missing | TASK-000 (D4) | Add as item 0 |
| Missing | B4 typed `GateReport` | Pull from M2 into Sprint-01/02 (it is a domain type — it belongs in M0's domain work anyway) |

---

## 2. Refined SWE-bench / SWE-bench Pro protocol

### 2.1 Task manifests are TCB artifacts

Pin, per suite, a versioned manifest: instance IDs, base-commit SHAs, environment image digests, test-command hashes. The manifest is a benchmark definition and therefore **immutable TCB** (spec §6 already implies this; make it explicit — this closes the same class of hole as C18 in the Phase 0 register, the phantom `s0-core.json`). B1's repo cache is generated *from* manifests, which fixes the "12 repositories" under-scoping (D12): Verified's set is 12 repos; Pro's public set is materially larger and must be enumerated from its manifest, not assumed. (Action: verify Pro's current public repo count against the dataset at manifest-pinning time; do not import my figure — per your own rule.)

### 2.2 Contamination and overfitting controls

The current tree has no defense against benchmark overfitting, which is the standard attack on any leaderboard claim:

1. **Split discipline.** Partition each suite: DEV (ablations, loop engineering — burn freely), HOLDOUT (admission decisions only, capped at ≤ 1 evaluation per candidate mechanism), SEALED (publication runs only; each run logged; ≥ 2 mechanisms admitted between touches). Splits are pinned in the manifest; the split assignment is TCB.
2. **Anti-memorization canary.** Frontier models have seen SWE-bench repos in training. For the *lift* claim this partially cancels (both arms share the model), but for absolute claims add a small perturbed-task set (semantically equivalent, surface-rewritten issues) and report the absolute delta between original and perturbed as a contamination indicator.
3. **Pro's broken-task exposure.** ADR-0004 itself notes ~30% of public Pro tasks were estimated broken in a mid-2026 audit. Adopt a task-validity gate: a task enters the manifest only if the gold patch passes and the empty patch fails on your instrument (bidirectional canary, per-task). Tasks failing it are excluded *with the exclusion list published* — silent exclusion is the overfitting vector.

### 2.3 The lift baseline, pinned

Lift is only as defensible as its baseline. Pre-register in `measurement.md`:

- Baseline = one completion, official SWE-bench inference format, no execution feedback, no retrieval beyond the benchmark-provided context, temperature and seed pinned, same model checksum/version string as the harness arm.
- Harness arm = AETHER default config, hash-pinned.
- Both arms per manifest task; paired by task; outcome = pass@1 (see 2.4).
- Report: lift with CI, absolute both arms, cost-per-resolved-task both arms, and token totals.

### 2.4 Statistical protocol amendments (ADR-0003 rev. 2)

**(a) Power — the load-bearing amendment (D1).** Verification script and results:

```python
# Appendix A — exact McNemar power, Monte-Carlo (stdlib only)
import random
from math import comb

def exact_mcnemar_p(b, c):
    n = b + c
    if n == 0: return 1.0
    return min(1.0, sum(comb(n, i) for i in range(min(b, c) + 1)) * 2 / 2**n)

def power(N, p01, p10, alpha=0.05, iters=20000, seed=7):
    rng, hits = random.Random(seed), 0
    for _ in range(iters):
        b = c = 0
        for _ in range(N):
            u = rng.random()
            if u < p01: b += 1
            elif u < p01 + p10: c += 1
        hits += exact_mcnemar_p(b, c) < alpha
    return hits / iters
```

| True +10pt lift scenario | N=50 | N=100 | N=200 | N=300 |
|:--|:--|:--|:--|:--|
| clean (p₀₁=.12, p₁₀=.02) | 0.32 | 0.73 | 0.97 | 1.00 |
| noisy (p₀₁=.20, p₁₀=.10) | 0.18 | 0.38 | 0.70 | 0.88 |
| very noisy (p₀₁=.30, p₁₀=.20) | 0.12 | 0.25 | 0.48 | 0.66 |

At the ratified N ≥ 50, the protocol detects its own committed target 12–32% of the time — *before* the Holm–Bonferroni penalty makes it worse. As written, ADR-0003 is an engine for discarding true improvements and for demoralizing the loop-engineering cadence ("nothing clears the floor" will be the modal outcome even when things work).

**Amendment:** N is derived, not fixed. Pre-register the discordance assumption from the first A/A + baseline runs (which give you p₀₁+p₁₀ empirically), then size for 80% power at the minimal effect of interest. Tier it: N=50 smoke screen (directional only, never admits) · N≈150 admission tier for effects ≥ +10pt · N≈300 publication tier. Where cost binds, use a group-sequential design with an α-spending function so a large true effect can stop early — statistically principled and cheaper in expectation than fixed-N.

**(b) Pass aggregation (D14).** Primary outcome = pass@1 on the first seeded pass. Passes 2+ estimate per-arm flakiness, reported separately; flaky tasks (discordant within-arm) are flagged in the manifest and analyzed with and without. Never merge passes into the primary outcome post hoc.

**(c) Family declaration.** ADR-0003 already requires declaring the gate family before the sweep — add the mechanism: the family is a committed YAML in the TCB (`measurement/families/<sweep-id>.yaml`) merged *before* any arm runs; the statistics module refuses to compute corrected p-values for an undeclared family. Enforcement over discipline, per house style.

**(d) Cost criterion (D11).** Replace "cost held flat or reduced" with: cost-per-resolved-task non-inferior within a pre-declared margin (default ≤ +20%), evaluated on the same paired runs. Reconciles ADR-0003 with ADR-0007 and measures the economically meaningful unit.

### 2.5 Comparative-lift rig (the missing instrument for the mission)

Add a `HarnessUnderTest` seam to the runner (it is measurement tooling, not a port — consistent with ADR-0005's "measurement is a tool"): given (harness, model, manifest), produce paired outcomes through *your* evaluator. Arms: bare-model baseline · AETHER · OpenHands (OSS, runnable today) · others as licensing allows. Same model, same manifest, same evaluator ⇒ the only defensible competitor comparison in existence, and it converts the mission statement from marketing into a measurement. Schedule: after the floor, before any public claim.

---

## 3. Gate-driven criteria for autonomy and self-improvement phases

These extend the M-series past M3. Each gate is mechanical; each phase has a tripwire; none may weaken the TCB (all inherit I7/I8 and ADR-0006 enforcement checks as standing preconditions).

**M4 — Meta-loop v1 (prompt/skill mutation, current ADR-0006 mutable surface).**
- G4.1: `evolution/` exists; `tcb-isolation` forbidden-importer contract demonstrably fails when a TCB import is introduced in a scratch branch (negative test in CI).
- G4.2: One full mutate→evaluate→admit cycle completes with admission through the ADR-0003 (rev.2) gate on the HOLDOUT split; the admitted artifact is auto-committed within the mutable surface; the audit trail (candidate, family, p, CI, cost) is machine-readable.
- G4.3: A deliberately regressive mutation is *rejected* by the gate (the meta-loop's own canary — a self-improvement loop that cannot demonstrably reject a bad change has a gate that cannot fail).

**M5 — Workflow self-redesign (requires ADR-0014, Deliverable 3 §2).**
- G5.1: Workflow topology expressed as validated declarative data; the executor refuses graphs failing schema/static checks (type-compatible sockets, budget bounds on iteration constructs, evaluator-node non-bypassable).
- G5.2: Meta-loop proposes a topology variant; variant runs on DEV; admission via rev.2 protocol on HOLDOUT; admitted topology auto-commits *as data* within the mutable surface.
- G5.3: Tripwire on regression breadth: an admitted topology that regresses the SEALED split on its first publication run triggers automatic rollback to the prior topology (rollback path itself tested).

**M6 — Self-modification of harness code (never auto-commit).**
- G6.1: Meta-loop may open PRs against non-TCB code; CI runs the full admission protocol as a required check; human merge remains mandatory (ADR-0006 boundary unchanged — this phase changes *who writes the PR*, not who approves it).
- G6.2: Provenance labeling: agent-authored commits are marked; `tcb-check` demonstrably rejects an agent-authored TCB modification (negative test).
- G6.3: Recursive-lift metric defined: lift of (AETHER improved by AETHER) over (AETHER at M5 freeze), same manifest, same model — the first honest number for "recursive self-improvement," and the one that distinguishes the project from every competitor's marketing.

**Standing tripwire for all autonomy phases:** any admitted change whose post-hoc SEALED performance falls below its HOLDOUT admission CI lower bound twice consecutively suspends auto-commit (revert to PR-for-everything per ADR-0006's own reversal condition) until the divergence is explained. Overfitting-to-HOLDOUT is the meta-loop's dominant failure mode once the judge is unbreakable; this tripwire is its detector.
