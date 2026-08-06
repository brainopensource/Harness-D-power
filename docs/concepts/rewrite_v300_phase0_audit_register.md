---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Phase 0 Audit Register

**The pre-meeting deliverable specified in [`rewrite_v300_context.md`](./rewrite_v300_context.md):**
every factual contradiction between the two tracks, and every numeric claim that cannot be
traced to a measurement in this repository.

**Method.** Both proposal sets, the head-to-head, and all eight competitor teardowns were
read against the code and files they cite. Where a document makes a claim about a
competitor, the claim was checked against that competitor's source, which is on disk under
`src/`. Every row below carries a citation a reader can re-derive without trusting this
document.

**Headline.** Three of the twelve fork rows in
[`rewrite_v300_decision_brief.md`](./rewrite_v300_decision_brief.md) misstate Track B,
including two of the three flagged as must-decide. The brief declares this exposure in its
own Appendix F — *"Framing is Track A's… correct them in the room."* This register is that
correction, delivered on paper so Track B can contest it rather than having to reconstruct
it live.

---

## Part 1 — Contradictions

### 1.1 Fork rows unsupported by Track B's text

| # | Claim in the brief | What Track B's text says | Citation | Effect |
| :--- | :--- | :--- | :--- | :--- |
| **C1** | **F6:** Track B has *"no TCB boundary"* | Track B defines `kernel/` as **"Trusted Computing Base (TCB)"** and states **I7/I8/I9 verbatim**: *"I7 (Generator ≠ Evaluator)… I8 (Immutable TCB): A camada Kernel e o Evaluator são imutáveis e isolados (`import-linter: tcb-isolation`)"*. ADR-12 adopts `domain-is-pure`, `ports-are-pure`, `tcb-isolation` | `blueprint_arquitetura_B.md:163-165`; ADR-12 at `decisoes_adr_B.md:147-149`; tree at `blueprint_arquitetura_B.md:30-65` | **F6 narrows sharply.** See C2 for what survives |
| **C2** | **F6:** *"GEPA auto-commits to production on `p<0.05`"*, quoted as `AblationGate → CommitProd[Commit Git Automático em Produção]` | The string does not exist. `grep -rn "CommitProd\|AblationGate\|Commit Git\|Automático em Produção"` over all five Track B documents returns **zero hits**. ADR-05 contains no diagram at all | `rationale/rewrite_b/` — grep verifiable | The auto-commit charge is **unsupported by Track B's current text**. It presumably described an earlier revision (see C4) |
| **C3** | **F5:** Track B declares *"12 ports up front"*, without an adapter-first rule | Track B **adopts Track A's A-010 in three separate places**: *"Aceitar a **Regra A-010 da Track A**: iniciar o `src/aether/ports/` com 8 portas essenciais"*; the ADR debate table resolves *"**Adotar a Regra A-010**"*; and Sprint 0's second deliverable is *"Consolidação em 8 portas base essenciais (Regra A-010 da Track A)"* | `auditoria_sagiha_B.md:70`; `decisoes_adr_B.md:172`; `roadmap_sprints_B.md:70` | **F5 is not contested.** The brief states Track B's position as the reverse of what Track B wrote |
| **C4** | **F2:** Track B has *"no A/A noise floor"* | Track B commits to measuring it in Sprints 0–1: *"medir o ruído A/A baseline e o scaffold-attributable lift"*, and its audit lists *"Ausência de Rastreamento de Ruído A/A"* as a defect to fix | `roadmap_sprints_B.md:22`; `auditoria_sagiha_B.md:31,36` | **F2 narrows to sequencing**, not concept. Both tracks want the floor; they disagree on whether it precedes the first published number |

**Root cause of C1–C4.** `rewrite_ab_comparison.md` reviewed a **superseded revision of Track
B**. Its own snapshot note dates Track B to 15:04; the files on disk carry mtimes of
15:22–15:24, and the whole tree was squashed into `2a8c417 docs: clean repo`, so no history
survives to diff. Track A's stated mitigation — that every claim about Track B is quoted or
verified — was applied honestly to text that has since changed. This is a process defect,
not a bad-faith one, and the fix is a re-read rather than a retraction.

**What survives of F6.** Track B has the TCB invariants but never connects them to the
self-improvement loop: `evolution/` appears in no import-linter contract, and no commit
policy is stated anywhere in the five documents. That is a real gap and it is worth the
meeting's time — it is simply about half as severe as the row as written, and it is a gap
of omission rather than of position.

### 1.2 Competitor evidence that inverts or fabricates its source

`competitors_research/tech_lead_B/hermes_self_evolution_B_gemini.md` is the **sole source**
for F6's right-hand column. Both of its load-bearing claims contradict the primary source,
which is in this repository.

| # | Claim | Primary source | Citation |
| :--- | :--- | :--- | :--- |
| **C5** | *"`Fitness -->\|Pass Rate Lift p < 0.05\| ProductionDeploy[Git Commit & Deploy to Production]`"* — no PR step anywhere in the document | *"**PR review** — All changes go through human review, **never direct commit**"*, and the default config ships `create_pr: bool = True` | Claim: `hermes_self_evolution_B_gemini.md:52,99`. Source: `src/hermes_self_evolution/README.md:76`; `evolution/core/config.py:47`; `PLAN.md:705-741` |
| **C6** | *"**Statistical Significance Gate:** Demands $p < 0.05$ across at least 50 test instances before promoting a mutated skill or prompt to production."* Mapped into `src/aether/ports/evaluator.py` as a requirement | **No such gate exists.** `grep -rn "0\.05\|p_value\|ttest\|mcnemar"` over `src/hermes_self_evolution/` returns nothing in any evaluation path. Actual `eval_dataset_size: int = 20`, `holdout_ratio: 0.25` → roughly **five** holdout examples | Claim: `hermes_self_evolution_B_gemini.md:107,124`. Source: `src/hermes_self_evolution/evolution/core/config.py:35,38` |
| **C7** | Grok Build worktree performance under a heading reading *"Workspace Isolation Performance **Benchmarks**"*: `<50ns C-ABI`, `Btrfs CoW / Reflinks Creation <5ms`, `Git Worktree Add <15ms`, section title *"SUB-10MS COPY-ON-WRITE WORKTREE ENGINE"* | **None of these figures appears in `src/grok_build/`.** The crates are real; the timings are not in them | Claim: `grok_build_B_gemini.md:33,107,109`. Source: grep over `src/grok_build/**/*.{rs,md}` |
| **C8** | *">92% Prompt Cache Hit Rate Target"*, stated three times | The 92% in the corpus is an **effective context window** figure — *"approximately 92% of the advertised limit"* — not a cache metric | Claim: `claude_refs_B_gemini.md` §3.2. Source: `src/claude_refs/claude-code-ultimate-guide/guide/core/context-engineering.md:235` |
| **C9** | Nine core harness modules attributed to arXiv 2605.18747: `RunLoop, ContextAssembler, Compactor, Dispatcher, Sandbox, EventBus, Governor, MemoryStorage, Evaluator` | These are **AETHER's own port names**. The corpus's nine are While-Loop Engine, Context Management, Tool Registry, Sub-Agent Management, Built-in Skills, Session Persistence, Dynamic Prompt Assembly, Lifecycle Hooks, Permission Enforcement | Source: `src/claude_refs/…/guide/core/agent-harness.md` §2 |
| **C10** | arXiv 2602.11988 cited for both *"Context Engineering / Cache Alignment / Attention Diffusion"* and *"ETH Zürich Config Inflation"*; cost inflation given as **+23%** | 2602.11988 is the AGENTS.md study only. The paper reports **>20%**, not 23% | `claude_refs_B_gemini.md`; cross-check `measurement_strategy.md` §1c |
| **C11** | The *"Dumb Zone"* (attention diffusion at 40–60% of window) rendered as settled fact with an ASCII chart | The corpus explicitly hedges it: *"Treat this as a genuinely open question rather than a settled fact."* Track A independently flags it as unverified | Source: `src/claude_refs/…/context-engineering.md:51`; Track A at `measurement_strategy.md` §1c.2 |

> **C6 is the finding to read twice.** A fabricated significance gate, asserted inside the
> research corpus that informs the fork about whether numbers may be trusted before the
> instrument is verified. F2 is not an abstract concern about discipline; the failure mode
> it exists to prevent occurred during Phase 0, in a document written to support the
> opposite position.

### 1.3 Contradictions inside a single track

| # | Contradiction | Citation |
| :--- | :--- | :--- |
| **C12** | **Track B, on its own headline F1 number.** The tree, ADR-01 and the roadmap put the tree-sitter parse at **`<50ns`**; the runtime document says the same parse runs *"em **milissegundos**"* | `decisoes_runtime_B.md:43` vs. `:51`, `blueprint_arquitetura_B.md:33`, ADR-01 |
| **C13** | **Track A, on port counts.** Claims *"seventeen ports, five with no adapter"*; `src/sagiha/ports/` holds **16 files** plus `__init__.py`. Reaching 17 requires counting `Workspace` and `WorktreeManager` as two protocols in one file — which Track A does elsewhere, but not here | `auditoria_sagiha.md` §0/§3.1 vs. `ls src/sagiha/ports/` |
| **C14** | **Track A, on file counts.** `src/sagiha/` stated at **106** Python files; actual is **105**. The LOC figure (12,949) and test figure (8,197) are exact | `auditoria_sagiha.md` §0 |
| **C15** | **The comparison, on Track B's ADRs.** *"Each of B's nine ADRs carries a mermaid diagram"* — there are **14** ADRs and **2** carry diagrams | `rewrite_ab_comparison.md` §2.5 |
| **C16** | **The comparison, on an artifact that does not exist.** §2.2 describes *"Blueprint §1.2 … a row per technical domain and a column per competitor"* and §5 recommends copying it. Track B's blueprint has §1.1 and then jumps to §2 | `rewrite_ab_comparison.md` §2.2, §5 |
| **C17** | **The synthesis, on its own arithmetic.** `19 covered + 17 sharpen + 34 gaps + 8 declines = 78` does not reconcile. Only the 8 declines are enumerated; there is no per-proposal bucket tag. **Eight proposals receive no verdict at all: P7, P8, P15, P32, P38, P42, P43, P44.** P65 and P74 are counted twice, in §1 and again in §3 | `synthesis_amendments.md` §1–§4 |

### 1.4 Repository state contradicting the documents

| # | Documented | Actual | Consequence |
| :--- | :--- | :--- | :--- |
| **C18** | `benchmarks/definitions/s0-core.json` is *"committed and pinned (W9.1/W9.2, audit M-1)"*, 30 tasks / 12 repos / 30 pinned SHAs, treated as TCB by both `noise-floor.md` and `auditoria_sagiha.md` §1.2 | `benchmarks/` is an **empty, git-untracked directory**. `git ls-files benchmarks` returns nothing | The `bench-aa` CI job is guarded on this file's existence, so it is a **permanent silent no-op** — a gate that cannot fail, which is the precise defect class `noise-floor.md` exists to document |
| **C19** | The brief's Appendix F and the meeting notes state `rewrite_v300_project_vision.md` *"does not currently exist in docs/00/"* | It exists, 10,205 bytes, `updated: 2026-08-05` | Drop the claim; no other action |
| **C20** | `.importlinter` `tcb-isolation` and `ci.yml` `TCB_PATHS` protect `src/sagiha/kernel/policy` and `src/sagiha/outer_loop/evaluator` | Correct **today** | At the `src/sagiha/` → `src/aether/` migration these do not fail — they **pass vacuously**. This is the mechanism F6's decision depends on |
| **C21** | The normative word budget stands at 19,720 against a 15,000 ceiling, read as a content breach | `docs_budget.py` matched ADRs by the prefix `08-decisions/`; the archive move put them at `_archive/08-decisions/` and the exemption stopped selecting. 28 files, 5,779 words re-entered. **19,720 − 5,779 = 13,941**, the pre-move figure | Not a content breach. One string. Repaired, with a drift test |
| **C22** | 19 dead relative links attributed to the archive reorganisation | All 19 were `../../` resolving to `docs/` rather than the repo root. **Every target file exists** | Repaired |

---

## Part 2 — Numeric claims and their provenance

**Legend.** `[M]` measured in this repository and re-derivable · `[3P]` third-party with a
named source · `[3P-flag]` third-party, and the citing document flags it unverified ·
`[T]` self-set target or gate, never measured · `[BARE]` asserted with no source and no
measurement.

### 2.1 The finding that governs the rest

**The only numbers in either proposal that trace to a measurement in this repository are
`src/sagiha/` size counts and the contents of `src/sagiha/e0/statistics.py`.** Every
benchmark figure, every latency, and every performance target on both sides is `[T]`,
`[BARE]` or `[3P]`.

That is not a criticism of either track — no valid benchmark number exists to cite, which
is the project's central documented fact. It does mean **no architectural fork can be
settled by appeal to a number today**, and F1 in particular cannot.

### 2.2 What is genuinely measured

| Claim | Verdict |
| :--- | :--- |
| `src/sagiha/` = **12,949 LOC**, **8,197 test LOC** (0.63:1) | `[M]` exact |
| Per-file LOC across ~29 modules (`dispatch.py` 179, `run_loop.py` 725, `cli.py` 805, `statistics.py` 259, …) | `[M]` every spot-check exact |
| `e0/statistics.py`: exact McNemar, Holm–Bonferroni, seeded bootstrap, 2000 iterations, pure stdlib | `[M]` verified line by line — `mcnemar_exact()`, `holm()`, `bootstrap_ci()` |
| SAGIHA emits **no `cache_control`** anywhere | `[M]` grep returns zero hits |
| `search.enabled` / `retrieval.enabled` ship `false` | `[M]` `config.py:364` |
| A/A run 2026-08-01: **30 tasks × 2 passes**, 12 repos, `fatal: invalid reference:`, `Pass rate 0.0%` | `[M]` — **and the source file states these are not a measurement of the harness.** 0.0% is 30 infrastructure failures |
| **105** Python files | `[M]` — documents say 106 (**C14**) |

`e0/statistics.py` is the single cleanest asset Phase 0 produced: the one component whose
claimed properties are verifiable line by line, and the one the plan proposes to port
verbatim. It is also the direct answer to F3.

### 2.3 Track B — numeric inventory

| Figure | Occurrences | Provenance |
| :--- | :--- | :--- |
| `<50ns` FFI / AST parse latency | 7 | `[BARE]` — and self-contradicted (**C12**) |
| `<10ms` worktree creation | 6 | `[BARE]`, used as a **Sprint 0 acceptance gate** |
| `0ms` container allocation | 4 | `[BARE]` — amortized by construction, and drains under Best-of-N fan-out |
| `>92%` prompt cache hit rate | 5 | `[BARE]`; the corpus figure it derives from is a context-window metric (**C8**) |
| `40x` faster than IPC/gRPC "a ~4.0ms"; gRPC `1.5–5.0ms` | 3 | `[BARE]` |
| RAM `~150MB` Python / `~15MB` Rust / `~60MB` PyO3 | 1 | `[BARE]` |
| Baseline `~68.0%` Verified / `~38–40%` Pro / `~45%` Terminal-Bench / `~50%` cache, column headed *"Baseline Prototípico (`sagiha`)"* | 2 | `[BARE]` — **no source, no date, no run.** The prototype has never produced a valid number, so no baseline can exist |
| Sprint targets 72/78/84/88, 42/46/52/56, 50/58/68/72, 65/75/88/92 | 1 table | `[T]` |
| Final targets Verified ≥90%, Pro ≥60%, Terminal-Bench ≥75% | 5 | `[T]` |
| `p < 0.05`, `N ≥ 50`, Student's t / two-tailed permutation | 4 | `[BARE]` — no power analysis |
| `37% menos tokens`; `101 Commands`; MMR `λ=0.7` | 1 each | `[BARE]` |
| Context inflation `23%` / precision drop `3%` | 1 | `[3P]` — arXiv 2602.11988; source says **>20%** (**C10**) |
| 5 sprints × ~14 days | 1 | `[T]` |

**Zero reversal conditions across all 14 ADRs.** Confirmed by reading each.

### 2.4 Track A — numeric inventory

Track A's figures are broadly self-labelled, and `measurement_strategy.md` §1c.2 is a
dedicated provenance-correction section that retracts four of its own claims unprompted.
That discipline is real and is the strongest procedural asset either track produced. The
gaps below are the exceptions to it.

| Figure | Provenance |
| :--- | :--- |
| **Runtime §1 latency table** — PyO3 ~100ns, FTS5 ~50µs, UDS ~20µs, gRPC ~200µs, tree-sitter ~2ms, container 200ms–5s, LLM 2–60s | `[BARE]` — no benchmark, no hardware, no citation. **This table is the entire load-bearing argument for A-002 and for Track A's F1 position**, including the "four to seven orders of magnitude" claim derived from it |
| *"One-shot with a perfect sandbox lands 20–40%; the gap to 70–80% is the feedback edge"* | `[BARE]` — the single largest unattributed claim in the set, and it orders the whole edit-mechanism document |
| Pro leader **~80.3%**, Verified frontier **~96%**, Fable 5 ~80%, Opus 5 ~79.2%, Confucius 74.6% | `[BARE]` — Track A flags `~80.3%` as *"worth independent re-verification"*. **F4 rests entirely on this** |
| `~12×` BoN cost difference on the shared prefix | `[BARE]` — arithmetic on published rates, presented in the consequences register as if observed |
| PyO3 `<50ns`, gRPC 1.5–5.0ms, CoW `<10ms`, pool `0ms` | `[3P-flag]` — explicitly *"not our measurements"*, recorded as design targets. **Correctly handled** |
| MECW ~92%, 70% cliff, Dumb Zone 40–60%, adherence ladder, blast radius, path-scoping 40–50% | `[3P-flag]` — each carries a "these are other people's numbers" prefix and a named experiment |
| Tool Search 55K→8.7K (−85%), selection 49%→74% | `[3P]` — Anthropic guidance, no link |
| Cache 1.25×/2× write, 0.1× read, 4 breakpoints, 20-block lookback | `[3P]` provider mechanics |
| Targets: Pro ≥80%, Verified ≥96%, lift ≥+10pts, cache >92%, RT-1 >10min, RT-2 >300MB/>1%, RT-3 >200ms | `[T]` |
| Milestone durations | **None by design** — *"the exit gates are the schedule"*. The only calendar is Track B's, adopted as indicative with an explicit "not commitments" label |

### 2.5 The asymmetry worth recording

Both tracks assert unmeasured numbers. They differ in whether they say so.

- Track A carries a provenance-correction section, retracts four of its own claims,
  prefixes third-party figures with "these are other people's numbers", and states the
  governing rule: *"A number we did not measure on our own instruments never appears in a
  result, a claim, or a regression gate."*
- Track B labels none of its figures, presents `[T]` targets as *"Baseline Prototípico"*
  for a prototype that has produced no valid number, and carries no reversal condition on
  any of its 14 ADRs.

**This is a difference in measurement discipline, and it is separable from which
architecture is correct.** On F1 specifically the two tracks are equally unmeasured:
Track A's latency table is no better sourced than Track B's `<50ns`. A reader who takes
Track A's side on F1 because Track B's numbers are unsourced has not read Track A's.

---

## Part 3 — What this changes

| Fork | Status after the audit |
| :--- | :--- |
| **F5** | **Closed.** Both tracks wrote the same rule; the brief states Track B's position backwards (**C3**) |
| **F6** | **Narrowed.** Track B has the TCB; the residual gap is that `evolution/` is bound by no contract and no commit policy exists (**C1, C2**). The competitor evidence for the strong version is inverted (**C5**) and partly fabricated (**C6**) |
| **F2** | **Narrowed to sequencing.** Both tracks want the A/A floor (**C4**); they disagree on whether a number may be published first |
| **F1** | **Unchanged and genuinely open** — and neither side may cite a number, because neither has one (**§2.5**) |
| **F4** | **Blocked on verification.** Rests on a single-session, unverified leaderboard re-baselining that its own author flags as such |
| **F3, F7–F12** | Unchanged by this audit |

**Non-architectural items with owners needed:** C18 (`bench-aa` is a permanent no-op),
C20 (TCB enforcement goes vacuous at the tree migration), C17 (eight competitor proposals
never adjudicated). C21 and C22 are repaired.

---

## Limits of this register

- **Track B has not reviewed it.** It is an audit of Track B's text against its sources,
  not a negotiation with its author. Where Track B's intent differs from Track B's text,
  the author's correction outranks this document — the same standing the brief grants
  Track B over Track A's framing.
- **It adjudicates nothing.** Findings feed
  [`rewrite_v300_decision_record.md`](./rewrite_v300_decision_record.md); the decisions are
  the meeting's.
- **Absence of evidence is reported as such.** Where a grep returns nothing, the row says
  the string is absent from the current text — not that it was never written. C2 in
  particular is consistent with the claim having been accurate against an earlier revision.
