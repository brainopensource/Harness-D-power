---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Tech Lead Alignment: Decision Brief

**For:** Tech Lead A · Tech Lead B · Prototyping Developer
**Purpose:** lock the contested architecture so the Tier 2 spec and Sprint 1 backlog can be written.
**Prepared by:** Track A. **Track B has not reviewed this framing** — treat the fork descriptions as
contestable and correct them in the room.

> ### Revision 2026-08-05 — three fork rows corrected against Track B's text
>
> Appendix F of revision 1 declared that the fork descriptions were written from Track A and
> unreviewed by Track B. An audit of Track B's on-disk documents found that **three rows
> misstated Track B's position**, two of them among the three flagged as must-decide:
>
> | Row | Revision 1 said | Correction |
> | :--- | :--- | :--- |
> | **F6** | Track B has no TCB boundary and auto-commits to production | Track B defines `kernel/` as the TCB and states I7/I8/I9 verbatim. The auto-commit quote is **not in Track B's current text** |
> | **F5** | Track B declares 12 ports up front | Track B **adopts Track A's A-010** — 8 ports, adapter-first — in three places. Moved to Block 1 as agreed |
> | **F2** | Track B has no A/A noise floor | Track B commits to measuring the A/A floor in Sprints 0–1. The fork narrows to *sequencing* |
>
> **Cause:** [`rewrite_ab_comparison.md`](../_archive/rationale/rewrite_ab_comparison.md)
> reviewed a superseded Track B revision — its snapshot note reads 15:04; the files on disk
> are 15:22–15:24, squashed into `2a8c417` with no history to diff. Track A's verification
> discipline was applied honestly to text that has since changed.
>
> Full evidence, with citations:
> [`rewrite_v300_phase0_audit_register.md`](./rewrite_v300_phase0_audit_register.md).
> **Track B has not reviewed the corrections either** — if Tech Lead B corrects a row in the
> room, that still outranks this document.

---

## Block 1 — Agreed baseline (5 invariants, no decision needed)

Both tracks arrived at these independently. Confirm and move on.

| # | Invariant | Enforcement |
| :--- | :--- | :--- |
| **1** | **Hexagonal ports.** All I/O crosses a typed `Protocol`; `domain/` has zero I/O dependencies | import-linter `domain-is-pure`; pyright strict |
| **2** | **Single execution choke-point.** Every effect passes `kernel/dispatch.py`, gated by the CAR policy engine | Architecture test: no bypass path to a tool handler |
| **3** | **Wire-serializable ports.** Every port method `async`; Pydantic payloads only — no file handles, callables, generators or live objects | Reflection contract over *all* ports |
| **4** | **Prompt cache is architecture, not optimization.** Fixed prefix layers, explicit `cache_control`, hit rate is a gated metric | CI floor on hit rate over a fixed replay |
| **5** | **Trusted Computing Base.** Evaluator, gates, policy and benchmark definitions are isolated from the agent. *Generator ≠ Evaluator* | import-linter `tcb-isolation` + CI `tcb-check` |
| **6** | **Eight ports, adapter-first.** A port enters `ports/` in the same change as its first adapter and conformance test (A-010) | Conformance meta-test |

> **#5 is confirmed in writing, not just verbally.** Track B's blueprint labels `kernel/` *"Trusted
> Computing Base (TCB)"* and states the invariants verbatim — *"**I8 (Immutable TCB):** A camada
> Kernel e o Evaluator são imutáveis e isolados (`import-linter: tcb-isolation`)"*
> (`blueprint_arquitetura_B.md:163-165`, ADR-12). What Track B does **not** do is bind the
> self-improvement loop to that boundary: `evolution/` appears in no import-linter contract, and no
> commit policy is stated. That residue is fork **F6**, and it is narrower than revision 1 claimed.
>
> **#6 was fork F5 in revision 1.** Both tracks wrote the same rule — Track B: *"Aceitar a **Regra
> A-010 da Track A**: iniciar o `src/aether/ports/` com 8 portas essenciais"*
> (`auditoria_sagiha_B.md:70`, `decisoes_adr_B.md:172`, `roadmap_sprints_B.md:70`). Confirm and move
> on. **Two caveats worth 60 seconds:** Track B's own preference was 9 ports (`Memory` and
> `CodeGraph` from the foundation) before it capitulated, so check the capitulation is real and not
> an artifact of document ordering; and A-010's existing reversal condition still stands — a port
> with two adapters planned in the same phase may be introduced ahead of the first, second named.

---

## Block 2 — Contested forks (the agenda)

Full both-sides write-ups: [ADR set, Part IIc](../_archive/rationale/rewrite/rewrite_v300_decisoes_adr.md).

**Decide today — expensive or impossible to reverse:**

| # | Fork | Track A | Track B (corrected) |
| :--- | :--- | :--- | :--- |
| **F1** | **Rust core** | Python monoglot; PyO3 sidecar per component on a measured trigger | `core_rs/`, 8 modules, **at Sprint 0** |
| **F2** | **Instruments before *numbers*** | Code starts M0; skeleton ships M1a reporting an honest zero; **no capability number trusted until the A/A floor is published** | Sprint 0 builds **and measures**. B does commit to the A/A floor in Sprints 0–1 — the fork is **sequencing**, not whether the floor exists |
| **F6** | **Meta-loop authority** | RHI never touches the TCB; every mutation lands as a **PR** | TCB **is** defined (I7/I8/I9, `tcb-isolation`), but `evolution/` is bound by **no contract** and **no commit policy is stated** |

**Decide today if time allows — otherwise assign an owner and a date:**

| # | Fork | Track A | Track B |
| :--- | :--- | :--- | :--- |
| **F3** | Statistical protocol | A/A floor · exact McNemar · Holm–Bonferroni | `p<0.05`, N≥50, Student's t / two-tailed permutation |
| **F4** | Benchmark targets | Pro ≥80%, Verified ≥96%, lift alongside | Verified ≥90%, Pro ≥60%, Terminal-Bench ≥75% |
| ~~F5~~ | ~~Port count~~ | **Resolved — not contested.** Both tracks wrote A-010. Moved to Block 1, invariant #6 | |
| **F7** | Architect/Editor split | Seam built, **shipped off** behind an ablation | Built and enabled, Sprint 1 |
| **F8** | Shell AST | Effect **classification** only; sandbox is the perimeter | Presented as eliminating security bypasses |
| **F9** | Schedule form | Exit gates only | 5 sprints × ~14 days |
| **F10** | Static repo context in prefix | 5 layers; generated layer is the **first M2 ablation** | 3 fixed markers incl. AST Skeleton Map |
| **F11** | LSP | `growth` tier, warm pool | Eliminate; replace with tree-sitter |
| **F12** | IP protection | Compilation is a speed bump | Nuitka rated "Excelente" |

**Plus one decision neither track made:** the **workflow DAG** (ADR-0018 / A-024) has disappeared from
three consecutive implementation plans without anyone voting to drop it. Keep, drop, or defer?

---

## Block 3 — Decisions requested

Walk out of the room with these. Each unlocks a specific downstream artifact.

- [ ] **F1** — Rust at Sprint 0, Python-first, or *instrument-then-decide*? → unblocks the `src/aether/` tree and the toolchain requirement
- [ ] **F2** — is a capability number publishable before the A/A floor exists? → unblocks the sprint sequence
- [ ] **F6** — define the immutable set (evaluator? gates? benchmark definitions? CI?) and bind `evolution/` to it → unblocks all autonomy work
- [ ] **F4** — committed target vs stretch target → unblocks the definition of "done". **Note the leaderboard research behind it is unverified; ratifying may mean ratifying a re-verification task**
- [ ] **F7** — does Architect/Editor ship enabled or behind a flag? → unblocks `agency/`
- [ ] **DAG** — keep, drop, or defer → unblocks `workflow/`. **See Appendix G: A-024 already decided this**
- [ ] **Owner + date** assigned for F3, F8, F9, F10, F11, F12
- [ ] **Confirm invariants #5 and #6** as corrected above
- [ ] **Owner** for the two non-architectural items in Appendix F that block CI honesty
- [ ] **Approve the Tier 2 spec outline** and name its single owner

---

<div style="page-break-after: always;"></div>

# Appendix — supporting material (not part of the one-page brief)

## A. Why F1, F2 and F6 are the three that matter

**F1** is the only genuine either/or. Both positions are defensible and both tracks are weak on it —
Track A never names a module and defers to triggers nobody has instrumented; Track B sets `<50 ns`,
`<10 ms` and `0 ms` as *sprint acceptance gates* for latencies never measured on this hardware. A
third position: put a timer on worktree creation and AST parse-and-validate in the first working
slice — one afternoon — and let the number pick the side.

Three checks worth doing before voting: `<50 ns` is the FFI crossing cost, not the parse (a real
tree-sitter parse is milliseconds in any language); `<10 ms` is a filesystem property and may already
be free on a reflink-capable host; `0 ms` pool allocation is amortized and **drains under Best-of-N
fan-out**, which is the workload it exists for.

> **Correction to revision 1, and it cuts against Track A.** The criticism above — that Track B's
> figures are unmeasured — is true. Track A's are no better. The runtime §1 latency table (PyO3
> ~100 ns, gRPC ~200 µs, *"four to seven orders of magnitude"*) carries **no benchmark, no hardware
> and no citation**, and it is the entire load-bearing argument for A-002 and for Track A's side of
> this fork. **Neither track may cite a number here.** That is the real case for the third position,
> and it is stronger than the one revision 1 made.
>
> Two supporting facts. Track B contradicts itself on its own headline figure: the parse is `<50 ns`
> in four places and *"em **milissegundos**"* at `decisoes_runtime_B.md:43`. And the only external
> numbers in the corpus that would justify a Sprint 0 Rust core — `<8 ms`, `<5 ms`, `<15 ms`, printed
> under a heading reading *"Performance **Benchmarks**"* — **appear nowhere in `src/grok_build/`**.

**F2** is not symmetric. The three instrument defects are documented and reproduced in this
repository:

| Blocker | Effect | Earliest fixable |
| :--- | :--- | :--- |
| **B1** — runner resolves base commits against the *local* repo; the 12 upstream SWE-bench repos were never cloned | All 30 tasks fail `fatal: invalid reference:` — this is why the 2026-08-01 A/A run produced nothing | **Now.** Standalone utility, no AETHER dependency |
| **B3** — editable install's `.pth` leaks live `src/` into every isolated worktree | **Candidate diffs invisible to the gates scoring them.** This one produced numbers | After the evaluation container exists |
| **B4** — exit-127 scored as test failure, not instrument error | Instrument failures enter the denominator | After the gate exists |

A number taken over B3 is not a faster route to the same place — it is work that gets discarded
retroactively, along with every decision made on it. `noise-floor.md` still reads *"still not
populated"*; `s1_honest_baseline.md` records the correction that took the measured pass rate to 0.0%,
*and the drop was the fix*.

**Do not read F2 as "fix everything before writing code."** Two independent reviewers have already
made that error. B1 starts now; B3/B4 arrive with the components they isolate.

**F6** is asymmetric for a different reason. An optimizer whose mutable surface includes the
evaluator has one strictly dominant strategy: **weaken the judge.** No downstream statistical rigour
detects it, because the statistics are computed by the thing being weakened, and the failure is
retroactive. That argument stands on its own and nothing below weakens it.

> **Correction to revision 1 — the fork is much narrower than stated, and the evidence for the
> strong version does not hold.**
>
> **Track B does define the TCB.** `blueprint_arquitetura_B.md:163-165` states I7/I8/I9 verbatim,
> the tree labels `kernel/` *"Trusted Computing Base (TCB)"*, and ADR-12 adopts `tcb-isolation`.
> The `p<0.05 → Commit Git Automático em Produção` quote attributed to Track B **is not in Track B's
> current text** — grep for `CommitProd`, `AblationGate` or `Commit Git` across all five documents
> returns zero hits, and ADR-05 carries no diagram at all.
>
> **The Hermes guardrail is real, and it points the other way from how it was used.** The primary
> source in this repository says *"**PR review** — All changes go through human review, never direct
> commit"* (`src/hermes_self_evolution/README.md:76`) and ships `create_pr: bool = True`
> (`evolution/core/config.py:47`). The competitor study that attributed auto-commit to Hermes
> (`competitors_research/tech_lead_B/hermes_self_evolution_B_gemini.md:52`) **inverted its source**,
> and the same document asserts a *"Statistical Significance Gate: p < 0.05 across at least 50 test
> instances"* that **does not exist in Hermes' code** — actual `eval_dataset_size: int = 20` with a
> 0.25 holdout, roughly five examples. Worth stating plainly in the room: a fabricated significance
> gate, inside the research meant to inform the fork about trusting numbers.
>
> **What actually remains of F6**, and it is worth deciding: Track B has the TCB invariants but never
> binds the self-improvement loop to them. `evolution/` appears in no import-linter contract, and no
> commit policy is stated anywhere in the five documents. That is a gap of omission, roughly half the
> severity of the row as written — and both tracks are closer to agreement than revision 1 implied.

**Likely resolution:** settle the *boundary* first. If the TCB is defined and mechanically enforced,
auto-commit *within* it is far less dangerous — the loop can rewrite a prompt automatically because
it structurally cannot rewrite the gate. Commit policy is downstream of the boundary.

**One mechanical prerequisite the meeting should not skip.** Whatever F6 decides, its enforcement is
`tcb-isolation` in `.importlinter` and `TCB_PATHS` in `ci.yml` — and both currently name
`src/sagiha/kernel/policy` and `src/sagiha/outer_loop/evaluator`. At the `src/sagiha/` → `src/aether/`
migration neither fails; **both pass vacuously**. An F6 decision enforced by a contract that selects
no files is not enforced. This is now covered by `tests/unit/test_path_constant_drift.py`, but the
migration itself needs an owner.

## B. Reading list, by role

| Read this | Who | Why |
| :--- | :--- | :--- |
| [`rewrite_ab_comparison.md`](../_archive/rationale/rewrite_ab_comparison.md) | Both leads | Full side-by-side, including where Track A is weaker. Written by Track A's author — bias declared |
| [ADR Part IIc](../_archive/rationale/rewrite/rewrite_v300_decisoes_adr.md) | Both leads | The fork register, both sides at full strength |
| [`rewrite_v300_measurement_strategy.md`](../_archive/rationale/rewrite/rewrite_v300_measurement_strategy.md) §1c, §2, §3 | Whoever owns F2/F3/F4 | The blockers, the literature, the floor protocol |
| [`rewrite_v300_blueprint_arquitetura_B.md`](../_archive/rationale/rewrite_b/rewrite_v300_blueprint_arquitetura_B.md) §2 | Prototyping dev | The file-level tree — the most immediately useful artifact either track produced |
| [`rewrite_v300_synthesis_amendments.md`](../_archive/competitors_research/tech_lead_A/rewrite_v300_synthesis_amendments.md) | Whoever writes Tier 2 | P1–P78 mapped onto the plan: 19 covered, 17 to sharpen, 34 gaps, 8 declines. **The arithmetic is presentational** — eight proposals (P7, P8, P15, P32, P38, P42, P43, P44) get no verdict at all, and P65/P74 are double-counted |
| [`rewrite_v300_phase0_audit_register.md`](./rewrite_v300_phase0_audit_register.md) | **Everyone, before forming a position** | Every contradiction between the tracks and every untraceable number, with citations. It is what produced the corrections in this revision |

## C. The documentation tiers this meeting unblocks

| Tier | Artifact | Owner | Written when |
| :--- | :--- | :--- | :--- |
| **1** | This brief | Track A | Done |
| **2** | **Normative spec** — ~2–3k words, minimal statement of what is *true*. Every contract points at code; the spec navigates, `ports/` defines | One named owner | **After** this meeting — writing it before means writing it twice |
| **3** | Rationale (`docs/_archive/`) — the *why*, ~65k words | Both leads | Exists. Frozen. `retrieval: excluded` |
| **4** | **Executable contracts** — `ports/*.py`, `domain/`, generated event catalog, mock adapter set, conformance suite, cassettes | Prototyping dev | Starts immediately; does not wait on Tier 2 |

**Diagram budget: five.** Layer/dependency graph · run-loop sequence · dispatch choke point ·
context prefix layout · phase dependency graph. Each encodes something a previous attempt got wrong.
Anything beyond five rots faster than it informs.

## D. What the prototyping developer starts on Monday, regardless of the vote

None of this is blocked by any fork:

1. **B1 — the upstream repo cache.** Clone, SHA-pin and reuse the 12 SWE-bench task repositories.
   Standalone, no AETHER dependency, and it is what unblocks every number.
2. **The mock adapter set.** 100 turns in 50 ms, no API calls, no containers. This is what makes
   "iterate and pivot fast" real rather than aspirational.
3. **Two timers** — worktree creation, AST parse-and-validate. One afternoon, and it settles F1 with
   a number instead of a preference.

**Experiment protocol** — needed because no track wrote one and it is the role's actual contract:
experiments live outside `src/aether/`, exempt from the invariants, and are deletable. An experiment
produces a **number and a recommendation**; it becomes a decision only through an ADR with a reversal
condition. **An experiment that shows nothing is recorded as showing nothing** — that rule is what
would have saved the predecessor.

## E. Standing rules that survive whatever is decided

- Every gate ships with a test proving it **can fail**.
- Stubs raise; they never return a plausible value.
- No mechanism promotes to production without an ablation clearing the noise floor.
- `docs/STATUS.md` makes zero claims unsupported by a line-level code read. On day one it says
  *nothing is implemented*, and that is correct content.
- No external code enters `src/aether/`. Concepts and published theory transfer; implementation does
  not.

## F. Known problems with this brief

- **Framing is Track A's.** Fork descriptions may misstate Track B's position; correct them in the
  room. **Three did** — see the revision block at the top. Corrections came from an audit of Track B's
  text, which Track B has also not reviewed. The same standing applies: Tech Lead B outranks both.
- **The leaderboard re-baselining** behind F4 (Pro leader ~80.3%, Verified ~96%) is Track A's own web
  research from a single session and has not been independently verified. F4 rests on it entirely.
  Ratifying F4 without re-verification means ratifying an unverified premise.
- **Both CI gates are repaired**, and the diagnosis is worth 30 seconds because it recurs below.
  Neither was a content problem. `docs_budget.py` matched ADRs by the prefix `08-decisions/`; the
  archive move put them at `_archive/08-decisions/`, the exemption stopped selecting, and 28 files /
  5,779 words silently re-entered the budget — **19,720 − 5,779 = 13,941**, the pre-move figure. All
  19 dead links were `../../` resolving one directory short. Both fixed;
  `tests/unit/test_path_constant_drift.py` now fails when a path-keyed constant selects nothing.
- **Two items still need an owner, both the same class of defect:**
  - `benchmarks/definitions/s0-core.json` is documented as *"committed and pinned"* and treated as
    TCB, but `benchmarks/` is **empty and untracked**. The `bench-aa` job is guarded on that file, so
    it is a **permanent silent no-op** — a gate that cannot fail, which is exactly what
    `noise-floor.md` exists to warn about. Held open as a strict `xfail`.
  - `TCB_PATHS` and `tcb-isolation` go vacuous at the `src/aether/` migration (Appendix A, F6).
- **`rewrite_v300_project_vision.md` exists.** An earlier note claimed it did not. Nothing to do.

## G. The workflow DAG — the premise is wrong, so check before voting

Block 2 asks whether the DAG *"disappeared from three consecutive implementation plans without anyone
voting to drop it."* It did not disappear. **A-024 re-sequenced it deliberately**, and carries a
reversal condition — which is more than most decisions in this set have.

| Phase | What lands | Cost |
| :--- | :--- | :--- |
| **M0** | `WorkflowStep[In, Out]` — node and socket types only. No executor | Near zero |
| **M1a** | Walking skeleton runs as a **four-node linear graph** (`retrieve → generate → apply → evaluate`) | Small |
| **M2** | **Per-node memoization keyed by input digest**; partial re-execution | Real, and it pays for itself |
| **M3** | Branching, fan-out, conditional paths | Real |

The reasoning is worth keeping because it generalises: *"a linear pipeline **is** a DAG with no
branches"*, and retrofitting a graph onto a pipeline costs far more than starting with a trivial
graph — **the dependency direction is asymmetric**. The M2 memoization is not a performance nicety:
no mechanism promotes without an ablation, an ablation re-runs a pipeline with one node changed, and
memoization turns that from full re-execution into subtree re-execution. **The cost of running
ablations is a first-order design concern**, and this is what pays it down.

**Reversal condition (A-024, verbatim in substance):** if the node abstraction is not carrying weight
at the M2 boundary — no measurable memoization benefit, no branching in sight — collapse it to a plain
sequential pipeline. The hatch stays open until M2 precisely because *"four nodes are cheap to
un-abstract; forty would not be."*

**So the decision requested is not keep/drop/defer.** It is: does anyone want to overturn A-024? If
not, correct the premise and move on — this is a 60-second item, not an agenda slot.
