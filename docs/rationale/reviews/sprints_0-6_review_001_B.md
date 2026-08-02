---
status: rationale
updated: 2026-08-01
retrieval: excluded
---

# SAGIHA v2 Sprint Review 001-B — Phases 0–6 (v2-S0 through v2-S6)

| Field | Value |
| :--- | :--- |
| **Document ID** | `sprints_0-6_review_001_B` |
| **Audit date** | 2026-08-01 |
| **Tree HEAD (audit)** | `eae4c22` (`refactor_aether_v2`) |
| **Scope** | v2-S0 … v2-S6 only |
| **Out of scope** | v2-S7 (Story-DAG, MCP, streaming TUI); Conductor C0+; dense retrieval (ADR-0014); AOI; RHI Tier C; A2A; performance sidecars; warm LSP |
| **Gate verdict** | **CONDITIONAL PASS** — mechanism-complete under honest-negative doctrine; release tag blocked until P0 clears |
| **Regression snapshot** | 321 passed / 11 skipped · ports 17 · lint-imports 5/5 · pyright **3 errors** · docs budget **15,183 / 15,000** |

---

## Documents Used for Evaluation

### Normative / execution plans

| Document | Role in audit |
| :--- | :--- |
| [`docs/implementation/development_plan_v2.md`](../../implementation/development_plan_v2.md) | Normative sprint sequence, epics, exit gates (v2-S0…S7) |
| [`docs/implementation/refactor_sagiha_v2_guidelines.md`](../../implementation/refactor_sagiha_v2_guidelines.md) | Phase guidelines, H-series baseline, verification commands |
| [`docs/implementation/sprint_v2_s4_options.md`](../../implementation/sprint_v2_s4_options.md) | E0 / BoN / scoring / export trade-offs (S4) |
| [`docs/implementation/sprints_tasks_order_deps_plan.md`](../../implementation/sprints_tasks_order_deps_plan.md) | Wave mapping, dependency DAG, developer prompts |
| [`docs/STATUS.md`](../../STATUS.md) | Single source of **implementation** truth (claimed state) |
| [`AGENTS.md`](../../../AGENTS.md) | CAR invariants, TCB definition, port-adapter rules |

### Vision / review corpus (rationale)

| Document | Role in audit |
| :--- | :--- |
| [`docs/rationale/reviews/next_gen_architecture_specs.md`](next_gen_architecture_specs.md) | Seed-only L6, compaction, TaintGate, FrozenRunState, B5a perimeter |
| [`docs/rationale/reviews/critical_gaps_analysis.md`](critical_gaps_analysis.md) | Pre-v2 gap taxonomy |
| [`docs/rationale/reviews/codebase_delta_refactor.md`](codebase_delta_refactor.md) | H1–H4 delta findings |
| [`docs/rationale/reviews/agi_evolution_path.md`](agi_evolution_path.md) | Conductor roadmap — **future reference only** (not scored) |

### Contracts & decisions

| Document | Role in audit |
| :--- | :--- |
| `docs/02-architecture/car-model.md` | Capability authorization model |
| `docs/02-architecture/security-and-threat-model.md` | Perimeter / T7 taint |
| `docs/03-contracts-and-models/frozen-run-state.md` | Grants-absent freeze schema |
| `docs/03-contracts-and-models/hexagonal-ports.md` | Port remoteability |
| `docs/05-tech-stack/indexing-and-retrieval.md` | Chunking / FTS5 / graph expectations |
| `docs/08-decisions/` ADRs **0019–0025** | Port consolidation, effects, seed-only, RHI, port-rent, E0-not-a-port, scoring seams |
| `docs/superpowers/specs/2026-07-31-v2-s6-retrieval-code-graph-design.md` | Approved S6 mechanism-first design |
| `docs/superpowers/plans/2026-07-31-v2-s6-retrieval-code-graph.md` | S6 implementation plan |
| `.superpowers/sdd/final-review.md` | Wave 5 whole-branch review (Approve with nits) |

### Empirical / honesty artifacts

| Document | Role |
| :--- | :--- |
| `docs/rationale/benchmarks/s1_honest_baseline.md` | Post-honesty re-measure |
| `docs/rationale/benchmarks/s1_before_baseline.md` | Pre-honesty (RC-7) |
| `docs/rationale/benchmarks/s4-harvest-findings.md` | 0/23 harvest; honest-negative BoN |
| `docs/rationale/benchmarks/noise-floor.md` | Template only — not populated |
| `docs/implementation/ci-podman-perimeter.md` | Proposed CI job (not landed) |

### Code under audit

Primary tree: `src/sagiha/` (`domain/`, `ports/`, `kernel/`, `agency/`, `adapters/`, `outer_loop/`, `e0/`, `composition.py`, `cli.py`) plus contracts under `tests/contracts/` and `tests/integration/`.

---

# Chapter 1 — Executive Summary

## 1.1 What this phase set out to do

The v2 re-baseline (`development_plan_v2.md` + `refactor_sagiha_v2_guidelines.md`) reordered work around one thesis: **instruments must tell the truth before capability ships**. The H-series delta (`codebase_delta_refactor.md`) proved fabricated gates, dead budget accounting, lying stubs, and constant `syntax_valid`. Phases 0–6 were planned to: shrink docs and lock ADRs (S0); fix honesty (S1); freeze the port surface (S2); ship context + taint + freeze (S3); harden E0 then Best-of-N (S4); land the Podman perimeter (S5); land lexical retrieval + code graph + cold-start (S6). Conductor / Story-DAG / MCP / streaming remain Phase 7+.

## 1.2 What was achieved (mechanism)

| Wave | Sprint | Mechanism | Empirical |
| :--- | :--- | :--- | :--- |
| 1 | v2-S0 | Docs/SSOT/ADRs/STATUS | Budget ceiling currently **violated** (+183 words) |
| 2 | v2-S1 | H1–H4 fixed; baselines committed | Pass-rate drop documented as the fix |
| 2 | v2-S2 | 17 ports; PURE effects; builtins; trajectory Message | Complete |
| 3 | v2-S3 | Assembler, Compactor, TaintGate, FrozenRunState | Complete |
| 4 | v2-S4 | Honest E0 stats; BoN; scoring; export | **Deferred** — no suite / noise floor |
| 4 | v2-S5 | Real Podman sandbox; egress; autonomous unlock | CI Podman **not** landed |
| 5 | v2-S6 | FTS5 + graph + tools + seed + `init` | **Deferred** — no recall/ablation suite |

**Defaults that enforce honesty:** `search.enabled=false`, `retrieval.enabled=false`.

**Operational MVP today:** honest gated coding loop (subprocess or container), cost/budget telemetry, cassette replay/resume, compaction + seed-only Layer-6 *slot*, taint + human-required mutations, freeze/thaw, CLI `run` / `replay` / `harvest` / `bench` / `export` / `init`, BoN and retrieval available but off.

## 1.3 Plan vs code (high level)

- Epics for S1–S3 and mechanism halves of S4–S6 match `src/` and STATUS’s closed claims.
- Amended **honest-negative** exit gates for S4/S6 are intentional and correctly reflected in STATUS — empirical claims were not fabricated.
- STATUS over-claims **pyright 0** (tree has 3 errors) *(Note: Double-check commit timeline — STATUS.md was accurate when baselined on 2026-07-31; the 3 pyright errors were introduced during subsequent S6 indexer work. Unchecked plan checkboxes reflect markdown maintenance backlog rather than non-delivery — double-check commit logs for exact delivery dates)*. S0 exit gate **docs ≤15k** currently fails. Plan checkboxes for S0–S2 remain unchecked though STATUS marks them closed. Port-count prose in older plan text still says “15”; code/ADR-0019/0024 correctly use **17**.

## 1.4 Architectural health (what is good)

CAR choke point, TCB isolation (import-linter 5/5), domain purity, async remoteable ports, grants-absent freeze, seed-only assembler, loud S7 stubs (MCP/OTel/stream), and fail-closed export eligibility are **intact**. Prior Critical H1–H4 defects are **remediated**.

## 1.5 Gate decision

| Question | Answer |
| :--- | :--- |
| Mechanism freeze through Wave 5? | **Yes**, after P0 |
| Tag / claim “all green”? | **No** until pyright + docs budget clear |
| Flip search/retrieval default-on? | **No** until suite + ablations (P1) |
| Start v2-S7? | **Yes after P0** — S7 deps are mechanism, not empirics |

**Overall: CONDITIONAL PASS.** Chapter 2 lists every defect that blocks a 90+/100 posture across architecture, quality, hexagonal purity, DRY, and release honesty.

---

# Chapter 2 — Defects, Drifts, Blockers & Remediation

This chapter is **problem-focused only**. It inventories what is wrong, why it matters for architecture / quality / SOLID / hexagonal / DRY / workflow, and how to fix it. Ordered for a path to **≥90/100** on major software-engineering axes before tagging and before default-on capability.

---

## 2.1 Scoring axes & current penalty map

| Axis | Why score is pulled down | Target to clear 90+ |
| :--- | :--- | :--- |
| **Release honesty** | STATUS claims pyright 0; budget CI would fail | P0 green signals match STATUS |
| **Hexagonal / contracts** | `Indexer` Protocol ≠ adapter signature | Structural conformance + pyright 0 |
| **Architecture cohesion** | Dual symbol-path namespaces; dead sequential search shell | One naming scheme; one search path |
| **Config honesty / YAGNI** | `max_chunk_tokens` accepted then discarded | Implement or remove field |
| **DRY** | `SKIP_DIRS` copied 4×; IndexService reaches private `_db_path` | Shared walk constants; public APIs |
| **Security ops** | Perimeter not in CI; no per-grant short-lived secrets | CI Podman job; clarify or implement |
| **Measurement integrity** | Empty suite / template noise floor | Suite ≥30 + populated floor before claims |
| **Docs SSOT** | Plan checkboxes stale; 15k overshoot | Syncboxes + demotions |
| **Retrieval quality (latent)** | No chunk prefix; init ignores graph | Spec-faithful indexing before default-on |

---

## 2.2 Critical — release / gate blockers

These contradict claimed green signals or break the S0 exit gate. **Must fix before any release tag.**

### C-R1 — Pyright fails while STATUS claims zero errors

| | |
| :--- | :--- |
| **Evidence** | `uv run pyright src/sagiha` → **3 errors**. `docs/STATUS.md` Frozen Regression Signals row claims **0 errors** *(Note: Double-check commit timeline — STATUS.md reflected 0 pyright errors when written on 2026-07-31. The 3 errors arose during recent S6 indexer implementation; double-check whether this is post-closeout regression drift rather than intentional misrepresentation)*. |
| **Locations** | `src/sagiha/composition.py` (~158): `FTS5Indexer` not assignable to `Indexer` because `neighbors` types diverge. `src/sagiha/adapters/indexer/service.py` (~52, ~78): `reportPrivateUsage` on `indexer._db_path`. |
| **Why bad** | Release honesty is part of the v2 thesis. A STATUS matrix that lies about typecheck reintroduces the H1/H5 failure mode (a number that looks measured but is false). Hexagonal ports require adapters to structurally satisfy Protocols. |
| **How to fix** | (1) Align `Indexer.neighbors` and `FTS5Indexer.neighbors` on one parameter name and semantic (`query: str` for FTS seed, **or** rename port to `search` / add a separate `neighbors_of_path`). (2) Expose `db_path` as a public read-only property or pass path into `IndexService` at construction — never read `_db_path`. (3) Re-run pyright; update STATUS only when green. |

### C-R2 — Normative documentation budget exceeded

| | |
| :--- | :--- |
| **Evidence** | `python3 scripts/docs_budget.py --max 15000` → FAIL — **15,183** words (over by **183**). S0 exit gate requires ≤15k. |
| **Why bad** | Doc mass outrunning code was an explicit anti-pattern in the guidelines. CI `docs-budget` fails → “governance phase closed” is false. |
| **How to fix** | Demote or trim ≥183 normative words (STATUS bloat, architecture long-form, implementation notes mis-tagged `normative`). Prefer demote to `rationale` + `retrieval: excluded`. Confirm EXIT 0 before merge/tag. |

---

## 2.3 Major — architecture, contracts, measurement integrity

Block **default-on** of search/retrieval and any published empirical claim. Mechanism freeze may proceed with these documented, but **90+ architecture/quality scores require addressing them**.

### M1 — No pinned benchmark suite / noise floor (S4 empirical half)

| | |
| :--- | :--- |
| **Evidence** | `benchmarks/definitions/s0-core.json` missing; `noise-floor.md` is an explicit **template**; CI `bench-aa` skips; harvest 0/23 (`s4-harvest-findings.md`). |
| **Why bad** | Without a suite, BoN vs single-shot, retrieval ablations, and init ablations are unfalsifiable. Shipping “complete” measurement without numbers is fine only while defaults stay off — flipping defaults without P1 re-creates fabricated success. |
| **How to fix** | Harvest/validate an external or synthetic ≥30-task suite; commit `s0-core.json`; run `bench --aa`; populate `noise-floor.md`; unguard CI. Only then publish deltas or enable features. |

### M2 — Podman perimeter not gated in CI (S5)

| | |
| :--- | :--- |
| **Evidence** | `.github/workflows/ci.yml` has no podman job; only proposal `docs/implementation/ci-podman-perimeter.md`. Tests exist under `@pytest.mark.podman` but are skipped in default CI. |
| **Why bad** | ADR-0006 makes the sandbox the perimeter. Untested in CI means regressions in egress/`network=none`/conformance can land unnoticed. Autonomous unlock without CI proof weakens the security story. |
| **How to fix** | Land the proposed human-authored TCB-adjacent CI job; run workspace conformance + perimeter canary on Podman runners. |

### M3 — `Indexer.neighbors` Protocol vs FTS implementation (hexagonal break)

| | |
| :--- | :--- |
| **Evidence** | Port: `neighbors(self, path: str, …)`. Adapter: `neighbors(self, query: str, …)` running FTS `MATCH`. Seed correctly passes **goal text**, not a path. |
| **Why bad** | Violates hexagonal conformance: Protocol is the contract. Callers reading the port expect path-scoped neighbors; implementation is full-text search. This is the root of C-R1’s composition type error. |
| **How to fix** | Decide the product API: (A) rename to `search(query: str)` on the Protocol and update all call sites; or (B) keep `neighbors(path)` as graph expansion and add `search` for FTS. Update `build_retrieval_seed` accordingly. Add a contract test that the adapter is assignable to `Indexer`. |

### M4 — Dual symbol-path namespaces (chunking vs code graph)

| | |
| :--- | :--- |
| **Evidence** | `chunking._module_name` → last path segment (`pkg/util.py` → `util`); `treesitter._module_name` → dotted package path (`pkg.util`). Same symbol appears as `util.greet` vs `pkg.util.greet`. |
| **Why bad** | Breaks cohesion between indexer and graph; call-resolution and impact analysis become inconsistent; violates DRY and single source of naming truth. Blocks trustworthy retrieval default-on. |
| **How to fix** | Extract one `_module_name(path) -> str` shared helper (prefer full dotted relative to package root). Reindex fixtures; assert chunk symbol_path prefixes match graph `defines` names in conformance tests. |

### M5 — `max_chunk_tokens` is a dead config knob

| | |
| :--- | :--- |
| **Evidence** | `RetrievalConfig.max_chunk_tokens` exists; `analyze_python_tree` does `del max_chunk_tokens`; FTS hardcodes `1024`. |
| **Why bad** | Config honesty is part of instrument honesty. Operators believe they can bound chunk size; they cannot. Oversized AST nodes hurt FTS quality. |
| **How to fix** | Implement statement-boundary splits when chunk tokens exceed budget **or** remove the config field and document fixed policy until ablations exist. |

### M6 — Plan / STATUS SSOT drift (process quality)

| | |
| :--- | :--- |
| **Evidence** | `development_plan_v2.md` S0–S2 epics still `[ ]`; STATUS marks closed. Older plan text says “15 ports”; code has 17 *(Note: Double-check document roles — development_plan_v2.md is a historical planning document, whereas STATUS.md is the normative SSOT; double-check code delivery in git history before assuming non-delivery from markdown checkboxes)*. |
| **Why bad** | Agents and humans retrieve contradictions. Undermines S0’s purpose. |
| **How to fix** | Tick closed epics; replace “15” with “17 (ADR-0019 restated + ADR-0024)”; one normative claim set. |

### M7 — Chunk text missing spec prefix envelope

| | |
| :--- | :--- |
| **Evidence** | Indexing spec requires path + symbol path + signature prefix on chunks; stored text is often raw AST span. |
| **Why bad** | Retrieval hits lack standalone context; recall@10 will be attributed wrongly to “vocabulary” when chunking is the real miss (exactly the ADR-0014 warning). |
| **How to fix** | When writing FTS rows, prepend `path\nsymbol_path\nsignature\n---\n` (or equivalent) before body; update conformance assertions. |

---

## 2.4 Minor — quality, DRY, dead code, incomplete wiring

Address to push architecture/quality into the 90s; not merge-blockers for mechanism freeze.

### m1 — `sagiha init` never passes a code graph

| | |
| :--- | :--- |
| **Evidence** | `cli.py` calls `generate_agents_md(..., graph=None)`. |
| **Why bad** | Spec optional graph summary never appears; cold-start under-delivers vs S6.4 intent. |
| **How to fix** | On `--reindex` or when `.sagiha/code_graph.db` exists, build/load `TreeSitterCodeGraph` and pass it in. |

### m2 — Init module discovery misses `src/*.py`

| | |
| :--- | :--- |
| **Evidence** | `_discover_python_modules` only top-level `*.py` and `*/__init__.py` packages. |
| **Why bad** | Common layout (`src/pkg/...`) under-represented in `AGENTS.md`. |
| **How to fix** | Walk `src/` and package roots; exclude tests/venvs via shared `SKIP_DIRS`. |

### m3 — `SKIP_DIRS` duplicated four times

| | |
| :--- | :--- |
| **Evidence** | Identical frozensets in `fts5.py`, `service.py`, `treesitter.py`, `generate.py`. |
| **Why bad** | DRY violation; skip-list drift risk. |
| **How to fix** | Single `sagiha.adapters.indexer.walk.SKIP_DIRS` (or `domain` constant) imported everywhere. |

### m4 — `IndexService` bypasses indexer encapsulation

| | |
| :--- | :--- |
| **Evidence** | Direct SQLite against `indexer._db_path`. |
| **Why bad** | Breaks adapter boundary; couples service to FTS schema; causes pyright private-usage errors. |
| **How to fix** | Public methods on `FTS5Indexer`: `replace_file_chunks(...)`, `clear_path(...)`, `chunk_count()`. |

### m5 — Full reindex does not prune deleted files

| | |
| :--- | :--- |
| **Evidence** | Reindex updates seen files; no wipe/orphan delete. |
| **Why bad** | Stale chunks/edges after deletes → wrong retrieval / impact. |
| **How to fix** | Track seen paths; delete DB rows for unseen paths, or wipe + full rebuild on `rebuild_from_root`. |

### m6 — Dead / misleading search scaffolding

| | |
| :--- | :--- |
| **Evidence** | `adapters/search/sequential.py` still SENIOR TODO shell while `BestOfNSearch` is real. |
| **Why bad** | Dual-path confusion; looks like N=1 is unfinished when BoN covers sequential launch. |
| **How to fix** | Delete shell, or make it a thin wrapper documenting “use BestOfN with n=1”, or raise `NotImplementedError` with pointer. |

### m7 — Export CLI uses static six-tool schemas

| | |
| :--- | :--- |
| **Evidence** | Export path builds from `BUILTIN_SCHEMAS` without code-intel tools. |
| **Why bad** | Trajectories recorded with retrieval enabled may not round-trip schema-faithfully in export. |
| **How to fix** | When exporting runs that used code-intel tools, reconstruct schemas from registry snapshot stored on the run (preferred) or from enabled config. |

### m8 — S5 credential story incomplete vs plan wording

| | |
| :--- | :--- |
| **Evidence** | Env scrub + secret path filter exist; “per-grant short-lived injection” from plan not found *(Note: Double-check sandbox scope — host environment scrubbing and secret file exclusion are fully active in ContainerSandbox; double-check whether per-grant short-lived secret injection was intended as a Phase 7 enhancement)*. |
| **Why bad** | Spec/plan over-promise vs implementation; security reviewers will flag. |
| **How to fix** | Either implement short-lived inject-per-grant or amend plan/STATUS to state host-env scrub + materialize path exclusion only. |

### m9 — TaintGate does not block `run_command`

| | |
| :--- | :--- |
| **Evidence** | `_TAINT_BLOCKED_TOOLS = {apply_edit, write_file}`; `run_command` allowed after taint *(Note: Double-check threat model rationale — run_command is permitted under taint to allow read-only inspection commands such as git status; double-check whether shell blocking is desired or if container sandbox egress firewall is the intended isolation boundary)*. |
| **Why bad** | Spec wording sometimes lists broader mutation set; shell remains a write/exfil channel on subprocess runtime. |
| **How to fix** | Keep documented tradeoff for gate git under subprocess; for `runtime=container`, rely on perimeter; optionally add autonomy-level policy: tainted + autonomous → deny `run_command` unless allowlisted PURE argv. |

### m10 — Unused / dead helpers

| | |
| :--- | :--- |
| **Evidence** | e.g. `_parse_symbol_ref` unused in graph adapter (per S6 review). |
| **Why bad** | Noise, false maintenance surface. |
| **How to fix** | Delete or wire; keep pyright unused checks clean. |

### m11 — MCP `list_tools` returns `[]` instead of raising

| | |
| :--- | :--- |
| **Evidence** | `invoke_tool` raises; `list_tools` returns empty *(Note: Double-check MCP specification — list_tools returning [] is documented in adapters/mcp/driver.py as a truthful null for zero connected servers rather than a false stub)*. |
| **Why bad** | Mild H3 inconsistency (empty is argued as truthful). |
| **How to fix** | Accept with comment, or raise until S7 implements discovery. |

---

## 2.5 Performance & operational risks (latent)

Not measured with profilers in this audit; flagged as **risks**, not proven bugs *(Note: Double-check with empirical profiler benchmarks before taking these items strictly as factual runtime bottlenecks on standard repository sizes)*.

| Risk | Why it matters | Mitigation |
| :--- | :--- | :--- |
| **Dual work at scale if one-parse regresses** | Full-repo Tree-sitter twice would dominate cold start | Keep `IndexService` one-parse invariant in CI contract test |
| **No incremental watch daemon** | Spec deferred; large repos pay full reindex on cold start | Accept for MVP; add `watchfiles` later with measured trigger |
| **Stale index after deletes (m5)** | Wrong retrieval / impact | Prune orphans |
| **Oversized unsplit chunks (M5)** | FTS noise, token blowups when seeding | Implement `max_chunk_tokens` splits |
| **BoN parallel without suite** | Cost explosions if someone enables search live | Keep `enabled=false`; document spend caps |

---

## 2.6 What is *not* a defect (do not “fix” into overclaim)

| Item | Why it is acceptable |
| :--- | :--- |
| S4/S6 empirical halves unpublished | Amended honest-negative exit gates; STATUS accurate |
| `coverage_not_decreased=None` | No Toolchain adapter yet — honest absence |
| MCP/OTel/stream stubs raising | Loud stubs; S7 scope |
| Dense retrieval absent | ADR-0014 |
| Conductor absent | Explicitly out of scope until S7 |
| `search`/`retrieval` default false | Correct fail-safe |

---

## 2.7 Prioritized remediation checklist (path to 90+)

### P0 — Before tag / before claiming green (unblocks CONDITIONAL → PASS)

- [ ] **C-R1** Align `Indexer`/`FTS5Indexer.neighbors` (or split APIs); stop using `_db_path`
- [ ] **C-R1** `uv run pyright src/sagiha` → 0 errors
- [ ] **C-R2** Docs budget ≤15,000 normative words
- [ ] Update `docs/STATUS.md` regression table only after P0 green

### P1 — Before default-on or publishing deltas (architecture / measurement 90+)

- [ ] **M1** Commit ≥30-task suite + populate noise floor; unguard `bench-aa`
- [ ] **M3/M4/M5/M7** Retrieval contract + symbol namespace + chunk budget + chunk prefix
- [ ] **M2** CI Podman perimeter job
- [ ] Ablations: BoN vs single-shot; retrieval on/off; init on/off — publish or shelve honestly

### P2 — Quality / DRY / completeness (push toward 95)

- [ ] **m1–m5** Init graph wiring, discovery, SKIP_DIRS, encapsulation, orphan prune
- [ ] **m6–m11** Dead search shell, export schemas, credential wording, taint/policy docs, unused helpers
- [ ] **M6** Tick plan checkboxes; fix port-count prose

### P3 — Explicitly after S7 / funding triggers

- MCP, streaming steer, Story-DAG, OTel, Conductor C0, dense tier, learned scorers

---

## 2.8 Suggested “definition of ready” for 90+/100

The project may claim **≥90 on architecture, hexagonal purity, honesty, and release discipline** when:

1. All **P0** boxes are checked and CI mirrors them.
2. Import-linter 5/5, pytest monotonic, replay green, **pyright 0**, docs budget green — and STATUS matches.
3. Port adapters pass structural conformance (no Protocol/impl signature drift).
4. Single symbol-path and walk vocabulary shared by indexer + graph (DRY).
5. Config knobs that exist either work or are removed.
6. Search/retrieval remain off **or** P1 empirics are published.
7. Perimeter tests run in CI for the container path.

Until then, the accurate public claim is: **mechanism-complete through v2-S6 under honest-negative defaults; CONDITIONAL PASS pending P0.**

---

## Appendix A — Sprint delivery matrix (reference)

| Sprint | Status | Open problem IDs |
| :--- | :--- | :--- |
| v2-S0 | Partial | C-R2, M6 |
| v2-S1 | Complete | — (honest `None` coverage by design) |
| v2-S2 | Complete | m6, M6 prose |
| v2-S3 | Complete | m9 (documented tradeoff) |
| v2-S4 | Mechanism complete / empirics deferred | M1 |
| v2-S5 | Mechanism complete / CI gap | M2, m8 |
| v2-S6 | Mechanism complete / empirics deferred | C-R1, M3–M5, M7, m1–m5, m7, m10 |

## Appendix B — Commands to re-verify this report

```bash
uv run pytest -q
uv run pyright src/sagiha
uv run lint-imports
uv run ruff check src/sagiha
python3 scripts/docs_budget.py --max 15000
grep -rn "(Protocol)" src/sagiha/ports/ | wc -l   # expect 17
```

---

*End of `sprints_0-6_review_001_B.md`. Next engineering step: execute Chapter 2 §2.7 P0, then start v2-S7 or P1 measurement track.*
