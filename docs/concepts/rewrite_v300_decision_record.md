---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Phase 0 Decision Record

**Status: RATIFIED 2026-08-05.** All twelve forks and the workflow DAG are decided. The
alignment meeting was held with the Project Lead holding both Tech Lead positions, on the
evidence in the [audit register](./rewrite_v300_phase0_audit_register.md) — which had
already resolved F5 outright and narrowed F2 and F6 to the point where the remaining
disagreement was small enough to settle without further contest.

**Each decision is now an ADR** under [`docs/decisions/`](../decisions/README.md), with its
reversal condition. Those ADRs are binding; this file is the record of *how* the decisions
were reached and stops being edited.

> **What ratification does not buy.** Deciding F1 does not make Python fast, and deciding
> F4 does not verify a leaderboard. Three decisions below are explicitly provisional and
> name the measurement that will confirm or overturn them. A decision with a reversal
> condition is a hypothesis with a commit date, not a conclusion.

**Inputs.** The corrected [decision brief](./rewrite_v300_decision_brief.md), the
[audit register](./rewrite_v300_phase0_audit_register.md), both proposal sets, and the
competitor teardowns. The audit changed the shape of the agenda: **F5 is not contested, and
F6 and F2 are materially narrower than the original framing.**

**On ratification, this file becomes the record and
ADR Part IIc (`docs/_archive/rationale/rewrite/rewrite_v300_decisoes_adr.md`) becomes history.**
Two live registers of the same forks is how the DAG went three plans without a vote.

**Every row carries a reversal condition.** A decision without one is a preference with
better formatting — and Track B's 14 ADRs carry zero, which is the single most fixable
process gap Phase 0 produced.

---

## Part 1 — The three that need the room

### F1 · Compiled core

**Recommendation: instrument-then-decide.** Python-first. No `core_rs/` at Sprint 0. Two
timers — worktree creation, AST parse-and-validate — land in the first working slice, and
the number picks the side.

**Why not either track's position.** Neither may cite a number, because neither has one.
Track B's `<50 ns` / `<10 ms` / `0 ms` are bare and used as *sprint acceptance gates*; Track
B contradicts itself, putting the same parse at *"em milissegundos"*
(`decisoes_runtime_B.md:43`); and the external figures that would justify a Sprint 0 Rust
core appear nowhere in `src/grok_build/`. **Track A is no better off**: the runtime §1
latency table is the load-bearing argument for A-002 and carries no benchmark, no hardware
and no citation. Track A's own comparison calls its position *"safe and, from a builder's
perspective, evasive."*

This is not splitting the difference. It is the only position with a defensible evidentiary
basis, and it costs one afternoon. The archive is silent on F1 — the *only* fork with
nothing to say to it — which is precisely why it needs a measurement rather than a debate.

**What binds.** RT-1 (cold index >10 min on 1M LOC), RT-2 (RSS >300 MB or idle CPU >1%),
RT-3 (incremental re-index >200 ms) remain the triggers, with one amendment that fixes
Track A's evasion: **a trigger nobody has instrumented cannot fire.** Each RT must have a
named measurement before it counts as a trigger.

**Reversal condition.** A measured number crossing RT-1/2/3 on real hardware, recorded in
`docs/benchmarks/results/`, promotes exactly the component that crossed it — never the
whole core. Wire-serializable ports (I3) are what keep this cheap; that is the invariant
paying for itself.

---

### F2 · May a capability number be published before the A/A floor exists?

**Recommendation: no. And the fork is narrower than framed.**

**What is actually contested is sequencing, not concept.** Track B commits to measuring the
A/A floor in Sprints 0–1 (`roadmap_sprints_B.md:22`) and lists its absence as a defect
(`auditoria_sagiha_B.md:31`). Both tracks want the floor. The disagreement is whether a
number may be published before it exists.

**The archive settles it, at the predecessor's expense.** `concept_review.md` names
*"sequencing measurement last"* as the **primary conceptual failure**; H1 in the refactor
plan is measurement honesty; and the isolation leak made candidate diffs invisible to the
gates scoring them — an instrument that produced numbers while not measuring what it
claimed. This is a post-mortem, not a preference.

**The rule, stated narrowly enough to be implementable:**

- **B1 starts now.** Standalone, no AETHER dependency, and it unblocks every number.
- **B3 and B4 arrive with the components they isolate** — the evaluation container and the
  gate respectively.
- **No capability number is published before the floor is.** Until
  `docs/benchmarks/results/noise-floor.md` holds a real number, the project reports no
  results — which is the current and correct state.

**Explicitly not** *"fix everything before writing code."* Two independent reviewers have
already made that error, and it is not implementable.

**Adopt Track B's N ≥ 50.** Track A already concedes this in `measurement_strategy.md`
§5b.1: *"Track B's N ≥ 50 is the better half of its protocol and Track A should adopt it
explicitly."* `≥2 passes per arm` is vaguer than it should be given Tier 0 makes passes
free.

**Reversal condition.** None. If this is wrong, the project has no way to know anything.

---

### F6 · What may the self-improvement loop modify, and may it commit?

**Recommendation: settle the boundary; commit policy follows. The fork is roughly half as
wide as it was framed.**

**Correction first.** Track B **does** define the TCB — `kernel/` is labelled *"Trusted
Computing Base (TCB)"*, I7/I8/I9 appear verbatim at `blueprint_arquitetura_B.md:163-165`,
and ADR-12 adopts `tcb-isolation`. The auto-commit quote attributed to Track B is not in
Track B's text. The competitor evidence behind the strong version **inverted its source**
(Hermes ships `create_pr: bool = True` and *"never direct commit"*) and **fabricated** a
`p<0.05 / N≥50` gate that does not exist in Hermes' code.

The underlying argument is untouched by any of that: an optimizer whose mutable surface
includes its evaluator has one dominant strategy — weaken the judge — and no downstream
statistics detect it, because the statistics are computed by the thing being weakened.

**The residual gap, which is real:** Track B never binds the loop to the boundary.
`evolution/` appears in no import-linter contract, and no commit policy is stated anywhere.

**Proposed boundary.**

| | Contents |
| :--- | :--- |
| **Immutable (TCB)** | Policy engine · evaluator · gates · benchmark definitions · CI configuration · `.importlinter` |
| **Mutable by the loop** | Prompts · skills (`SKILL.md`) · instructions · retrieval parameters |

**Proposed commit policy, downstream of the boundary as the brief argues.** Auto-commit
permitted **within the mutable surface**; PR-not-commit for everything else. The loop may
rewrite a prompt automatically precisely because it structurally cannot rewrite the gate.
This is also what Hermes actually does, so adopting it costs nothing in ambition.

**Enforcement — and this is the part that must not be waved through.** `evolution/` enters
`tcb-isolation` as a forbidden importer of the TCB, in the same change that creates it.
**Today's enforcement is already a trap:** `.importlinter` and `ci.yml` `TCB_PATHS` both
name `src/sagiha/…`. At the migration to `src/aether/` neither fails — **both pass
vacuously**, and F6's guarantee evaporates silently. `tests/unit/test_path_constant_drift.py`
now catches it; the migration still needs an owner.

**Reversal condition.** If enforcement degrades from mechanism to convention — a contract
that selects nothing, an exemption nobody re-reads — revert to PR-for-everything until the
mechanism is restored.

---

## Part 2 — Resolved by the audit

### F5 · Port count and entry rule — **close as agreed**

Both tracks wrote the same rule. Track B: *"Aceitar a **Regra A-010 da Track A**: iniciar o
`src/aether/ports/` com 8 portas essenciais"* — in its audit, its ADR debate table, its
Sprint 0 deliverable and its first Gantt bar. Track B independently invokes the rule to
delete `advisory.py`.

**Decision: 8 ports, adapter-first.** `ModelProvider` · `Workspace` (+`WorktreeManager`) ·
`ToolRegistry` · `PolicyEngine` (TCB) · `TrajectoryStore` · `Evaluator` (TCB) · `Indexer` ·
`ResourceGovernor`. Growth tier arrives with adapters: `CodeGraph`, `Memory`, `Toolchain`,
`CandidateSearch`, `LSPAdapter`, `Advisory`.

**Worth 60 seconds anyway:** Track B's own preference was 9 (with `Memory` and `CodeGraph`
from the foundation) before it capitulated. Confirm the capitulation is genuine.

**Reversal condition (A-010, unchanged).** A port with two independent adapters planned in
the same phase may be introduced ahead of the first, with the second named.

### Workflow DAG — **premise wrong; nothing to decide**

The DAG did not vanish without a vote. **A-024 re-sequenced it deliberately**: M0 types
only, M1a four-node linear graph, M2 per-node memoization, M3 branching. It carries a
reversal condition — collapse to a sequential pipeline if the abstraction is not carrying
weight at M2, *"four nodes are cheap to un-abstract; forty would not be."*

**Decision: keep as A-024 specifies.** The question is only whether anyone wants to overturn
it. Correct the premise and move on.

---

## Part 3 — The remaining nine, decided

Assigning owners to these would have deferred nine decisions that the evidence already
settles. Each is decided; each has an ADR and a reversal condition.

| Fork | Decision | ADR |
| :--- | :--- | :--- |
| **F3** Statistical protocol | **Exact McNemar** for paired binary outcomes, **Holm–Bonferroni** across the gate family, **N ≥ 50**, A/A floor first. Track B's Student's t is not a preference difference — on paired binary data its p-value does not mean what it appears to mean; and α per-test across five arms is a **~23% family-wise error rate**. Track B's N ≥ 50 is the better half of its protocol and is adopted. `e0/statistics.py` ports verbatim — 259 LOC, the one component whose claimed properties verify line by line | [0003](../decisions/0003-statistical-admission-protocol.md) |
| **F4** Benchmark targets | **Lift is the committed target; absolutes are provisional.** Lift ≥ +10 points, published with every absolute number and never without it. Absolutes adopted from Track B (Verified ≥90%, Pro ≥60%, Terminal-Bench ≥75%) as the committed gate, Track A's (Pro ≥80%, Verified ≥96%) as stretch — **both flagged provisional pending re-verification**, because the re-baselining behind them is single-session research its own author flags as unverified. Inverting the priority costs nothing: lift is what the harness moves, and it survives a model swap and a leaderboard reshuffle | [0004](../decisions/0004-benchmark-targets.md) |
| **F7** Architect/Editor | Build the seam Track B specifies (`architect.py` / `editor.py` decoupled), bind *enablement* to config as Track A specifies. **Ships off**, behind an M2 ablation. Track B already proposed a config switch, so the gap was narrower than the fork implied. It roughly doubles per-task cost and the evidence is mixed — that is exactly what an ablation is for | [0007](../decisions/0007-architect-editor-seam.md) |
| **F8** Shell AST | **The mechanism was never contested; the claim attached to it was.** Build the parser, wire it to the `Reject \| AskRuleMatch \| AskFailClosed` taxonomy, and state in the ADR that its purpose is **classification and escalation, never containment**. The sandbox is the perimeter. A control that looks like security invites the real security to be removed | [0008](../decisions/0008-shell-ast-classifies.md) |
| **F9** Schedule form | **The gate decides when a phase ends; the calendar decides when to worry.** Indicative durations are tripwires, not commitments. A phase running 50% over is a signal to re-scope, not a reason to skip its gate | [0009](../decisions/0009-gates-are-the-schedule.md) |
| **F10** Static repo context | **Five layers, and the generated repo layer is the first M2 ablation.** Neither track has evidence; both treated a generated context layer as obviously valuable. arXiv 2602.11988 measured that category as *negative-value* when generated (~−3%) and positive when human-written (~+4%). Ships enabled, ablated early, deleted if it loses | [0010](../decisions/0010-context-prefix-layers.md) |
| **F11** LSP | **No LSP.** Tree-sitter for syntax; the T2 semantic tier is served by invoking the project's own linters and type-checkers directly — cheaper, less stateful, and already required to exist. `LSPAdapter` is not a port and does not appear in the tree. Track B was right, and its reasoning (instability, cost) understated the better argument | [0011](../decisions/0011-no-lsp-adapter.md) |
| **F12** IP protection | **Compilation is packaging, not architecture.** Deferred to a packaging phase with no architectural footprint. Corroborating: Grok Build ships a native Rust binary and still obfuscates only its prompt text, with a trivially reversible XOR generated by a build script. The moat is the measured harness | [0012](../decisions/0012-ip-protection-is-packaging.md) |

### Non-architectural, carried into the backlog

| Item | State |
| :--- | :--- |
| Docs word budget | **Fixed.** Root cause was a path prefix, not content |
| 19 dead links | **Fixed.** All were `../../` one level short |
| Path-drift test | **Added** — `tests/unit/test_path_constant_drift.py` |
| `benchmarks/definitions/s0-core.json` absent → `bench-aa` is a permanent no-op | **Open.** Held as a strict `xfail`; the suite has to be built. Belongs with B1 — same work, same sprint |
| `TCB_PATHS` / `tcb-isolation` go vacuous at the `src/aether/` migration | **Open, and it gates ADR-0006.** Must land in the same change as the first `src/aether/` commit, or F6 is enforced by nothing |
| 8 competitor proposals never adjudicated (P7, P8, P15, P32, P38, P42, P43, P44) | **Open.** None blocks Sprint 1; they are backlog candidates, not decisions |

---

## Part 4 — Starts Monday regardless

Not blocked by any fork. **The first blocks everything downstream.**

1. **B1 — the upstream repository cache.** Clone, SHA-pin and reuse the 12 SWE-bench task
   repositories. Standalone utility, no AETHER dependency. `src/sagiha/e0/repo_cache.py`
   (99 LOC) is the starting point; the defect is that the runner resolves
   `git worktree add <base_commit>` against the *local* repo, which is why all 30 tasks
   failed `fatal: invalid reference:` and the 2026-08-01 run produced nothing.
2. **The mock adapter set.** 100 turns in 50 ms, no API calls, no containers — what makes
   fast iteration real rather than aspirational.
3. **Two timers.** Worktree creation and AST parse-and-validate. Settles F1 with a number.

### Experiment protocol

No proposal wrote one, and the prototyping role has no contract without it.

- Experiments live **outside `src/aether/`**, are **exempt from the invariants**, and are
  **deletable**.
- An experiment produces **a number and a recommendation**. It becomes a decision only
  through an ADR with a reversal condition.
- **An experiment that shows nothing is recorded as showing nothing.** That rule is the one
  that would have saved the predecessor.

### Standing rules, whatever is decided

- Every gate ships with a test proving it **can fail**.
- Stubs raise; they never return a plausible value.
- Gates are tri-state — `True` / `False` / `None`, where `None` means *unmeasured* and never
  silently passes.
- No mechanism promotes to production without an ablation clearing the noise floor.
- `docs/STATUS.md` makes zero claims unsupported by a line-level code read. On day one it
  says *nothing is implemented*, and that is correct content.
- No external code enters `src/aether/`. Concepts and published theory transfer;
  implementation does not.

---

## Limits of this ratification

- **One person held all three roles.** The two proposals were written independently, and the
  audit checked both against their sources — but the adjudication had no adversary. The
  decisions most exposed to that are the ones where I ratified the position I had also
  argued for: F1's third option, and F10. Both carry early ablations for exactly that reason.
- **Three decisions are provisional by construction.** F1 is settled by two timers that have
  not run. F4 rests on a leaderboard re-baselining nobody has re-verified. F10 ships a layer
  the literature suggests may be negative-value. Each names the measurement that overturns it.
- **The archive's fork mappings were Track A's reading throughout.** Where the archive was
  described as "decisive" (F2) or "strong" (F3, F5, F6), that grading was never independently
  checked. F2's grading survives contact with the primary sources; the others were not
  load-bearing once the audit narrowed the forks.

**Where this goes next.** The decisions are ADRs under [`docs/decisions/`](../decisions/README.md);
what is *true* is [`docs/spec.md`](../spec.md). This file is history from here on — two live
registers of the same forks is how the DAG went three plans without a vote.
