---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# Track A vs Track B — cross-check of the two rewrite proposals

> [!NOTE]
> **LLM / AI AGENT NOTICE**: Phase-0 rationale. Not binding, defines no contract, decides nothing.

**Declared bias.** This comparison was written by the author of Track A. That is a conflict of
interest and the reader should weight it accordingly. The mitigation applied here is procedural:
every claim about Track B is quoted or verified against the repository, every criticism of Track A is
stated in the same section as the equivalent criticism of Track B, and §6 lists the places where
Track B is simply better and Track A should adopt from it. A second reader who has not written either
proposal would be a better judge of §5.

**Snapshot.** `docs/rationale/rewrite_b/` was last written at 15:04 on 2026-08-05, minutes before this
comparison. Track B is an actively-moving target; anything below may already be stale.

---

## 1. The two proposals at a glance

| | **Track A** (`docs/rationale/rewrite/`) | **Track B** (`docs/rationale/rewrite_b/`) |
| :--- | :--- | :--- |
| Documents | 13 (12 + index) | 5 |
| Words | ~49,500 | ~7,900 |
| RFP deliverables named | 9 + 3 additions | 9 named in the body; **5 in the §5 checklist** |
| Delivered | 12 of 12 | **5 of 9** — complete against the §5 checklist, missing the four §4 mechanism specs |
| Language | English | Portuguese |
| Runtime | Python 3.13 monoglot, sidecar behind a measured trigger | **Python + Rust `core_rs/` via PyO3, from Sprint 0** |
| Ports | 8, each added with its first adapter | 12, declared up front |
| Schedule | No durations — "the exit gates are the schedule" | **5 sprints × ~14 days, with a Gantt** |
| Benchmark targets | Pro ≥80%, Verified ≥96% | Verified ≥90%, Pro ≥60%, Terminal-Bench ≥75% |
| Statistical rule | A/A noise floor, exact McNemar, Holm–Bonferroni, α=0.05 family-wise | **p < 0.05, N ≥ 50, Student's t / permutation** |
| Reversal conditions | On every ADR | None |

The shapes are genuinely different, and the difference is not merely length. **Track B is a
specification.** It names files, modules, latencies and dates, and it decides. **Track A is a
decision record.** It argues, bounds, and defers to measurement. Each shape has a failure mode: a
specification can be confidently wrong; a decision record can fail to produce a system.

---

## 2. Where Track B is better

These are real and Track A should take them.

### 2.1 The file-level tree is directly actionable

Track B's blueprint §2 gives a complete `src/aether/` layout down to individual files with one-line
purposes — `core_rs/seek_sequence.rs`, `agency/context/taint_gate.py`, `evolution/trace_miner.py`.
Track A gives a package layout (§8) and stops at the directory. For a team about to open an editor,
B's tree is the more useful artifact, and it is the single thing Track A should copy outright.

### 2.2 The 15-domain confrontation matrix

Blueprint §1.2 is one table with a row per technical domain and a column per competitor, ending in an
AETHER column. It fits on a screen and it is the artifact a decision meeting actually wants. Track A's
equivalent evidence is spread across four teardowns and a three-way convergence table; B's version is
better packaged.

### 2.3 Compactness

7,900 words against 49,500. A Tech Lead reading both will finish B in twenty minutes and A in three
hours. That is not a small thing, and Track A's volume is a genuine cost — some of it is necessary
(the measurement argument does not compress) and some of it is not.

### 2.4 Decisiveness on the Rust core

Track B commits: `core_rs/` with eight named modules, compiled by Maturin, at Sprint 0. Track A defers
everything behind RT-1/RT-2/RT-3 triggers and never names a module. B's position is falsifiable and
schedulable; A's is safe and, from a builder's perspective, evasive. If the performance claims hold,
B has a stronger story for the "swap components to scale performance" goal.

### 2.5 Per-ADR sequence diagrams

Each of B's nine ADRs carries a mermaid diagram showing the actual flow. A's ADRs are prose. Diagrams
are faster to check for holes, and B's ADR-01 diagram in particular makes the Architect/Editor
hand-off legible in a way three paragraphs do not.

### 2.6 A calendar

B has sprints with dates. A refuses durations on the grounds that exit gates are the schedule — which
is intellectually correct and operationally unhelpful when someone has to plan a quarter. B's Gantt
is wrong in the way all Gantts are wrong, and it is still more useful than no Gantt.

---

## 3. Where Track A is better

### 3.1 The baseline numbers in Track B are contradicted by this repository

This is the most serious finding in the comparison, and it is verifiable rather than a matter of
taste.

Track B's audit §5.1 and roadmap §2 state a "Baseline Prototípico" for `src/sagiha/`:

| B's claimed baseline | Repository record |
| :--- | :--- |
| SWE-bench Verified ~68.0–72.0% | **No valid measurement exists** |
| SWE-bench Pro ~38.0–40.0% | **No valid measurement exists** |
| Terminal-Bench ~45.0% | **No valid measurement exists** |
| Prompt cache hit rate ~50.0% | SAGIHA emits **no `cache_control` at all**; caching is positional and unmeasured |
| Worktree creation ~1.5–4.5 s | Not instrumented |

What the repository actually records, verified while writing this:

- `docs/rationale/benchmarks/noise-floor.md`: **"Status: still not populated. A run was attempted on
  2026-08-01 and produced no usable floor."** And, in the file itself: *"Do not cite a noise floor
  from this file. There is not one yet."*
- The same file records `Benchmark complete! Pass rate: 0.0%` — quoted there **specifically so nobody
  mistakes it for a result**, because the run failed on all 30 tasks with `fatal: invalid reference:`.
- `s1_honest_baseline.md` records the correction that took the measured pass rate to 0.0%, and that
  *the drop was the fix*.

So Track B's sprint table measures every improvement against an origin that does not exist. A plan
that starts from ~68% and targets 90% is claiming +22 points; a plan that starts from *unknown* is
claiming nothing yet. The numbers are not conservative or optimistic — they are unsourced, and they
contradict the four benchmark records in this tree.

**This is not a small correction.** It is the exact failure the predecessor documented at its own
expense, and Track A's entire M1b phase exists to prevent it.

### 3.2 No A/A noise floor, so "p < 0.05" has no denominator

Track B requires statistical significance at p < 0.05 over N ≥ 50 instances, via Student's t or a
permutation test. That is the right instinct and it is better stated than most plans manage.

What is missing is the floor. Two identical configurations run against each other produce a non-zero
difference — LLM sampling, test ordering, flaky tests in the task repositories. Without measuring that
variance first, a significant result on a paired run cannot be distinguished from the harness's own
noise. Track A's protocol (exact McNemar for paired binary outcomes, Holm–Bonferroni across the gate
family, seeded bootstrap CI, floor published *before* any regression rule is enforced) exists because
the predecessor accepted variance as progress.

Two technical notes on B's choice, offered as improvements rather than objections: **Student's t is
the wrong test for paired binary outcomes** — resolve/not-resolve is a McNemar problem, not a t-test
problem — and **α = 0.05 applied per-test across five arms is a ~23% family-wise error rate**, which
is why A applies Holm–Bonferroni across the family.

### 3.3 The instrument blockers are not addressed

Track B's Sprint 0 begins building. Three documented, reproduced instrument defects remain open:

| Blocker | Effect if unfixed |
| :--- | :--- |
| **B1** — the runner runs `git worktree add <base_commit>` against the *local* repo while SWE-bench base commits live in 12 never-cloned upstream repositories | Every task fails with `fatal: invalid reference:`. This is why the A/A run produced nothing |
| **B3** — the editable install's `.pth` leaks the live `src/` into every isolated worktree | **Candidate diffs are invisible to the gates scoring them.** The gate reports on the wrong tree |
| **B4** — exit-127 "command not found" scored as a test failure rather than an instrument error | Instrument failures enter the denominator, widening every interval unpredictably |

B3 is the dangerous one: it is an isolation mechanism that silently did not isolate, and it *produced
numbers*. A plan that starts measuring at Sprint 0 without fixing it produces confident numbers over a
broken instrument — which is worse than producing none.

### 3.4 The targets appear to be below the current state of the art

Track B targets Verified ≥90%, Pro ≥60%, framed as *"liderança SOTA incontestável"*.

Per Track A's re-baselining (August 2026, from web research — so this figure is Track A's own claim
and should be re-verified independently): **SWE-bench Pro's leader is ~80.3%**, with the top cluster
around 79–80%, and **Verified is saturating near 96%** with the top tier within about one point.

If those figures hold, B's targets would land roughly 20 points below the Pro leader and 6 points
below the Verified frontier. B's numbers are consistent with `PLANNING.md`'s stale snapshot (Pro
leader 69.2%) — and even against that snapshot, a 60% Pro target is below the leader.

### 3.5 Two citations are misattributed, and one contradicts B's own design

I made the first of these errors myself and corrected it after verifying against arXiv; Track B has
not.

**arXiv 2605.18747** is *"Code as Agent Harness"* (Ning et al., May 2026), a survey organized as
Harness Interface → Harness Mechanisms → Scaling the Harness. Track B attributes to it the three
properties **Parity / Receptivity / Observability** (blueprint §1.1). Those are not that paper's
framework. They are a good decomposition and worth keeping — but as an AETHER proposal, not as a
citation.

**arXiv 2602.11988** is *"Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding
Agents?"* (Gloaguen, Mündler, Müller, Raychev, Vechev — SRI Lab, ETH Zürich). Track B calls it *"Agent
Context Evaluation"* and attributes to it the **"Dumb Zone" at 40–60% of the window** (ADR-02, audit
§3.2). That paper measures whether context files help; it says nothing about where attention degrades
in a window. The Dumb Zone figure is unverified and should be carried as a hypothesis.

**And the paper cuts against B's design rather than supporting it.** Its finding: repository context
files **do not generally improve task success while increasing inference cost by >20%**, with
LLM-generated files *reducing* success ~3% and human-written ones improving it ~4%. Track B's ADR-02
cites this approvingly and then fixes an **"AST Skeleton Map do Repositório"** as cache marker 3 —
machine-generated, always-on repository context, which is precisely the category the paper measured as
negative-value. Track A has the same exposure (its static repo-context layer is also generated) and
flags it explicitly, making that layer the first ablation of M2. Track B does not notice the tension.

### 3.6 Performance figures are acceptance gates, not measurements

B's roadmap §2 sets these as sprint acceptance criteria: worktree creation **< 10 ms**, container
allocation **0 ms**, FFI latency **< 50 ns**, cache hit rate **> 92%**.

None is measured; all are targets imported from competitor documentation. Three specific problems:

- **"0 ms" is not a physical quantity.** A pre-warmed pool amortizes startup; it does not eliminate it.
  Under Best-of-N fan-out — which is exactly the workload that needs it — the pool drains and the
  Nth subagent waits for a cold container. The honest metric is *p99 allocation latency under fan-out*.
- **`< 10 ms` is filesystem-dependent and may already be free.** Grok Build's own worktree pool is
  macOS-only in production, with the reason in the source: *"Linux has O(1) BTRFS snapshots; the pool
  adds value only on macOS/APFS where worktree creation is O(file_count)."* On a Btrfs or
  XFS-with-reflink host, much of the gain may already exist. We do not know which case we are in
  because nobody has timed it.
- **`< 50 ns` for tree-sitter AST validation conflates two things.** The FFI *call* can be tens of
  nanoseconds; the *parse* cannot. B's own blueprint says *"passa o hunk por Tree-sitter `ast.parse` em
  <50ns"* — that is the crossing cost applied to the work. A parse of a real source file is
  milliseconds regardless of language.

The deeper issue is sequencing: a sprint gate on an unmeasured number either blocks the sprint or gets
waived, and a gate that gets waived is not a gate.

### 3.7 No TCB, and an auto-evolution loop that can commit to production

Track B has no equivalent of Track A's invariants **I7** (generator ≠ evaluator), **I8** (immutable
TCB), or **I9** (hard gates admit, proxies rank). Combined with ADR-05, that is the most
consequential structural gap in the proposal:

> `AblationGate{Ablação Estatística p < 0.05?} -->|Aprovado| CommitProd[Commit Git Automático em Produção]`

An auto-evolution engine that mutates prompts and skills, evaluates itself, and **commits to
production automatically on a p-value** — with no boundary excluding the evaluator, the gates and the
benchmark definitions from its mutable surface — has one very efficient strategy available to it:
weaken the thing that judges it. Nothing in B's design prevents that, and the failure is retroactive
— it invalidates every number the project has produced, not just the current run.

Track A's position: the meta-loop may optimize prompts, routing, skills and tool schemas; it may
never touch policy, evaluator, gates, benchmark definitions or CI, enforced by an import-linter
contract plus a CI check on the agent identity. And every mutation lands as a reviewable PR, never a
direct commit. Hermes' own self-evolution repository — which B cites as the inspiration for GEPA —
requires exactly this: *"All changes deploy via PR, never direct commit."*

### 3.8 Ports declared before adapters — the predecessor's exact failure

B's audit correctly identifies the problem: five of SAGIHA's ports have no adapter, and it invokes the
rule — *"código sem adaptador não paga aluguel"* — to eliminate `advisory.py`.

Then B's blueprint declares twelve ports up front, including `code_graph`, `memory`, `search` and
`indexer`, without an adapter-first rule. Track A's A-010 makes it an entry rule: **a new port is
added in the same change as its first adapter and its conformance test**, starting at eight. That is
the mechanism that prevents the exact defect B's audit diagnoses.

For the user's stated goal — *minimalistic, decoupled, easy to swap later* — the entry rule is the
load-bearing part. A port designed against an imagined adapter is a guess with type annotations.

### 3.9 No reversal conditions

Every Track A ADR carries a **Reversal Conditions** section, on the principle that a decision without
one is a belief. None of B's nine ADRs has one.

This bears directly on the user's requirement that components be *"easily swapped and changed in the
future"*. A reversal condition is precisely the mechanism that keeps a decision cheap to undo: it
records, in advance, the measurement that would flip it. Without one, revisiting a decision requires
re-litigating the original argument, which teams do not do.

### 3.10 Security is a mechanism list, not a perimeter argument

B's ADR-03 specifies TaintGate, CAR and a Shell AST ExecPolicy, and presents the last as eliminating
*"bypasses de segurança baseados em regex"*.

Shell AST analysis is a better parser applied to command analysis. It does not change the argument
that command analysis is unwinnable as *containment*: there are unboundedly many spellings of any
command (expansion, base64, an interpreter, a fetched script). Track A's ADR-0006 states the perimeter
position explicitly — the sandbox is the perimeter, blocklists are UX — and Track A's recent amendment
takes the same shell-AST idea but scopes it to **effect classification only, never containment**.

Track B also has no equivalent of Track A's three documented escape vectors (domain fronting via a
CDN apex, Unix-socket privilege escalation, filesystem escalation via `$PATH` write paths), and no
treatment of the self-DoS composition failure — an agent scheduling a job that restarts the harness,
which the supervisor revives, which resumes the session that scheduled it. B has all three ingredients
on its roadmap (Conductor scheduling, durable resume, container supervision) and no guard.

### 3.11 IP protection is overstated

B's runtime matrix rates Nuitka-compiled Python as **"Excelente"** IP protection. Track A's position,
corroborated by the competitor study: compilation is a speed bump, not protection. The corroboration
is unusually direct — Grok Build ships a *native Rust binary* and still obfuscates only the prompt
text, with a trivially reversible XOR. A well-funded competitor shipping compiled code concluded that
prompts were the only asset worth protecting and that a speed bump sufficed.

### 3.12 Four of nine RFP deliverables are missing

RFP B's body names nine expected deliverables; its §5 checklist names five. Track B delivered the five
in the checklist. Missing, against the body: `mecanismo_edicao_B`, `contexto_memoria_B`,
`seguranca_sandbox_B`, `autonomia_agi_B`.

This is partly an ambiguity in RFP B rather than an omission by Track B, and it should be read that
way. The practical consequence stands: the four §4 mechanism areas exist only as ADR fragments, so
there is no equivalent of Track A's repair-loop analysis, cache-mechanics treatment, perimeter design
or autonomy ladder.

---

## 4. Head-to-head on the user's five stated criteria

| Criterion | Track A | Track B | Reading |
| :--- | :--- | :--- | :--- |
| **Clean codebase** | 8 ports, adapter-first, import-linter layer contracts, loud-stub doctrine, TCB isolation | 12 ports, `core_rs/` with 8 Rust modules, strict typing, "zero legacy bloat" | **A**, narrowly — B's typing and no-bloat rules are equivalent, but A's entry rule and layer contracts are mechanically enforced |
| **Minimalistic** | Deliberately absent list with a trigger per row; nothing ships without an ablation | 15 domains all built across 5 sprints; Rust core, PTY, GEPA, Conductor all in scope | **A** clearly. B builds fifteen subsystems before any of them is measured |
| **Decoupled** | I3 wire-serializable ports enforced by a reflection contract over *all* ports in CI | Ports "100% remotáveis", Pydantic-only payloads — same idea, **no enforcement mechanism named** | **A**, on enforcement. The design intent is identical |
| **Grows on a solid foundation** | Walking skeleton → instruments → capability, with a hard serialization point at M1b | Sprint 0 foundation → four capability sprints, no instrument phase | **A**. B's foundation is broader but rests on unverified instruments |
| **Easy to swap components later** | Reversal conditions on every ADR; adapter substitutability (I4) with one conformance suite across N adapters; sidecar stays free via I3 | Hexagonal ports; Rust core is a swap *target*, not a swap *seam* | **A**, and this is the widest gap. B's `core_rs/` couples eight subsystems to one language and a build step at Sprint 0 — that is harder to swap, not easier |

The last row deserves expanding, because it inverts the intuition. B's Rust core looks like it serves
"scale performance later" — but committing eight subsystems to a compiled module in the first sprint
makes each of them *more* expensive to replace, adds a toolchain to every developer's loop, and puts a
compile step inside the self-improvement loop. Track A's position is that I3 keeps the sidecar option
free per component, so the swap happens where a measurement says it should. That is the design that
matches the stated goal; B's is the design that matches the stated *technology*.

---

## 5. What each proposal should take from the other

**Track A should take from Track B:**

1. The file-level `src/aether/` tree (§2.1). Directly.
2. The 15-domain confrontation matrix as a one-page decision artifact (§2.2).
3. Per-ADR sequence diagrams for the mechanisms that have a non-obvious flow.
4. A calendar — even a wrong one — alongside the exit gates.
5. Ruthless compression. 49,500 words is a barrier to the decision it exists to inform.

**Track B should take from Track A:**

1. **Delete the baseline table** until a number exists, and read `noise-floor.md` before writing
   another. This is the highest-priority item in this document.
2. An A/A noise floor before any p-value; McNemar rather than a t-test for paired binary outcomes;
   family-wise correction.
3. Fix B1/B3/B4 before Sprint 0 measures anything.
4. A TCB boundary, and PR-not-commit for the GEPA loop.
5. The port entry rule — a port arrives with its adapter.
6. Reversal conditions on every ADR.
7. Correct the two citations, and notice that the ETH paper argues against the AST-skeleton cache
   marker rather than for it.
8. Re-baseline the targets against the current leaderboard.

---

## 6. Summary judgement

**Track B is the better specification. Track A is the better plan.**

B is what you hand to an engineer who is ready to build and needs to know what to build. It names the
files, draws the flows, and commits to a stack. If the numbers in it were sound, it would be the
stronger document, and it would be close.

The numbers are not sound, and the failure is structural rather than clerical. B measures against a
baseline this repository's own records say does not exist, sets sprint gates on latencies nobody has
timed, requires significance without establishing variance, and begins measuring on instruments that
are documented as broken. That is the predecessor's exact failure mode, restated with better diagrams
— and it is retroactive, because every number taken over a broken instrument has to be discarded, as
this project has already discovered once at its own expense.

A's weaknesses are real but recoverable: it is too long, it under-specifies the physical layout, and
its refusal to commit to a schedule or a stack will frustrate anyone trying to start. Those are
editing problems. B's are measurement problems, and measurement problems are the ones that invalidate
work already done.

**The recommendation this comparison supports** — offered for the Tech Lead to accept or reject — is
neither track wholesale: take **Track A's measurement discipline, TCB boundary, port entry rule and
reversal conditions** as the spine, and **Track B's file-level structure, domain matrix and sprint
calendar** as the skin. The two are compatible; nothing in B's layout conflicts with A's invariants,
and nothing in A's discipline prevents B's tree from being built.

The one genuine either/or is the **Rust core at Sprint 0**. That is a real fork, both positions are
defensible, and it is the decision most worth spending meeting time on. Track A would resolve it the
same way it resolves everything else: put a timer on worktree creation and AST parsing in the first
working slice, and let the number decide before committing a toolchain.

---

**Sources verified while writing this:** `docs/rationale/benchmarks/noise-floor.md` ·
`s1_honest_baseline.md` · `s4-harvest-findings.md` · `src/sagiha/agency/run_loop.py` (725 lines,
31 KB — B's "~850 linhas" is close) · `src/sagiha/ports/` (17 files) · `src/sagiha/adapters/`
(12 directories — B says 11) · `docs/rationale/reviews/review_project_rewrite_v300B.md` §4–§5 ·
[arXiv 2605.18747](https://arxiv.org/abs/2605.18747) · [arXiv 2602.11988](https://arxiv.org/abs/2602.11988)
