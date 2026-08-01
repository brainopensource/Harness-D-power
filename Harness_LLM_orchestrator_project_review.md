---
status: rationale
updated: 2026-08-01
retrieval: excluded
---

# SAGIHA v2 — Senior Architect Review Gate: Audit V3 (Sprints v2-S0 → v2-S6)

| Field | Value |
| :--- | :--- |
| **Document ID** | `Harness_LLM_orchestrator_project_review` |
| **Audit date** | 2026-08-01 |
| **Tree HEAD** | `eae4c22` (`refactor_aether_v2`) |
| **Auditor role** | Senior Principal Software Architect & Systems Auditor |
| **Scope** | `v2-S0` … `v2-S6` only |
| **Out of scope** | `v2-S7` (Story-DAG, MCP, streaming TUI); Conductor C0+; dense retrieval (ADR-0014); AOI; RHI Tier C; A2A; performance sidecars; warm LSP |
| **Prior reports adjudicated** | `sprints_0-6_review_001.md`, `sprints_0-6_review_001_B.md` |
| **Host facts** | Podman 5.8.4 present → the 11 `@pytest.mark.podman` tests **execute** here |

> **Method note.** Every number in Section 1 is from a command I ran against this tree at this
> HEAD, captured in Section 1.2. Where a prior report's number disagrees, Section 6 says which
> one is right and why. No score in this document is a subjective "/100" rating — the previous
> two reports both invented those, and they are not reproducible, so they are not repeated here.

---

# Section 1 — Executive Summary & Gate Decision

## 1.1 Gate Decision: **CONDITIONAL PASS — release tag BLOCKED**

The v2 re-baseline delivered its architectural thesis. The CAR choke point, TCB isolation,
grants-absent freeze, seed-only Layer-6 assembler, honest `None`-valued gates, real spend
telemetry, and the rootless Podman perimeter are all **genuinely implemented and verified by
tests** — not scaffolded, not fabricated. The H1–H4 instrument-honesty defects from
`codebase_delta_refactor.md` are remediated, and I confirmed each one in code (Section 3.3).

The tag is nevertheless blocked, and blocked harder than either prior report concluded, for two
reasons:

1. **Five of seven CI-enforced verification gates are currently RED**, not two. Both prior
   reviews reported only `pyright` and `docs_budget`. They missed that `.github/workflows/ci.yml`
   also runs `ruff check .`, `ruff format --check .`, and `scripts/check_links.py` — and all
   three fail, the last with **106 dead relative links**. `docs/STATUS.md` claims "Lint: clean".
   That claim is false today.
2. **A new Critical defect neither prior report found: seed retrieval silently fabricates an
   empty result set.** `FTS5Indexer.neighbors` swallows `sqlite3.OperationalError` and returns
   `[]`. Because `build_retrieval_seed` passes the raw task goal into FTS5 `MATCH`, any goal
   containing `(`, `)`, `'`, `-`, or `:` — i.e. essentially every real coding goal — raises an
   FTS5 syntax error that is converted into a plausible-looking "no results". This is precisely
   the H5 failure mode v2-S1 exists to eliminate, re-introduced in v2-S6, in the one subsystem
   whose whole purpose is measurement-gated capability. Evidence and reproduction in **C-1**.

Mechanism freeze through Wave 5 is otherwise sound. `v2-S7` may begin once P0 clears; its
dependencies are mechanism, not empirics.

## 1.2 Summary Scorecard — commands executed at HEAD `eae4c22`

| # | Gate | Command | Required | **Measured** | Status |
| :- | :--- | :--- | :--- | :--- | :--- |
| 1 | Test suite | `uv run pytest -q` | ≥ 332 passed, 0 failed | **332 passed, 0 failed, 0 skipped** (165.5 s) | ✅ **PASS** |
| 1b | — non-Podman subset | `uv run pytest -q -m "not podman"` | — | **321 passed, 11 deselected** | ✅ informational |
| 2 | Type check | `uv run pyright src/sagiha` | 0 errors | **3 errors, 0 warnings** | ❌ **FAIL** |
| 3 | Import layering | `uv run lint-imports` | 5/5 kept | **5 kept, 0 broken** (135 files, 590 deps) | ✅ **PASS** |
| 4a | Lint (CI scope) | `uv run ruff check .` | 0 | **34 errors** (25 fixable) | ❌ **FAIL** |
| 4b | Lint (src scope) | `uv run ruff check src/sagiha` | 0 | **1 error** (`cli.py:89` I001) | ❌ **FAIL** |
| 4c | Format | `uv run ruff format --check .` | 0 | **17 files would be reformatted** | ❌ **FAIL** |
| 5 | Docs budget | `python3 scripts/docs_budget.py --max 15000` | ≤ 15,000 | **15,183 words (over by 183)**, exit 1 | ❌ **FAIL** |
| 6 | Link integrity | `python3 scripts/check_links.py` | 0 broken | **106 dead relative links**, exit 1 | ❌ **FAIL** |
| 7 | Event catalog | `python3 scripts/gen_event_catalog.py --check` | in sync | **in sync (38 events)**, exit 0 | ✅ **PASS** |
| 8 | Port surface | `grep -rn "(Protocol)" src/sagiha/ports/` | 17 across 16 files | **17 Protocols, 16 port modules** | ✅ **PASS** |

**Sprints:** 7 planned (S0–S6). **Mechanism-complete: 7/7.** **Fully closed including exit
gates: 5/7** — S0 fails its own ≤15k word gate, S6 fails `pyright` and ships a broken retrieval
query path. S4 and S6 empirical halves are *correctly and honestly* deferred, not failures.

## 1.3 Top 3 Strengths

1. **The honesty doctrine is real, not decorative.** `gate_evaluator.py` genuinely shells out to
   `git diff` against `RunContext.base_commit`, genuinely returns `None` when it cannot compute a
   check, and `None` genuinely never counts as a pass. `_stage_intent_to_add` closes the
   untracked-file bypass that would otherwise let an agent write new files past
   `tests_unmodified`. `e0/statistics.py` implements a real exact McNemar test, a seeded
   percentile bootstrap, and Holm correction in pure stdlib — reproducible by construction. This
   is the strongest part of the codebase and it is stronger than either prior report credited.
2. **The capability-security core holds under inspection.** `kernel/dispatch.py` is a true single
   choke point: policy authorization, *unconditional* `verify_grant()` at point of effect (with an
   in-code comment explaining precisely why a `getattr` duck-type would be a hole), governor lease
   acquisition in a `try/finally`, and broad exception capture that converts any adapter blow-up
   into a `ToolResult(is_error=True)` rather than a crash. `FrozenRunState` is provably
   grants-absent and enforced by a contract test. `lint-imports` keeps 5/5 including
   "Trusted computing base depends on nothing mutable".
3. **The taint deviation is documented, reasoned, and correct.** The 18-line comment at
   `dispatch.py:127-144` explains why the `<untrusted-data>` envelope is applied at
   `assembler.py` rather than at dispatch: wrapping at the choke point corrupted `GateEvaluator`'s
   parse of `git diff --numstat` and silently re-broke three coding gates. That is an engineer
   who found a subtle regression, fixed it at the right layer, and wrote down why. Machine
   consumers get clean bytes; the model cannot be shown unlabelled ones.

## 1.4 Top 3 Critical Risks / Drifts

1. **C-1 — Seed retrieval silently returns fabricated empty results** (new; §4). Layer-6
   retrieval is non-functional for realistic goals *and lies about it*. Any future
   retrieval-on/off ablation run today would produce a correct-looking negative result for
   entirely the wrong reason, and that negative would then be published as evidence.
2. **C-2 — Release signals contradict `docs/STATUS.md`; 5/7 CI gates red.** STATUS asserts
   "Type check 0 errors" and "Lint clean". Both false. The S0 governance sprint's own two gates
   (word budget, link integrity) both fail, one of them by 106 broken links. "Governance phase
   closed" is not currently a true statement.
3. **C-3 — No contract test asserts adapter→Protocol assignability.** This is the *structural*
   defect behind C-R1, and neither prior report named it as the root cause.
   `tests/contracts/test_indexer_conformance.py` exercises `FTS5Indexer` concretely and passes;
   `tests/contracts/test_port_shape.py` enumerates Protocols but never checks that any adapter
   satisfies one. So a Protocol/impl signature divergence lands green in pytest and is caught
   only by `pyright` — and STATUS was reporting `pyright` from memory. The hexagon has no
   automated conformance edge.

---

# Section 2 — Sprint Delivery Audit Matrix (v2-S0 → v2-S6)

| Sprint | Objective | Planned Epics | Status | Delivered Modules / Files | Open Issues / Drifts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **v2-S0** | Docs shrink, SSOT, ADRs, governance | S0.1 ≤15k normative budget · S0.2 `rationale/` migration · S0.3 SSOT consolidation · S0.4 ADRs 0019–0023 · S0.5 STATUS re-baseline | **Partial — exit gate RED** | `docs/STATUS.md`, `docs/08-decisions/0019`–`0025` (26 ADRs), `scripts/docs_budget.py`, `scripts/check_links.py`, `scripts/gen_event_catalog.py` | **C-2** budget 15,183 > 15,000 · **C-3d** 106 dead links · **M-6** plan checkboxes stale (18 `[ ]` vs 17 `[x]`) · **M-7** "21 → 15 ports" prose survives at `development_plan_v2.md:19,221` · **m-12** 8 docs carry no `status:` tag, incl. `refactor_sagiha_v2_guidelines.md` — a normative-in-practice doc escaping the budget by being untagged |
| **v2-S1** | Instrument honesty (H1–H4) | S1.1 real base-commit gates · S1.2 spend telemetry · S1.3 `ast.parse` syntax gate · S1.4 loud stubs · S1.5 honest re-measure | **Complete** | `outer_loop/evaluator/gate_evaluator.py`, `kernel/governor.py`, `agency/run_loop.py:405`, `adapters/workspace/local.py:81`, `docs/rationale/benchmarks/s1_honest_baseline.md` | None blocking. `coverage_not_decreased=None` is a correct honest absence (no `Toolchain` adapter), not a gap. |
| **v2-S2** | Port consolidation & kernel corrections | S2.1 21→17 ports · S2.2 PURE/DESTRUCTIVE effects · S2.3 builtin tool fixes · S2.4 composition hardening · S2.5 trajectory `Message` completeness | **Complete** | `ports/` (17 Protocols / 16 modules), `kernel/policy/effects.py`, `adapters/tools/builtins.py`, `composition.py` | **m-6** `adapters/search/sequential.py` is a live-exported lying stub (see §4) · **M-7** prose drift |
| **v2-S3** | Context engine & taint | S3.1 `ContextAssembler` seed-only L6 · S3.2 `ExchangeCompactor` · S3.3 TaintGate v1 monotonic · S3.4 `FrozenRunState` + role failover | **Complete** | `agency/context/assembler.py`, `agency/context/compactor.py`, `kernel/policy/engine.py`, `agency/freeze.py`, `domain/control.py` | **m-9** `run_command` not taint-blocked — deliberate, asserted in code (`_TAINT_BLOCKED_TOOLS <= MUTATION_TOOLS`), documented tradeoff; needs a doc amendment, not a code change |
| **v2-S4** | E0 hardening & Best-of-N | S4.0 ADR-0024 cleanup · S4.1 E0 statistics · S4.2 BoN over worktrees · S4.3 S-0/S-1 ranking-only scoring · S4.4 SFT/DPO exporter | **Mechanism complete · empirics deferred (honest)** | `e0/{harvester,runner,statistics,reporter,protocols}.py`, `adapters/search/best_of_n.py`, `outer_loop/export/{eligibility,sft,dpo,redaction,license,schema}.py` | **M-1** no pinned suite: `benchmarks/definitions/` **does not exist**; `noise-floor.md` is a self-declared template · `search.enabled=false` is the correct fail-safe · **NOTE:** the audit brief's path `outer_loop/export/exporter.py` does not exist |
| **v2-S5** | Perimeter & isolation | S5.1 rootless Podman `ContainerSandbox` · S5.2 egress allowlist + secret isolation · S5.3 `autonomous` unlock | **Mechanism complete · CI gap** | `adapters/sandbox/container.py`, `domain/config.py:485-498` | **M-2** no Podman job in `.github/workflows/ci.yml`; only the proposal `docs/implementation/ci-podman-perimeter.md` · **m-8** "per-grant short-lived secret injection" in plan text is not implemented (env scrub + materialize-path exclusion are) |
| **v2-S6** | Retrieval, code graph, cold start | S6.1 FTS5 + AST chunking · S6.2 Tree-sitter graph · S6.3 code-intel builtins · S6.4 `sagiha init` · S6.5 frontmatter exclusion | **Partial — Critical defect** | `adapters/indexer/{fts5,chunking,service,frontmatter}.py`, `adapters/code_graph/treesitter.py`, `outer_loop/init/generate.py` | **C-1** silent FTS query failure · **C-R1** `Indexer.neighbors` Protocol break (3 pyright errors) · **M-3** dual symbol-path namespaces · **M-4** dead `max_chunk_tokens` · **M-5** no chunk prefix envelope · **m-1..m-5** init graph wiring, discovery naming, `SKIP_DIRS` ×4, `_db_path` leak, no orphan prune · **NOTE:** the brief's path `outer_loop/init/generator.py` is wrong — the file is `generate.py` |

---

# Section 3 — Architectural Invariant & Security Review

## 3.1 CAR Policy & TCB Containment — **PASS**

- **Single choke point.** `kernel/dispatch.py:26` `dispatch()` is the only path from Agency intent
  to Runtime effect. Verified: no `agency/` module imports `adapters/` or `runtime/`, enforced by
  the `Agency must not reach the Runtime` import contract (KEPT).
- **Authorization.** `policy.authorize(call, ctx)` at `dispatch.py:63`; denial short-circuits with
  a `ToolCallDenied` event and an error `ToolResult`. `PolicyEngine.authorize` lives at
  `kernel/policy/engine.py:138` — *not* L48 as `sprints_0-6_review_001.md` claims.
- **Point-of-effect grant verification is unconditional.** `dispatch.py:85` calls
  `await policy.verify_grant(decision.grant_id)` with no `getattr`/`hasattr` guard, and the
  in-code rationale explains that a duck-typed check would let a non-conforming engine skip
  verification silently. Expired and forged grant ids fail closed.
- **Grant containment.** `domain/control.py:45` — `Decision.grant_id` is documented as
  "correlation only — the `Grant` itself never leaves dispatch". Enforced by
  `tests/contracts/test_port_shape.py::test_no_grant_in_any_public_signature`.
- **TCB isolation.** `lint-imports` contract "Trusted computing base depends on nothing mutable"
  is KEPT. `kernel/policy/effects.py` documents *why* it lives in `kernel/policy/`: the existing
  `tcb-isolation` contract plus CI's `tcb-check` make the PURE-argv allowlist agent-unwritable
  for free, with no new gate. That is good design economics.
- **Effect classification.** `classify_command()` narrows `DESTRUCTIVE`→`PURE` only, never widens;
  `git` requires a second `PURE_GIT_OPS` check so `git commit`/`push`/`checkout` stay destructive;
  `bash -lc` is never narrowed. Correct.

**Adjudication of a prior claim:** `sprints_0-6_review_001.md` Defect 3.1 recommends that
`ToolRegistry.dispatch()` catch `NotImplementedError` and wrap it in an error `ToolResult`.
**This is already implemented** at `dispatch.py:109-119`, which catches bare `Exception` — a
superset. The recommendation is redundant; no action needed.

## 3.2 Hexagonal Port Remoteability — **PASS with one structural gap**

- **17 Protocols across 16 port modules**, matching ADR-0019/ADR-0024. Confirmed by grep.
- **All port methods are `async`** — `grep -n "    def " src/sagiha/ports/*.py` returns nothing;
  `test_every_port_method_is_async` enforces it.
- **Domain purity** — the `Domain models have no I/O dependencies` contract is KEPT.
- **Serializability** — `test_all_port_payloads_are_serializable`, `test_no_untyped_dict_crosses_a_port`,
  and `test_all_datetimes_are_aware` all pass.
- **Gap (C-3):** nothing asserts that a concrete adapter is *assignable to* its Protocol.
  `test_indexer_conformance.py` calls `FTS5Indexer` methods directly and passes even though
  `FTS5Indexer` does not satisfy `Indexer`. This is the hole through which C-R1 landed green.

## 3.3 Instrument Honesty (H1–H4) — **all remediated, verified in code**

| Finding | Requirement | Verified location | Verdict |
| :--- | :--- | :--- | :--- |
| **H1** | Real `git diff` vs `RunContext.base_commit` | `gate_evaluator.py:109/120/135` (`_tests_unmodified`, `_diff_within_bounds`, `_no_new_suppressions`), each returning `None` on failure; `:184-186` — absent `base_commit` ⇒ all three `None` ⇒ fail closed; `:97` `_stage_intent_to_add` closes the untracked-file bypass | ✅ **FIXED** |
| **H2** | Real token usage + `record_spend` + reachable budget break | `run_loop.py:405` `await self._governor.record_spend(ctx.run_id, cost_usd)` after every turn; `:327-338` budget check → freeze + budget-park (`status="input-required"`) | ✅ **FIXED** |
| **H3** | Loud stubs, no false success | `adapters/mcp/driver.py` `invoke_tool` raises `NotImplementedError("v2-S7")`; `adapters/telemetry/otel.py:26` raises. `list_tools()` returning `[]` is documented as a truthful null for zero connected servers — **acceptable** | ✅ **FIXED** (one exception: **m-6**, below) |
| **H4** | `ast.parse` before writing Python | `adapters/workspace/local.py:81-82` — `ast.parse(text)` inside `apply_edit`, `SyntaxError` rejected | ✅ **FIXED** |
| **H5** | No fabricated statistics | `e0/statistics.py` — real `mcnemar_exact`, seeded `bootstrap_ci`, `holm`; `beats_noise_floor=None` when no floor supplied | ✅ **FIXED** — **but re-introduced elsewhere as C-1** |

**The H3 exception (m-6).** `adapters/search/sequential.py` is exported from
`adapters/search/__init__.py` and returns fabricated values: `propose()` returns invented
`candidate-<uuid>` branch IDs for non-existent worktrees, `evaluate()` returns `None`, `select()`
returns `branch_ids[0]`. Under the v2-S1 doctrine this is a *lying stub*, not dead code — the
exact class of artifact S1.4 was chartered to eliminate. Both prior reviews classified it as a
Minor "dead scaffolding" item; it is better read as a surviving H3 instance. It is not currently
wired into `composition.py` (only `BestOfNSearch` is), which is why it is Major and not Critical.

## 3.4 Context Engine, TaintGate & FrozenRunState — **PASS**

- **Seed-only Layer 6 is structurally enforced.** `assembler.py:12` — "`retrieval_seed` is
  accepted **only** by `__init__`, and no public method takes a ..."; `:144` the constructor
  parameter is `retrieval_seed: tuple[RetrievalHit, ...] = ()  # Layer 6: set once, frozen`;
  `:320` renders it once. There is no post-construction write surface. ADR-0021 honored.
- **Cache-stability instrumentation is unusually good.** `AssembledPrompt` carries *two* digests
  (`prefix_digest`, `stable_prefix_digest`) with an in-code comment explaining that conflating
  them hides the regression signal: a moving `prefix_digest` may be a deliberate layer-7 update,
  whereas a moving `stable_prefix_digest` is the actual defect. This is the right instrument.
- **T7 envelope placement is correct** (see §1.3.3). `result_message()` at `assembler.py:66` is
  the single place a `ToolResult` becomes a model-visible `ToolResultBlock`, and `wrap_untrusted`
  is idempotent so double-wrapping is safe.
- **Taint is monotonic and survives freeze/thaw.** `engine.py:106` `mark_tainted` is documented as
  "Freeze/thaw must not be an untaint primitive"; `FrozenRunState.tainted` (`control.py:120`)
  carries the bit. `record_outcome` (`:213`) sets taint from untrusted results.
- **Taint blocks mutations at every autonomy level.** `engine.py:156` — `apply_edit`/`write_file`
  from a tainted run ⇒ `requires_human=True`. `run_command` is deliberately excluded, guarded by
  `assert _TAINT_BLOCKED_TOOLS <= MUTATION_TOOLS`, so gates can still run `git`. See **m-9**.
- **Grants-absent freeze.** `domain/control.py:67-87` states the invariant and names its enforcing
  contract test. Verified: no field is `Grant`-typed or transitively contains one.

## 3.5 Podman Perimeter & Egress — **PASS in code, UNGATED in CI**

- `sandbox/container.py` builds `podman run` argv with `--network=none` for both `network="none"`
  and `network="restricted"`; under `restricted` the only egress is a unix-socket HTTP `CONNECT`
  proxy with a hostname allowlist, forwarded to loopback, with `HTTP(S)_PROXY` and `no_proxy=""`
  injected. Direct outbound is impossible because there is no host network stack. Correct design.
- Host credentials are excluded: the container gets no inherited environment, only explicit
  `sandbox.env_passthrough` keys; `SECRET_MATERIALIZE_NAMES` filters `.env`, `.netrc`, `.npmrc`
  and friends out of workspace materialization; home is not mounted.
- **Autonomy unlock is enforced bidirectionally** in `domain/config.py:485-498`:
  `subprocess` + `autonomous|scheduled` is refused, *and* `autonomous|scheduled` requires
  `runtime ∈ {container, gvisor}`. Both directions present — a detail many implementations miss.
- **Gap M-2:** no Podman job exists in `.github/workflows/ci.yml`. The 11 `@pytest.mark.podman`
  tests pass on this host but are unenforced on any runner. ADR-0006 makes the sandbox *the*
  perimeter; an unenforced perimeter regresses silently.

---

# Section 4 — Codebase Drift & Defect Log

Severity: **Critical** = blocks tag or contradicts a claimed green signal · **Major** = blocks
default-on capability or published empirics · **Minor** = quality/DRY/completeness.

---

## CRITICAL

### C-1 — `FTS5Indexer.neighbors` silently fabricates empty results for real goals *(NEW — not in either prior report)*

| | |
| :--- | :--- |
| **Where** | `src/sagiha/adapters/indexer/fts5.py:199-234` (the `except sqlite3.OperationalError: return []` at ~`:217`); consumed by `src/sagiha/composition.py:129-131` `build_retrieval_seed` |
| **What** | `build_retrieval_seed` passes the raw task goal into `chunks MATCH ?`. FTS5 parses that string as **query syntax**, not as literal text. `(`, `)`, `'`, `-`, `:` and bare `AND`/`OR`/`NOT` are operators or syntax errors. The resulting `sqlite3.OperationalError` is caught and converted to `[]`. |
| **Evidence** (reproduced at HEAD, index containing `def greet(name)`) | `neighbors("greet")` → **1 hit**. `neighbors("Fix the bug in greet() so it returns a name")` → **0 hits**; underlying error `fts5: syntax error near ")"`. `neighbors("handle user's input")` → **0 hits**; `fts5: syntax error near "'"`. `neighbors("add auth - use JWT")` → **0 hits**; `no such column: use`. |
| **Why it must be fixed** | Three compounding harms. (1) **Functional:** Layer-6 seed retrieval — the entire S6.1 deliverable — is inert for realistic goals. (2) **Honesty (H5 class):** the failure is indistinguishable from a true "no matches". This is the exact anti-pattern v2-S1 was chartered to eliminate: a number that looks measured but was never computed. (3) **Measurement poisoning:** the M-1 retrieval-on/off ablation, when it is eventually run, would produce a correct-looking *negative* result caused by a query bug rather than by retrieval's value — and that negative would be published to `docs/rationale/benchmarks/`. Fixing M-1 before C-1 would actively manufacture a false finding. |
| **How to fix** | 1. **Escape the query.** Add a `_fts_query(text: str) -> str` helper in `fts5.py` that tokenizes on `\w+`, drops tokens shorter than 2 chars and the bare operators `AND OR NOT NEAR`, wraps each surviving token in double quotes, and joins with `OR` (for recall-oriented seeding). Route both `neighbors` and `find_symbols` through it. 2. **Stop swallowing.** Narrow the handler to the one legitimate case (`"no such table"` on a cold DB) and let every other `OperationalError` propagate — or, at minimum, `logger.warning` it and return a sentinel the caller can distinguish from a true empty. A silent `except` in a retrieval path is a lying instrument. 3. **Regression-test it.** In `tests/contracts/test_indexer_conformance.py`, assert that a goal-shaped query containing `()`, `'`, `-` and `:` returns the same hits as its bare-keyword equivalent. |
| **Files** | `src/sagiha/adapters/indexer/fts5.py`, `src/sagiha/composition.py`, `tests/contracts/test_indexer_conformance.py` |

### C-R1 — `Indexer.neighbors` Protocol/adapter divergence → 3 pyright errors *(confirmed; both prior reports correct)*

| | |
| :--- | :--- |
| **Where** | Port `src/sagiha/ports/indexer.py:22` `async def neighbors(self, path: str, limit: int = 20)` · Adapter `src/sagiha/adapters/indexer/fts5.py:199` `async def neighbors(self, query: str, limit: int = 20)` |
| **Pyright output (verbatim)** | `service.py:52:44 - error: "_db_path" is protected … (reportPrivateUsage)` · `service.py:78:44 - error: "_db_path" is protected …` · `composition.py:158:12 - error: Type "tuple[FTS5Indexer, TreeSitterCodeGraph, IndexService]" is not assignable … "FTS5Indexer" is incompatible with protocol "Indexer" … "neighbors" is an incompatible type` |
| **Why bad** | PEP 544 makes parameter *names* part of the structural contract (keyword calls must work). The port promises path-scoped neighbor expansion; the adapter delivers full-text search. A caller reading `ports/indexer.py` is misled about the semantics, and `composition.py` cannot type-check. |
| **How to fix** | Prefer **option B — split the APIs**, because the two operations are genuinely different and the codebase will want both: rename the FTS operation to `search(self, query: str, limit: int = 20) -> list[RetrievalHit]` on both Protocol and adapter, and *keep* `neighbors(self, path: str, ...)` on the Protocol as graph-expansion (implemented against `TreeSitterCodeGraph.impacted_by`, or removed from the port until an adapter exists — see ADR-0019's port-rent rule). Update `composition.build_retrieval_seed` to call `indexer.search(...)`. Option A (rename the port parameter to `query`) is a one-line fix that clears pyright but bakes the semantic lie into the contract; take it only if S7 is imminent. |
| **Prerequisite** | Land **C-3** first so this class of drift cannot recur. |
| **Files** | `src/sagiha/ports/indexer.py`, `src/sagiha/adapters/indexer/fts5.py`, `src/sagiha/composition.py`, `tests/contracts/test_indexer_conformance.py` |

### C-2 — `docs/STATUS.md` asserts green signals that are currently red

| | |
| :--- | :--- |
| **Where** | `docs/STATUS.md:113-123` "Frozen Regression Signals" |
| **What** | STATUS claims **"Type check — 0 errors, strict"** (actual: 3) and **"Lint — clean"** (actual: `ruff check .` 34 errors, `ruff format --check .` 17 files). STATUS also reports **"Tests — 321 passed (310 without Podman + 11 podman)"**; the arithmetic is wrong and the total is stale — measured is **321 without Podman + 11 Podman = 332**. |
| **Why bad** | STATUS is the declared SSOT. A SSOT that reports a typecheck result from memory rather than from a run is the H1 failure mode applied to the project's own dashboard. It is also what let C-R1 sit undetected: pytest is green, so nobody re-ran pyright. |
| **How to fix** | Correct the table **only after** P0 is green, and add the missing rows so the table covers every CI gate: docs budget, link integrity, event catalog. Then wire a `make verify` / `scripts/verify.sh` that runs all seven and is the *only* sanctioned way to update that table. |

### C-3 — No contract test asserts adapter→Protocol assignability *(NEW — root cause of C-R1)*

| | |
| :--- | :--- |
| **Where** | `tests/contracts/test_port_shape.py` (enumerates Protocols; never binds adapters) · `tests/contracts/test_indexer_conformance.py` (exercises `FTS5Indexer` concretely) |
| **Why bad** | The hexagon's central claim — adapters are substitutable behind ports — has no automated enforcement. A signature divergence produces a **green pytest run**. Detection depends entirely on a human remembering to run pyright, which C-2 proves does not happen reliably. |
| **How to fix** | Add `tests/contracts/test_adapter_conformance.py` with an explicit adapter↔port registry and a compile-time assertion per pair: <br>`def _assert_indexer(x: Indexer) -> None: ...` then `_assert_indexer(FTS5Indexer(db_path=":memory:"))`. Pyright checks the call site; pytest checks it constructs. Cover at minimum `FTS5Indexer→Indexer`, `TreeSitterCodeGraph→CodeGraph`, `LocalWorkspace→Workspace`, `ContainerSandbox→Workspace`, `BestOfNSearch→CandidateSearch`, `SQLiteTrajectoryStore→TrajectoryStore`, `DefaultPolicyEngine→PolicyEngine`, `DefaultResourceGovernor→ResourceGovernor`. |

### C-3d — 106 dead relative documentation links; `check_links.py` exits 1 *(NEW — neither prior report ran this gate)*

| | |
| :--- | :--- |
| **Evidence** | `python3 scripts/check_links.py` → exit 1, `106 dead relative link(s) across 120 files` |
| **Representative breakages** | `docs/STATUS.md → ../refactor_sagiha_v2_guidelines.md` (the SSOT cannot reach the guidelines it cites) · `docs/08-decisions/0024-…md → ../../refactor_sagiha_v2_guidelines.md` (an **ADR** with a broken reference) · four separate files → `rationale/reviews/2026-07-29-foundation-review.md` (a document that no longer exists) · the whole `docs/frontend/` tree uses absolute `file:///home/rock_dev/...` URLs |
| **Why bad** | This is a **v2-S0 exit gate** and it is enforced in CI (`ci.yml:71`). Its own error text says: *"A link to a file that a reorganisation moved is how docs/STATUS.md went missing for four inbound references."* The S0 docs migration created exactly the breakage the gate exists to prevent, and the gate was never re-run. Agents retrieving docs follow these links and get nothing. |
| **How to fix** | Three mechanical batches: (1) repoint the ~5 references to `refactor_sagiha_v2_guidelines.md` at `docs/implementation/refactor_sagiha_v2_guidelines.md`; (2) delete or redirect the ~4 references to the deleted `2026-07-29-foundation-review.md`; (3) convert every `file:///home/rock_dev/...` absolute URL in `docs/frontend/` and `docs/rationale/done/` to a repo-relative path — machine-specific absolute paths are unresolvable for every other reader anyway. Then re-run to zero. |

### C-2b — Normative docs budget exceeded *(confirmed; both prior reports correct)*

| | |
| :--- | :--- |
| **Evidence** | exit 1 — `normative word count 15,183 exceeds ceiling 15,000 (over by 183)`; 15 files tagged `status: normative` |
| **Largest normative contributors** | `02-architecture/context-and-cache-engineering.md` 762 · `02-architecture/car-model.md` 733 · `implementation/contracts-to-code.md` 709 · `02-architecture/microkernel-and-bus.md` 423 |
| **How to fix** | Demote ≥183 words rather than deleting content: `implementation/contracts-to-code.md` (709 w) is implementation guidance, not a contract — retagging it `status: rationale` + `retrieval: excluded` clears the overshoot with margin in one edit. Confirm exit 0 before merge. |
| **Related — m-12** | 8 files carry **no `status:` tag** and are therefore invisible to the budget, including `implementation/refactor_sagiha_v2_guidelines.md` and `implementation/sprints_tasks_order_deps_plan.md` — both treated as normative by the audit brief. Untagged normative docs are a budget-evasion loophole. Either tag them (and absorb the words) or have `docs_budget.py` **fail** on untagged files instead of merely listing them. |

---

## MAJOR

### M-1 — No pinned benchmark suite; noise floor unpopulated *(confirmed)*
`benchmarks/definitions/` **does not exist** at all (verified: `ls` fails). `docs/rationale/benchmarks/noise-floor.md` opens with *"Status: template, not yet populated … The numbers below are placeholders and must not be cited"* — a commendably honest artifact. Harvest yielded 0/23 (`s4-harvest-findings.md`). **Consequence:** BoN-vs-single-shot, retrieval on/off, and init on/off are all unfalsifiable, which is why `search.enabled=false` and `retrieval.enabled=false` are correct today. **Fix:** harvest or import a ≥30-task suite with pinned base commits (SWE-bench Lite subset is the pragmatic source), commit `benchmarks/definitions/s0-core.json`, run `sagiha bench --aa`, replace the template, unguard the `bench-aa` CI job. **Sequencing: fix C-1 first** or the retrieval ablation measures the query bug.

### M-2 — Podman perimeter not gated in CI *(confirmed)*
No podman job in `.github/workflows/ci.yml`; only the proposal at `docs/implementation/ci-podman-perimeter.md`. The 11 perimeter tests pass locally and are enforced nowhere. **Fix:** land the proposed job (human-authored, TCB-adjacent) running workspace conformance parametrized over `LocalWorkspace`/`ContainerSandbox` plus the egress canary on a Podman-capable runner.

### M-3 — Dual symbol-path namespaces between indexer and graph *(confirmed)*
`adapters/indexer/chunking.py:24-28` `_module_name` takes the **last path segment** (`pkg/util.py → "util"`); `adapters/code_graph/treesitter.py:38-42` `_module_name` takes the **full dotted path** (`pkg/util.py → "pkg.util"`). The same symbol is `util.greet` in FTS `symbol_path` and `pkg.util.greet` in graph `defines` edges. **Why bad:** cross-referencing a retrieval hit to a graph node silently fails; impact analysis and call resolution disagree; DRY violation with two divergent definitions of one concept. **Fix:** extract one shared `module_name(path) -> str` (prefer the full dotted form) into a single module — see m-3's `walk.py` — import it in both, and add a conformance assertion that every chunk `symbol_path` prefix matches a graph `defines` name for the same file.

### M-4 — `max_chunk_tokens` is a dead configuration knob *(confirmed)*
`domain/config.py:268` exposes `max_chunk_tokens: int = 1024`; `composition.py:157` threads it into `IndexService`; `IndexService` passes it to `analyze_python_tree`, which does **`del max_chunk_tokens  # reserved for oversized-chunk splitting`** (`chunking.py:129`). Separately, `fts5.py:68` hardcodes `1024` in `_index_python`, so the direct `reindex_file` path ignores the config entirely. **Why bad:** config honesty is instrument honesty. An operator who lowers this to bound prompt cost gets no behavior change and no warning. **Fix:** either implement statement-boundary splitting when a node exceeds the budget, or **delete the field**, remove the threading, and document the fixed 1024 policy until ablations justify tuning. Do not leave it accepted-and-discarded.

### M-5 — Chunk text carries no path/symbol/signature prefix *(confirmed)*
`chunking.py:60-95` sets `Chunk.text = _node_text(source, node)` — the raw AST span — and `fts5.py` stores only `(path, chunk)`. The indexing spec requires a `path / symbol_path / signature` envelope. **Why bad:** a retrieved chunk arrives in Layer 6 without standalone context, and BM25 cannot match on the file path or dotted symbol name the goal usually mentions. A recall@10 miss will be misattributed to "lexical retrieval is weak" (triggering ADR-0014's dense tier prematurely) when the real cause is chunking. **Fix:** prepend `f"{path}\n{symbol_path}\n{signature}\n---\n"` to the indexed body; keep the raw span available separately if a consumer needs clean bytes. Update conformance assertions.

### M-6 — Plan/STATUS SSOT drift *(confirmed)*
`docs/implementation/development_plan_v2.md` holds **18 unchecked `[ ]`** vs **17 checked `[x]`** epics while STATUS marks S0–S5 closed. **Fix:** tick the delivered boxes. *(Both prior reports were right to note this is markdown maintenance backlog rather than non-delivery — git history and code confirm delivery. But an SSOT that contradicts itself is exactly what S0 existed to end.)*

### M-7 — "21 → 15 ports" prose survives in the normative plan *(confirmed)*
`development_plan_v2.md:19` and `:221` both still state 15. ADR-0019 explicitly corrects this (*"That number is wrong"*), and the code has 17. **Fix:** replace both occurrences with "17 (ADR-0019 as restated, plus ADR-0024)". `next_gen_architecture_specs.md:46` and `codebase_delta_refactor.md:30` may keep the old number — they are `status: historical`.

### M-8 — `adapters/search/sequential.py` is a live-exported lying stub *(upgraded from prior reports' Minor)*
Returns fabricated `candidate-<uuid>` IDs for worktrees that do not exist, `None` from `evaluate()`, and `branch_ids[0]` from `select()`. Exported via `adapters/search/__init__.py`. Under the v2-S1 H3 doctrine this is a false-success payload, not dead code. Not currently wired in `composition.py` (only `BestOfNSearch` is), which caps severity at Major. **Fix:** delete the module and its export (`BestOfNSearch(n=1)` already covers the sequential case), or reduce it to three `raise NotImplementedError("use BestOfNSearch with n_candidates=1")` bodies. Do not leave methods that return plausible fabrications.

---

## MINOR

| ID | Defect | Evidence | Fix |
| :--- | :--- | :--- | :--- |
| **m-1** | `sagiha init` never passes a code graph | `cli.py:648` — `generate_agents_md(root, graph=None, force=force)`, while `generate.py:120` has a working `## Code graph` renderer that is therefore unreachable | On `--reindex`, or when `.sagiha/code_graph.db` exists, construct/load `TreeSitterCodeGraph` and pass it |
| **m-2** | Init module discovery mislabels and under-collects | `generate.py:47-57` — `rglob("*.py")` **does** find `src/pkg/__init__.py`, but names it `src.sagiha.domain` (leading `src.`), and non-package modules in subdirectories are skipped entirely (`elif "/" not in rel`) | Strip a leading `src/` before dotting; collect all non-`__init__` modules under discovered package roots. *(Note: prior report B's claim that discovery "only [finds] top-level `*.py` and `*/__init__.py`" is imprecise — packages at any depth are found.)* |
| **m-3** | `SKIP_DIRS` duplicated **4×** | Byte-identical frozensets in `indexer/fts5.py:22`, `indexer/service.py:18`, `code_graph/treesitter.py`, `outer_loop/init/generate.py:12` | One `sagiha/adapters/indexer/walk.py` exporting `SKIP_DIRS`, `TEXT_EXTENSIONS`, and `module_name()` (also fixes **M-3**); import everywhere |
| **m-4** | `IndexService` reaches into `FTS5Indexer._db_path` | `service.py:52` and `:78` open raw `sqlite3.connect(self._indexer._db_path)` and issue `DELETE`/`INSERT` against the `chunks`/`symbols` schema — this is the source of 2 of the 3 pyright errors | Add public write methods to `FTS5Indexer` — `replace_file_chunks(path, chunks, symbols)`, `clear_path(path)` — mirroring the existing public `chunk_count()`. A `db_path` property would silence pyright while leaving `IndexService` coupled to the FTS schema; prefer the real encapsulation fix |
| **m-5** | Full reindex never prunes deleted files | `service.py:99-105` `_reindex_all` updates only files it sees; no wipe, no orphan sweep | Track seen paths and delete rows for unseen ones, or truncate before a full `rebuild_from_root` |
| **m-7** | Export CLI builds schemas from static `BUILTIN_SCHEMAS` | `cli.py:572-588` uses `BUILTIN_SCHEMAS` + `TOOL_DESCRIPTIONS` only, while `builtins.py:245` shows the registry composes a *superset* at runtime when code-intel tools are enabled | Reconstruct schemas from a registry snapshot recorded on the run; fall back to enabled-config reconstruction. Otherwise SFT/DPO samples from retrieval-enabled runs carry a tool list the run did not actually have |
| **m-8** | S5 credential story narrower than plan wording | Env scrub + `SECRET_MATERIALIZE_NAMES` exclusion are implemented; "per-grant short-lived secret injection" is not | Amend the plan/STATUS wording to what exists, or schedule injection for S7. Do not leave a security over-promise in a normative doc |
| **m-9** | TaintGate does not block `run_command` | `engine.py:20` `_TAINT_BLOCKED_TOOLS = {apply_edit, write_file}`, guarded by `assert … <= MUTATION_TOOLS` | **Deliberate and defensible** (gates must run `git` under taint) but under-documented. Add the rationale to `security-and-threat-model.md#t7`, and consider: tainted + `autonomy=autonomous` ⇒ deny `run_command` unless `classify_command` returns `PURE`. Under `runtime=container` the perimeter is the real boundary |
| **m-11** | MCP `list_tools()` returns `[]` rather than raising | `mcp/driver.py` — documented in-code as a truthful null for zero connected servers | **Accept as-is.** The in-code justification is sound and distinguishes it from `invoke_tool`'s fabrication |
| **m-12** | 8 docs carry no `status:` tag | Listed by `docs_budget.py`; includes `refactor_sagiha_v2_guidelines.md`, `sprints_tasks_order_deps_plan.md` | Tag every file; make `docs_budget.py` exit non-zero on untagged files (see C-2b) |
| **m-13** | Empty CAR strata: `src/sagiha/runtime/` and `src/sagiha/aoi/` contain only `__init__.py` | `ls` verified | RUNTIME is a named stratum in `car-model.md` but all effects live in `adapters/`. Either document that RUNTIME is realized by `adapters/{sandbox,workspace}/`, or remove the empty packages. `aoi/` is correctly out of scope but should carry a one-line docstring saying so |
| **m-14** | Lint config scope mismatch between pyright and ruff | `pyproject.toml:70` scopes pyright to `include = ["src/sagiha"]` to exclude vendored trees; `ci.yml:41` runs `ruff check .` unscoped, so **16 of the 34 errors come from `aether_examples/`** and 3 from `keep_alive.py` | Add the vendored/example trees to ruff's `extend-exclude`, matching the pyright rationale already written at `pyproject.toml:63-69`. This alone cuts CI ruff failures by more than half and is honest — those trees are not this project's code |

---

## NOT DEFECTS — do not "fix" these into overclaims

| Item | Why acceptable |
| :--- | :--- |
| S4/S6 empirical halves unpublished | Amended honest-negative exit gates; STATUS reports this accurately |
| `coverage_not_decreased=None` | No `Toolchain` adapter exists — `None` is the true answer, and `None` never passes |
| `search.enabled=false`, `retrieval.enabled=false` | Correct fail-safe defaults under the honest-negative doctrine |
| MCP / OTel stubs raising `NotImplementedError` | Loud stubs, S7 scope, correct per H3 |
| Dense retrieval absent | ADR-0014 trigger has not fired |
| `_parse_symbol_ref` in `treesitter.py` | **Prior report B's m-10 is wrong.** It is covered by `tests/unit/test_code_graph_scaffolding.py:80` and carries an explicit `# pyright: ignore[reportUnusedFunction]`. Not dead code |
| Conductor / Story-DAG absent | Explicitly out of scope until S7 / C0 |

---

# Section 5 — MVP Status vs Deferred Roadmap

## 5.1 What is production-capable today at `v2-S6`

An honest, gate-verified, single-task autonomous coding loop:

- **Execution** — DMARTIC inner loop (`agency/run_loop.py`) with stuck-signature detection, max-steps
  and `end_turn` termination, and a **reachable** budget break that parks the run resumable.
- **Security** — CAR grants through a single dispatch choke point; unconditional point-of-effect
  grant verification; PURE/DESTRUCTIVE per-invocation classification; monotonic taint with
  human-required mutations; rootless Podman perimeter with allowlisted CONNECT-proxy egress and
  host-credential exclusion; `autonomous` autonomy unlocked only inside a container.
- **Context** — layered assembly with seed-only Layer 6, exchange-granular token-budgeted
  compaction, anchored artifacts surviving compaction, dual cache-stability digests.
- **Durability** — `FrozenRunState` freeze/thaw surviving `kill -9`; cassette record/replay;
  SQLite trajectory store with full `Message` persistence.
- **Evaluation** — real base-commit diff gates; E0 with exact McNemar, seeded bootstrap CI, and
  Holm correction; ranking-only S-0/S-1 scoring that can never admit.
- **Pipelines** — `sagiha export --format sft|dpo` with fail-closed eligibility
  (`admitted ∧ ¬tainted ∧ within-budget ∧ replay-verified`), secret redaction, license gating.
- **CLI** — `run`, `replay`, `harvest`, `bench`, `export`, `init`.
- **Available but correctly OFF** — Best-of-N search, FTS5 retrieval, code graph.

## 5.2 Honest caveats on that MVP

- Retrieval is off *and* **C-1 means it would not work if switched on**.
- No pinned benchmark suite exists, so **no performance claim about this MVP is defensible**.
- The container perimeter is untested on any CI runner (**M-2**).
- The default interactive CLI path uses `subprocess`, not the container — isolation claims apply
  to `runtime=container` only.

## 5.3 Explicitly deferred (correctly absent — do not penalize)

| Horizon | Contents | Gate/trigger |
| :--- | :--- | :--- |
| **v2-S7** | Story-DAG workflow runner (`agency/workflow/`), MCP client driver, streaming/steerable TUI, OTel exporter | Per-block gates in `next_gen_architecture_specs.md §5` |
| **Conductor C0+** | `sagiha_conductor` package, MissionSpec/MissionState, FleetGovernor, KnowledgeEngine, SkillCompiler, Tier-4 promotion | `agi_evolution_path.md §7`; C0 hard-depends on H1/H2 (both now satisfied) |
| **Deferred by ADR** | Dense vector retrieval (ADR-0014), AOI acting mode, RHI Tier C (ADR-0022), A2A remote pilots, performance sidecars, warm LSP | Each behind a measured trigger |

## 5.4 Scope-creep check — **clean**

I found **no** S7 or Conductor code polluting the S6 execution loop. `agency/` contains only
`run_loop.py`, `freeze.py`, and `context/` — no `workflow/`. `adapters/mcp/` and
`adapters/telemetry/otel.py` exist but raise loudly and are not wired into `composition.py`.
`aoi/` and `runtime/` are empty packages (**m-13**). Dimension 7 passes.

---

# Section 6 — Adjudication of the Two Prior Reports

Both reports were substantially correct on architecture and both correctly self-flagged several
of their own errors. Below, each disputed claim is resolved against the live tree.

## 6.1 `sprints_0-6_review_001.md`

| Claim | Verdict | Resolution |
| :--- | :--- | :--- |
| "332 passed out of 332 collected" | ✅ **TRUE** — and its own "double-check" note retracting this was **wrong** | With Podman 5.8.4 present, `pytest -q` = **332 passed, 0 skipped**. 321 is the `-m "not podman"` subset |
| "Ruff reports 30 errors" | ✅ **Essentially TRUE** at CI scope (`ruff check .` = **34**); its self-correction to "14" was the *narrower* `src/sagiha tests` scope | Both numbers are real; they measure different scopes. CI uses `.` |
| Pyright: 3 errors | ✅ **TRUE** | Confirmed verbatim |
| "…3 type errors in `fts5.py:199`, `service.py:52`, `composition.py:158`" | ⚠️ **PARTIALLY FALSE** (self-flagged, correctly) | No diagnostic is emitted *in* `fts5.py`; `:199` is the signature source, not an error locus |
| `outer_loop/export/exporter.py` | ❌ **FALSE** (self-flagged) | No such file. Modules are `eligibility.py`, `sft.py`, `dpo.py`, `redaction.py`, `license.py`, `schema.py` |
| `outer_loop/init/generator.py` | ❌ **FALSE** (self-flagged) | File is `generate.py`. *(The audit brief repeats this error.)* |
| `IndexService` uses `self._fts5._db_path` | ❌ **FALSE** (self-flagged) | Actual attribute is `self._indexer._db_path`. The encapsulation defect is real; the snippet is wrong |
| `PolicyEngine.authorize()` at L48 | ❌ **FALSE** | It is at `kernel/policy/engine.py:138` |
| Defect 3.1 — registry should catch `NotImplementedError` | ❌ **FALSE / already done** | `dispatch.py:109-119` already catches bare `Exception` and returns `ToolResult(is_error=True)`. No action needed |
| Defect 5.1 — path-validation duplication between `cli.py` and `composition.py` | ❌ **NOT SUBSTANTIATED** (self-flagged) | I found shared default path strings and `composition.py:145-147` creating `.sagiha/`, but no parallel validator pair. Its own caution against putting filesystem I/O in `domain/config.py` is correct — that would violate the domain-purity contract |
| "S0 Complete / 7 of 7 sprints 100% complete" | ❌ **OVERSTATED** (self-flagged) | S0's own budget and link gates are red |
| All "/100" scores, "Production-Ready" | ❌ **NOT REPRODUCIBLE** (self-flagged) | Subjective; not repeated in this audit |

## 6.2 `sprints_0-6_review_001_B.md`

| Claim | Verdict | Resolution |
| :--- | :--- | :--- |
| "321 passed / 11 skipped" | ⚠️ **HOST-DEPENDENT** | Correct on a Podman-less host. On this host: **332 passed, 0 skipped**. Its implicit correction of report 001 was itself wrong |
| C-R1 pyright 3 errors + locations | ✅ **TRUE** — most precise account of the two | Confirmed |
| C-R2 docs budget 15,183 | ✅ **TRUE** | Confirmed, exit 1 |
| M1 no suite / template noise floor | ✅ **TRUE** | `benchmarks/definitions/` does not exist |
| M2 Podman not in CI | ✅ **TRUE** | Confirmed |
| M3 `neighbors` Protocol break | ✅ **TRUE** | Confirmed; its option-A/option-B framing is the right one |
| M4 dual symbol-path namespaces | ✅ **TRUE** | Confirmed verbatim in code |
| M5 `max_chunk_tokens` dead | ✅ **TRUE** | Confirmed — and *worse*: `fts5.py:68` also hardcodes 1024 on the direct path |
| M6 plan/STATUS drift, "15 ports" prose | ✅ **TRUE** | 18 `[ ]` / 17 `[x]`; prose at `development_plan_v2.md:19,221` |
| M7 no chunk prefix envelope | ✅ **TRUE** | `Chunk.text` is the raw AST span |
| m1 `init` passes `graph=None` | ✅ **TRUE** | `cli.py:648` |
| m2 init discovery misses `src/*.py` | ⚠️ **IMPRECISE** | `rglob` finds packages at any depth; real defects are the `src.` prefix and skipped non-package submodules |
| m3 `SKIP_DIRS` ×4 | ✅ **TRUE** | All four confirmed |
| m4 `IndexService` private access | ✅ **TRUE** | `service.py:52,78` |
| m5 no orphan prune | ✅ **TRUE** | Confirmed |
| m6 dead search shell | ✅ **TRUE but UNDER-SEVERE** | It returns fabricated values and is exported — an H3 lying stub. Upgraded to Major (**M-8**) |
| m7 export static schemas | ✅ **TRUE** | `cli.py:572-588` |
| m8 per-grant secrets absent | ✅ **TRUE** | Env scrub + path exclusion exist; injection does not |
| m9 taint allows `run_command` | ✅ **TRUE and deliberate** | Asserted in code; needs a doc amendment |
| m10 `_parse_symbol_ref` unused/dead | ❌ **FALSE** | Tested at `tests/unit/test_code_graph_scaffolding.py:80`; carries an explicit pyright ignore |
| m11 MCP `list_tools` returns `[]` | ✅ **TRUE**, and **accept as-is** | In-code justification is sound |
| "Regression snapshot: pyright 3 errors, budget 15,183" | ✅ **TRUE** | Most accurate snapshot of the two reports |
| Gate verdict CONDITIONAL PASS | ✅ **CONCUR** | But its P0 list is incomplete — it omits C-1, C-3, C-3d, ruff, and format |

## 6.3 What **both** reports missed

1. **C-1** — silent FTS5 query failure (Critical; the single most consequential defect in the tree).
2. **C-3d** — 106 dead links; `check_links.py` is a CI gate and neither report ran it.
3. **Ruff and format are CI gates and both fail** — `ci.yml:41-42` runs `ruff check .` and
   `ruff format --check .`. Report 001 counted ruff but did not connect it to CI; report B omitted
   it from its P0 entirely.
4. **C-3** — the absent adapter→Protocol conformance test, i.e. the *root cause* of C-R1.
5. **The true CI failure count is 5/7, not 2/7.**
6. **STATUS's test arithmetic is wrong** (`310 + 11 = 321` should be `321 + 11 = 332`).
7. **m-14** — the ruff/pyright scope mismatch that makes CI red on vendored example trees.

---

# Section 7 — Actionable Remediation Plan

## P0 — Before any release tag *(unblocks CONDITIONAL → PASS)*

| # | Action | Files | Verify |
| :- | :--- | :--- | :--- |
| 0.1 | **Fix C-1**: add `_fts_query()` escaping; narrow the bare `except sqlite3.OperationalError` to the cold-DB case and log/propagate otherwise; add a goal-shaped-query regression test | `adapters/indexer/fts5.py`, `tests/contracts/test_indexer_conformance.py` | New test asserts `neighbors("Fix greet() in pkg/util.py")` returns the same hits as `neighbors("greet")` |
| 0.2 | **Fix C-3** *(before 0.3)*: add `tests/contracts/test_adapter_conformance.py` with typed assignability assertions for all 8 adapter↔port pairs | new test file | `pyright` flags any future Protocol/impl drift at the assertion site |
| 0.3 | **Fix C-R1**: split `Indexer.search(query)` from `Indexer.neighbors(path)` (option B); update `build_retrieval_seed` | `ports/indexer.py`, `adapters/indexer/fts5.py`, `composition.py` | — |
| 0.4 | **Fix m-4**: add `replace_file_chunks()` / `clear_path()` to `FTS5Indexer`; delete both `_db_path` reach-ins | `adapters/indexer/{fts5,service}.py` | — |
| 0.5 | `uv run pyright src/sagiha` | — | **0 errors** |
| 0.6 | **Fix m-14** then lint: add vendored/example trees to ruff `extend-exclude`; `uv run ruff check --fix` ; `uv run ruff format` | `pyproject.toml`, `src/sagiha/cli.py:89`, tests | `ruff check .` **0**; `ruff format --check .` **0** |
| 0.7 | **Fix C-2b**: demote `implementation/contracts-to-code.md` to `status: rationale` + `retrieval: excluded`; tag the 8 untagged files | `docs/**` | `docs_budget.py --max 15000` **exit 0** |
| 0.8 | **Fix C-3d**: repair the 106 dead links in the three batches described above | `docs/**` | `check_links.py` **exit 0** |
| 0.9 | **Fix C-2 last**: update the STATUS regression table from a real run; add budget/links/catalog rows; add `scripts/verify.sh` running all 7 gates | `docs/STATUS.md`, `scripts/verify.sh` | All 7 green, STATUS matches |

**Definition of done for P0:** `scripts/verify.sh` exits 0 on all seven gates, and every number in
`docs/STATUS.md` was copied from that run.

## P1 — Before flipping any default to ON or publishing any empirical delta

| # | Action | Blocks |
| :- | :--- | :--- |
| 1.1 | **M-1**: commit a ≥30-task pinned suite at `benchmarks/definitions/s0-core.json`; run `bench --aa`; replace the `noise-floor.md` template; unguard the `bench-aa` CI job | Every empirical claim |
| 1.2 | **M-3 + m-3**: create `adapters/indexer/walk.py` with one `SKIP_DIRS`, `TEXT_EXTENSIONS`, and `module_name()`; import in all four call sites; assert chunk `symbol_path` prefixes match graph `defines` names | `retrieval.enabled=true` |
| 1.3 | **M-5**: prepend the `path/symbol_path/signature` envelope to indexed chunk bodies | Trustworthy recall@10 |
| 1.4 | **M-4**: implement statement-boundary splitting **or** delete `max_chunk_tokens` and document the fixed policy | Config honesty |
| 1.5 | **M-2**: land the Podman perimeter CI job | `autonomous` security claim |
| 1.6 | Run the three ablations — BoN vs single-shot, retrieval on/off, init on/off — and publish or shelve each honestly. **Must follow 0.1**, or the retrieval ablation measures C-1 | Default-on |

## P2 — Quality, DRY, completeness

`M-8` (delete/raise the sequential stub) · `M-6` (tick plan checkboxes) · `M-7` (fix "15 ports"
prose) · `m-1` (init graph wiring) · `m-2` (init discovery naming) · `m-5` (orphan prune) ·
`m-7` (export registry snapshot schemas) · `m-8` (amend credential wording) · `m-9` (document the
`run_command` taint tradeoff in the threat model) · `m-12` (fail the budget on untagged docs) ·
`m-13` (document or remove empty `runtime/` and `aoi/` packages).

## P3 — After S7 / behind funding triggers

MCP client, streaming steer TUI, Story-DAG runner, OTel, Conductor C0, dense retrieval tier,
learned scorers/routers.

## Suggested sequencing

```
0.1 ──► 0.2 ──► 0.3 ──► 0.4 ──► 0.5 ─┐
0.6 ─────────────────────────────────┤
0.7 ──► 0.8 ─────────────────────────┴──► 0.9 (STATUS) ──► TAG v0.3.0-v2-S6
                                                              │
                                          ┌───────────────────┴──────────────┐
                                          ▼                                  ▼
                                    P1 (empirics track)              v2-S7 (mechanism track)
```

S7 does not depend on P1 — its prerequisites are mechanism, not measurement — so the two tracks
can proceed in parallel once P0 clears.

---

## Appendix A — Commands to reproduce this audit

```bash
uv run pytest -q                                  # 332 passed
uv run pytest -q -m "not podman"                  # 321 passed, 11 deselected
uv run pyright src/sagiha                         # 3 errors
uv run lint-imports                               # 5 kept, 0 broken
uv run ruff check .                               # 34 errors  (CI scope)
uv run ruff check src/sagiha                      # 1 error
uv run ruff format --check .                      # 17 files
python3 scripts/docs_budget.py --max 15000; echo $?   # 15,183 → exit 1
python3 scripts/check_links.py; echo $?               # 106 dead → exit 1
python3 scripts/gen_event_catalog.py --check; echo $? # in sync → exit 0
grep -rn "(Protocol)" src/sagiha/ports/ | wc -l   # 17
```

Reproduction for **C-1**:

```bash
uv run python - <<'PY'
import asyncio, tempfile, os
from sagiha.adapters.indexer.fts5 import FTS5Indexer
ix = FTS5Indexer(db_path=os.path.join(tempfile.mkdtemp(), "i.db"))
ix.reindex_file("a.py", "def greet(name):\n    return 1\n")
async def m():
    for q in ["greet", "Fix the bug in greet() so it returns a name", "handle user's input"]:
        print(repr(q), "->", len(await ix.neighbors(q, limit=5)), "hits")
asyncio.run(m())
PY
# greet                                        -> 1 hits
# Fix the bug in greet() so it returns a name  -> 0 hits   <-- swallowed fts5 syntax error
# handle user's input                          -> 0 hits   <-- swallowed fts5 syntax error
```

---

*End of `Harness_LLM_orchestrator_project_review.md`. Next engineering step: execute §7 P0 in the
stated order — C-1 first, because every retrieval measurement taken before it is fixed is
invalid. See `concept_review.md` for v3 architectural reflection.*
