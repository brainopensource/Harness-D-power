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

> **Caveat on #5.** Track A specifies it; **Track B's proposal does not define a TCB boundary**. It is
> listed here as agreed because both leads have stated it verbally — if that is not so, it collapses
> into fork **F6** below and is the single most important item on this page.

---

## Block 2 — Contested forks (the agenda)

Full both-sides write-ups: [ADR set, Part IIc](../_archive/rationale/rewrite/rewrite_v300_decisoes_adr.md).

**Decide today — expensive or impossible to reverse:**

| # | Fork | Track A | Track B |
| :--- | :--- | :--- | :--- |
| **F1** | **Rust core** | Python monoglot; PyO3 sidecar per component on a measured trigger | `core_rs/`, 8 modules, **at Sprint 0** |
| **F2** | **Instruments before *numbers*** | Code starts M0; skeleton ships M1a reporting an honest zero; **no capability number trusted until the A/A floor is published** | Sprint 0 builds **and measures** |
| **F6** | **Meta-loop authority** | RHI never touches the TCB; every mutation lands as a **PR** | GEPA **auto-commits to production** on `p < 0.05`, no TCB boundary |

**Decide today if time allows — otherwise assign an owner and a date:**

| # | Fork | Track A | Track B |
| :--- | :--- | :--- | :--- |
| **F3** | Statistical protocol | A/A floor · exact McNemar · Holm–Bonferroni | `p<0.05`, N≥50, Student's t |
| **F4** | Benchmark targets | Pro ≥80%, Verified ≥96%, lift alongside | Verified ≥90%, Pro ≥60%, Terminal-Bench ≥75% |
| **F5** | Port count | 8, each arriving **with its first adapter** | 12 declared up front |
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
- [ ] **F6** — define the immutable set (evaluator? gates? benchmark definitions? CI?) and the commit policy → unblocks all autonomy work
- [ ] **F4** — committed target vs stretch target → unblocks the definition of "done"
- [ ] **F5** — port count and whether the adapter-first entry rule binds → unblocks `ports/`
- [ ] **F7** — does Architect/Editor ship enabled or behind a flag? → unblocks `agency/`
- [ ] **DAG** — keep, drop, or defer → unblocks `workflow/`
- [ ] **Owner + date** assigned for F3, F8, F9, F10, F11, F12
- [ ] **Confirm invariant #5** is genuinely shared, or move it to F6
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
retroactive. Track B's own cited inspiration — Hermes Self-Evolution — lists among its five hard
guardrails: *"All changes go through pull request review, never direct commit."*

**Likely resolution:** settle the *boundary* first. If the TCB is defined and mechanically enforced,
auto-commit *within* it is far less dangerous — the loop can rewrite a prompt automatically because
it structurally cannot rewrite the gate. Commit policy is downstream of the boundary.

## B. Reading list, by role

| Read this | Who | Why |
| :--- | :--- | :--- |
| [`rewrite_ab_comparison.md`](../_archive/rationale/rewrite_ab_comparison.md) | Both leads | Full side-by-side, including where Track A is weaker. Written by Track A's author — bias declared |
| [ADR Part IIc](../_archive/rationale/rewrite/rewrite_v300_decisoes_adr.md) | Both leads | The fork register, both sides at full strength |
| [`rewrite_v300_measurement_strategy.md`](../_archive/rationale/rewrite/rewrite_v300_measurement_strategy.md) §1c, §2, §3 | Whoever owns F2/F3/F4 | The blockers, the literature, the floor protocol |
| [`rewrite_v300_blueprint_arquitetura_B.md`](../_archive/rationale/rewrite_b/rewrite_v300_blueprint_arquitetura_B.md) §2 | Prototyping dev | The file-level tree — the most immediately useful artifact either track produced |
| [`rewrite_v300_synthesis_amendments.md`](../_archive/competitors_research/tech_lead_A/rewrite_v300_synthesis_amendments.md) | Whoever writes Tier 2 | P1–P78 mapped onto the plan: 19 covered, 17 to sharpen, 34 gaps, 8 declines |

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

- **Framing is Track A's.** Fork descriptions may misstate Track B's position; correct them in the room.
- **The leaderboard re-baselining** behind F4 (Pro leader ~80.3%, Verified ~96%) is Track A's own web
  research from a single session and has not been independently verified. F4 rests on it.
- **The archive move broke both CI gates** — 19 dead relative links, and the normative word count is
  now 19,720 against a 15,000 ceiling. Unrelated to the architecture decisions, but it needs an owner
  before the next PR.
