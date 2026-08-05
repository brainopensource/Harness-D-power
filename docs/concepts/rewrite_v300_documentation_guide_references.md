---
status: rationale
updated: 2026-08-05
retrieval: excluded
---

# Phase-0 Review Reference Guide — what the prototype taught us

**Purpose.** The prototype phase produced ten audits and specs, now under
`docs/_archive/rationale/reviews/`. This guide does three jobs:

| For | Use |
| :--- | :--- |
| **Onboarding briefing** | §1 inventory + §2 per-document summaries + §4 top lessons |
| **The A/B decision meeting** | **§3 — which historical finding bears on which contested fork** |
| **Backlog & sprint planning after the meeting** | **§5 — which findings carry forward to greenfield, and which are moot** |

Companion documents, not duplicated here: the project vision brief (the mission in 10 minutes) and
[`rewrite_v300_decision_brief.md`](./rewrite_v300_decision_brief.md) (the meeting agenda).

> **Read the archive as history, not as instructions.** These reviews audit `src/sagiha/`, which is
> being retired. A finding is useful here only if §5 marks it as carrying forward.

---

## 1. Inventory

| Document | Scope |
| :--- | :--- |
| `README.md` (`docs/_archive/rationale/reviews/README.md`) | Audit taxonomy and finding-ID conventions |
| `Harness_LLM_orchestrator_aether_project_review_v210.md` (`docs/_archive/rationale/reviews/Harness_LLM_orchestrator_aether_project_review_v210.md`) | **Audit of record.** Actual title: *"SAGIHA v2.1.0 — Post-Remediation Audit & Forward Architecture Plan."* Verifies the W0–W8 remediation, then lists open defects using `N-C<n>` (critical) / `N-H<n>` (high) IDs |
| `concept_review.md` (`docs/_archive/rationale/reviews/concept_review.md`) | Retrospective: what the prototype got right vs. what failed conceptually |
| `critical_gaps_analysis.md` (`docs/_archive/rationale/reviews/critical_gaps_analysis.md`) | Architectural audit · competitive capability gap matrix · technical-debt register · a dialectical "should this survive?" close |
| `codebase_delta_refactor.md` (`docs/_archive/rationale/reviews/codebase_delta_refactor.md`) | Refactoring plan for findings **H1–H4** |
| `next_gen_architecture_specs.md` (`docs/_archive/rationale/reviews/next_gen_architecture_specs.md`) | v2→v3 spec: tiered self-improvement, dynamic context assembly, AST-aware edits |
| `prompt_review.md` (`docs/_archive/rationale/reviews/prompt_review.md`) | System-prompt structure, instruction budget, tool-schema clarity |
| `agi_evolution_path.md` (`docs/_archive/rationale/reviews/agi_evolution_path.md`) | The System-3 "Conductor" long-horizon layer |
| `review_project_rewrite_v300.md` (`docs/_archive/rationale/reviews/review_project_rewrite_v300.md`) | **Track A RFP charter.** Mandates 9 deliverables; Track A shipped 12 (the 9 plus three additions) |
| `review_project_rewrite_v300B.md` (`docs/_archive/rationale/reviews/review_project_rewrite_v300B.md`) | **Track B RFP charter.** Body names 9 expected deliverables; its §5 checklist lists 5. Track B shipped the 5 |

**Corrections to an earlier draft of this guide**, recorded so nobody greps for IDs that do not exist:
the audit of record uses **`N-C1`/`N-C2`/`N-C3`**, not "D1–D18"; `critical_gaps_analysis.md` contains
**no `G1–G10` scheme** — it is organized by section, not by numbered finding; and RFP A mandates
**9** deliverables, not 12.

---

## 2. Per-document insights

### `agi_evolution_path.md` — the Conductor
1. **A pilot and a scheduler; never an executor.** The Conductor owns time, attention and knowledge. It
   holds **zero tools, zero shell, zero capability grants**. Every effect is a task submitted down one
   port.
2. **Three timescales.** System 1 (ReAct) — seconds. System 2 (Best-of-N + repair) — minutes.
   System 3 (Conductor) — hours to weeks.
3. **Hibernation is durable absence, not sleep.** State serializes to SQLite and **the process exits**.
   A design that keeps a process alive for eight hours has narrowed the failure window, not closed it.
4. **Memory distillation has an evidence bar.** A raw trajectory becomes a guideline only with support
   from multiple admitted, taint-free runs — not from one impressive session.
5. **One rejection worth preserving:** a Conductor-resident hypothesis DAG at depth >1 is Monte Carlo
   tree search re-entering through the side door, and the cost analysis that rejected MCTS is not
   voided by renaming the tree.

### `concept_review.md` — keep vs. failed
**Keep:** the single dispatch choke point · the tri-state `GateReport` (`True`/`False`/**`None`**,
where `None` means *unmeasured* and never silently passes) · refuse-at-load config validation ·
boring storage (SQLite + tree-sitter, no daemons).

**Failed:** *sequencing measurement last* — capability shipped without proof of value, and every
number taken had to be discarded. And *plausible fallback lies* — swallowing an exception and
returning `[]` renders failure indistinguishable from "no results".

### `critical_gaps_analysis.md` — the gaps
Non-linear context degradation past ~70% of budget, so compaction triggers early rather than at
overflow · untrusted content must carry provenance or injection launders into trusted context · ports
without adapters are un-tested abstractions and must not exist.

### `next_gen_architecture_specs.md` — the mechanisms
Layered prompt prefix for cache stability · anchored search/replace with whitespace tolerance beats
line-number diffs · tree-sitter parse **before** disk write keeps syntax errors out of the test loop.

### `codebase_delta_refactor.md` — H1–H4
H1 measurement honesty (no dummy pass rates) · H2 budget reserved *before* execution, not recorded
after · H3 replay determinism byte-for-byte · H4 structural debt.

### `prompt_review.md` — the prompt budget
Adherence degrades past roughly 150 distinct directives · rule quality beats rule quantity · tool
schemas are paid on every call, so loading them on demand is a real lever.

### The audit of record (`…v210.md`)
The most useful part is not the defect list — it is §1.2, *"the tree is red right now, and it
regressed after W8."* A remediation that verified green and then regressed is the argument for
mechanical enforcement over discipline, and it is why every invariant in the v3 plan has a named CI
job rather than a convention.

---

## 3. Which finding bears on which contested fork

**This is the section for the A/B decision meeting.** Forks are defined in
[the decision brief](./rewrite_v300_decision_brief.md) §Block 2. The value of the archive in that
room is that several forks are not open questions — the prototype already answered them at its own
expense.

| Fork | What the archive says | Strength |
| :--- | :--- | :--- |
| **F2** — instruments before numbers | *"Sequencing measurement last"* is named in `concept_review.md` as the **primary conceptual failure**. H1 in the refactor plan is measurement honesty. The audit of record documents the isolation leak that made candidate diffs invisible to their own gates | **Decisive.** This is not a preference; it is a post-mortem |
| **F6** — meta-loop authority | `agi_evolution_path.md` states the Conductor holds **zero grants** and every effect goes down one port. The same logic applied to a self-evolution loop is the TCB boundary | **Strong.** Same principle, one layer up |
| **F3** — statistical protocol | H1 (dummy pass rates, bogus noise floors) is exactly what an unestablished floor produces | **Strong** |
| **F5** — port count / entry rule | *"Ports without active adapters must be demoted"* — and the prototype shipped five adapterless ports anyway | **Strong.** The rule existed and was not enforced; that is an argument for mechanism, not for the rule |
| **F7** — Architect/Editor | `next_gen_architecture_specs.md` binds model roles to tiers and requires the scoring role to differ from the execution role. It does **not** endorse splitting the editor | **Weak** — relevant but not dispositive |
| **F10** — static repo context | The layered prefix is specified; its *value* was never measured | **None.** Open on both sides |
| **F1** — Rust core | The archive is silent. Nothing in the prototype's history bears on it | **None** |
| **F4** — targets | Superseded. The archive's figures predate the current leaderboard | **None** |

**Reading for the meeting:** the archive settles F2 and materially supports F3, F5 and F6. It has
nothing to say about F1, which is why that fork needs a measurement rather than a debate.

---

## 4. Ten lessons, and where each is enforced

A lesson without an enforcement point is a wish. The right-hand column is what makes it real.

| # | Lesson | Enforced by |
| :--- | :--- | :--- |
| 1 | Build evaluation instruments before the capability they measure | The A/A floor is a named phase gate; every gate ships with a test proving it can fail |
| 2 | Generator ≠ Evaluator; the TCB is immutable by agent and meta-loop | import-linter `tcb-isolation` + a CI check on the agent identity |
| 3 | One dispatch choke point; grants verified **at the point of effect** | Architecture test asserting no bypass path |
| 4 | A port arrives with its first adapter and conformance test | Conformance meta-test |
| 5 | Prompt caching is architecture — fixed prefix layers, explicit breakpoints | CI floor on cache hit rate over a fixed replay |
| 6 | No plausible fallback lies — stubs raise, gates return `None`, never a silent pass | Loud-stub checker |
| 7 | Tree-sitter validates syntax before disk write | Verification tier T1, pre-write |
| 8 | Durable hibernation: serialize and **exit**; grants re-minted, never restored | Reflection contract asserting no grant in frozen state |
| 9 | Sub-agents at depth 1, scoped registry, context never inherited | Enforced at the registry — a sub-agent's tool set excludes delegation |
| 10 | **Code wins.** Contracts live in `src/aether/ports/`; documents navigate | When a doc and the code disagree, the doc is the bug |

---

## 5. What carries forward — the backlog seed

**This is the section for sprint planning.** Most of the archive audits code that is being retired.
A finding is only actionable if it survives the move to greenfield.

| Finding | Verdict | Sprint-1 candidate |
| :--- | :--- | :--- |
| Benchmark runner resolves task commits against the wrong repository | **Carries forward — the runner is being reused** | **Yes.** Standalone utility, no AETHER dependency, unblocks every number. *Start here* |
| Editable install leaks live source into isolated worktrees | **Carries forward — same packaging pattern** | Yes, but only once an evaluation container exists |
| Command-not-found counted as a test failure | **Carries forward** | Yes, with the gate |
| Dummy pass rates / unestablished noise floor (H1) | **Carries forward as a rule**, not as a bug | Ships as the A/A floor protocol |
| Budget recorded after the fact rather than reserved (H2) | **Carries forward** — and worsens under Best-of-N fan-out | Yes — a reserve/commit/release triple |
| Replay determinism (H3) | **Carries forward** | Yes — cassettes are the cheapest CI signal we have |
| Five adapterless ports | **Moot** — greenfield starts from zero ports | No. Becomes the entry rule instead |
| Exceptions swallowed into empty lists (C-1) | **Moot as a bug, carries as a doctrine** | No. Becomes the loud-stub rule |
| `run_loop.py` monolith (725 lines) | **Moot** — not being ported | No |
| `.sagiha/repo-cache/` not gitignored (`N-C1`) | **Moot** — path does not exist in greenfield | No, but the *class* (tool output written into the tree) is worth a lint |
| Structural debt in `src/sagiha/` (H4) | **Moot** | No |

**The pattern worth noticing:** almost everything that carries forward is an **instrument or a
doctrine**, and almost everything that is moot is **prototype code**. That is the strongest available
argument that the greenfield decision was right — and that the measurement layer is the part we
cannot start clean on, because we are reusing it.

---

## 6. Known limits of this guide

- **It summarizes; it does not replace.** Where a decision turns on a finding, read the source.
- **Fork mappings in §3 are Track A's reading** and have not been reviewed by Track B.
- The archive predates the competitor teardowns in `docs/_archive/competitors_research/`. Where the
  two disagree on a mechanism, the teardowns are newer and read actual competing implementations.
