---
status: rationale
retrieval: excluded
---
# SPRINT PLANNING — SAGIHA v0.3.0 Re-Baseline

**Status:** normative — this file supersedes the sprint sequence implied by `docs/sprints/` and re-baselines the block plan under the accepted v2 review corpus.
**Basis (audited, cross-referenced):** `docs/reviews/critical_gaps_analysis.md` · `docs/reviews/next_gen_architecture_specs.md` (v2 Spec) · `docs/reviews/codebase_delta_refactor.md` (Delta, findings H1–H4) · `docs/reviews/agi_evolution_path.md` (Conductor) · `docs/reviews/SAGIHA_review_v020.md` · `development_plan_improvements.md` · `docs/implementation/development-plan-and-prompts.md` · `src/sagiha` @ `85b08fb` (127/127 tests, 89.4% cov, pyright 0, 5/5 import contracts).

---

## 0. Where We Are, and What Changed

**Closed and archived:** Sprints 1, 2, 3a, 3a-security, 3b. The loop is real: a live model (Ollama Qwen 2.5 Coder 7B) drives tool calls through the dispatch choke point, path containment holds, cassette replay verifies in CI, and the v0.2.0 review documents empirical single- and multi-step runs. Blocks 2–5 exist as **pre-coding scaffolding only** — module shells, ports, and CLI stubs, not delivered capability.

**The design change (why this file exists).** Before starting Blocks 2/3/4 as previously scoped, the project adopted the v2 review corpus. The destination is unchanged (same four properties, same L0→L4 ladder, same ADRs); the *concept delta* is small but touches everything downstream, which is why the plan re-baselines rather than patches:

1. **Honesty before capability.** The delta audit proved three of four coding gates are hardcoded constants (H1), budget accounting is dead code (H2), scaffolding stubs fabricate success (H3), and `syntax_valid` is a constant (H4). Every Block 2–4 measurement taken over these is uninterpretable. Nothing new ships until the instruments read true.
2. **Port surface 21 → 15**, with three v2 bumps (`ModelProvider`, `ToolRegistry`, `CandidateSearch`) taken *now*, while each has ≤1 stub adapter — the cheapest they will ever be.
3. **Seed-only Layer-6 retrieval, exchange-granular compaction, monotonic taint, `FrozenRunState`, per-invocation PURE effects, scoring bootstrap ladder** — the six normative mechanisms from the Spec + amendments that Blocks 3–5 must be built *on*, not retrofitted *under*.
4. **The Conductor (AGI layer) is explicitly out of scope for this plan** — its C0 phase hard-depends on Sprints 1–2 below and starts only after Sprint 4's re-baselined bench numbers exist.

**Numbering note:** historical sprints 1–3b are closed under the old series. This document restarts numbering as the **v2 series** (Sprint 0 … Sprint 7) per the phase structure below; STATUS.md should reference sprints as `v2-S<n>` to avoid collision.

**Already verified closed (do not re-plan):** D19 event-catalog date churn, D20 `GateReport.admitted` None-handling, D21 `call_id` on results/events, D2 digest-keyed cassettes, D3 `build_kernel` mode honoring, D9 resume, R7 `ShortTermMemoryAdapter` deletion (adapter only — the dead Protocol remains, see v2-S2).

---

# PHASE 1 — Foundational Documentation & Governance

## Sprint v2-S0 — Docs Shrink, SSOT Consolidation, Decision Records

**Objective:** a lean, retrieval-safe documentation foundation that encodes the v2 decisions as normative text *before* code moves, so no sprint below argues with a stale doc.
**Scope:** `docs/` only; zero `src/` changes. **Duration class:** 1 short sprint — this is the cheapest-leverage work in the plan and must not balloon.
**Dependencies:** none. **Risk if skipped:** every later sprint re-litigates decisions against 147k words of partially superseded prose, and the agent maintainer retrieves contradictions.

- [ ] **Epic S0.1 — Normative word budget (≤ 15,000 words)**
  - [ ] Subtask: Inventory word counts per file (`scripts/docs_budget.py`, new — emits per-dir totals; wire as CI check with the 15k ceiling over `status: normative` files only).
  - [ ] Subtask: Demote to `rationale` frontmatter: `reference/` (already rationale — verify), `02-architecture/performance-sidecars.md`, `05-tech-stack/aoi-coprocessors.md`, long-form derivations duplicated by ADRs.
  - [ ] Verification: CI job `docs-budget` green; budget report committed to `docs/STATUS.md`.
- [ ] **Epic S0.2 — `rationale/` migration & retrieval scoping**
  - [ ] Subtask: Create `docs/rationale/`; move `docs/reference/*` and `docs/reviews/todo/*` legacy material (incl. the seven `sprint-fe-*.md` files and old `sprint-2/3/4.md` now sitting in `reviews/todo/`) into it; `docs/reviews/{doing,done}` stay as historical record.
  - [ ] Subtask: Add `retrieval: excluded` frontmatter key honored by the future indexer (Sprint v2-S6) and documented in `docs/README.md`.
  - [ ] Verification: `docs/README.md` sitemap regenerated; zero broken relative links (`scripts/check_links.py`, new; CI-wired).
- [ ] **Epic S0.3 — Fold the v2 corpus into normative SSOT (no duplication)**
  - [ ] Subtask: Amend `02-architecture/context-and-cache-engineering.md` + `prompt-architecture.md`: **seed-only Layer 6 ruling** (one paragraph) and **R9 superseded** by exchange-granular, token-budgeted compaction (`keep_first_exchanges=2`, `keep_last_tokens=24_000`, headroom 20%).
  - [ ] Subtask: Amend `02-architecture/security-and-threat-model.md`: TaintGate v1 (monotonic taint, propagation to summaries/anchored state, mutation-approval rule) as T7.
  - [ ] Subtask: Amend `04-workflows-and-loops/rhi-outer-loop.md`: Tier A/B/C economic re-founding; Tier C (mutation search) dormant behind funding trigger.
  - [ ] Subtask: New `03-contracts-and-models/frozen-run-state.md` (schema pointer into `src/`, grants-absent invariant) and `04-workflows-and-loops/trace-distillation.md` (exporter spec pointer).
  - [ ] Verification: each amended file cites the review doc it implements; `docs/reviews/*` marked `historical` — the normative copy lives in `01–08` only.
- [ ] **Epic S0.4 — Decision records for the re-baseline**
  - [ ] Subtask: ADR-0019 port consolidation 21→15 (deletions, `Advisory` merge, re-promotion conditions); ADR-0020 per-invocation effect classification + TCB allowlist placement; ADR-0021 seed-only retrieval; ADR-0022 RHI economic re-founding; ADR-0023 port-rent rule (zero adapters × 2 blocks ⇒ demotion review).
  - [ ] Verification: `08-decisions/README.md` log updated; every ADR carries reversal conditions.
- [ ] **Epic S0.5 — STATUS re-baseline**
  - [ ] Subtask: Rewrite `docs/STATUS.md`: v2 sprint series, honest capability table (gates listed as **fabricated until v2-S1**, per H1), Blocks 2–5 relabeled "scaffolding present / capability pending".
  - [ ] Verification: STATUS makes no claim the delta audit contradicts.

**Exit gate:** normative word count ≤ 15k in CI; zero broken links; ADRs 0019–0023 merged; STATUS re-baselined. *No code PR merges into `src/` before this gate — one sprint of doc discipline buys every later sprint an uncontested spec.*

---

# PHASE 2 — Refactoring & Code Honesty

## Sprint v2-S1 — Instrument Honesty (Gates, Cost, Syntax, Stubs)

**Objective:** every number the system reports becomes true. This sprint retires the H-series findings and is the hard prerequisite for all measurement.
**Dependencies:** v2-S0 (spec text to build against). **Expected side effect (document it, don't revert it):** bench pass-rates will *drop* when fabricated gates stop admitting — record before/after per Epic S1.5.

- [ ] **Epic S1.1 — Real gates (H1)** — `src/sagiha/outer_loop/evaluator/gate_evaluator.py`
  - [ ] Subtask: `RunContext.base_commit` field (`src/sagiha/domain/control.py`, additive); `RunLoop` checkpoints `run-start` before step 1 (`src/sagiha/agency/run_loop.py`).
  - [ ] Subtask: `tests_unmodified` via `git diff --name-only <base> -- tests/` through `dispatch()`; `diff_within_bounds` via `--numstat` vs `GatesConfig.max_diff_lines`; `no_new_suppressions` via `-U0` added-line pattern scan.
  - [ ] Subtask: `coverage_not_decreased` honest `None` + `GateReport.required_gates: frozenset[str]` (`src/sagiha/domain/work.py`) so `admitted` computes over the evaluable set.
  - [ ] Verification: e2e test — a run editing `tests/` yields `tests_unmodified=False ∧ admitted=False`; oversized diff fails bounds (`tests/unit/test_sprint3a_e2e.py` extended).
- [ ] **Epic S1.2 — Live budget & cost telemetry (H2)**
  - [ ] Subtask: `ModelProvider` v2 — `complete() -> Completion(message, usage, model)` (`src/sagiha/ports/model.py`, `domain/trajectory.py`); populate usage in `adapters/model/openai.py`; cassette migration script `scripts/migrate_cassettes_v2.py` (fixtures migrated same PR).
  - [ ] Subtask: `PricingConfig` per tier (`domain/config.py`); `RunLoop` emits real `TokenUsage`/`CostSummary`, calls `governor.record_spend()`; enforce `max_wall_clock_s` + sandbox concurrency in `kernel/governor.py`.
  - [ ] Subtask: Fix stuck-break dangling `tool_use` (synthetic `is_error` results before break) in `agency/run_loop.py`.
  - [ ] Verification: unit — $0.01 cap aborts at step 2 via the (now reachable) budget break; ledger within 5% of provider-reported usage on a live smoke run.
- [ ] **Epic S1.3 — Real `syntax_valid` (H4)** — `src/sagiha/adapters/workspace/local.py`
  - [ ] Subtask: `ast.parse` pre-write for `.py`; on `SyntaxError` do not write, return `syntax_valid=False, reason=f"syntax_error:{lineno}"`.
  - [ ] Verification: broken-edit test asserts file on disk unchanged and model receives the failing line.
- [ ] **Epic S1.4 — Stubs fail loud (H3)** — `adapters/sandbox/container.py`, `adapters/mcp/driver.py`, `adapters/telemetry/otel.py`
  - [ ] Subtask: every unimplemented method → `raise NotImplementedError("Block/Sprint …")`; `tests/unit/test_block5_scaffolding.py` inverted to assert raising.
  - [ ] Verification: grep gate in CI — no stub returns a success-shaped literal.
- [ ] **Epic S1.5 — Honest re-measure**
  - [ ] Subtask: run `sagiha harvest` + `sagiha bench --aa` before merging S1.1 and after; commit both reports to `docs/rationale/benchmarks/`.
  - [ ] Verification: STATUS updated with the post-honesty baseline and the explicit note that the drop is the fix.

**Exit gate:** 127+ tests green (count monotonic); replay job green post-cassette-migration; live smoke run shows non-zero cost telemetry; gate-dishonesty e2e tests in CI; A/A noise floor re-measured on honest gates.

## Sprint v2-S2 — Port Consolidation & Kernel Corrections

**Objective:** the v2 contract surface, locked before Block 3 writes real consumers against the old one.
**Dependencies:** v2-S1 (the `ModelProvider` v2 bump lands there; this sprint completes the remaining bumps).

- [ ] **Epic S2.1 — Deletions & merge (ADR-0019)** — `src/sagiha/ports/`
  - [ ] Subtask: delete `reviewer.py`, `embedding.py`; delete `ShortTermMemory` Protocol from `memory.py` (adapter already gone, R7); rewrite `advisory.py` → single `Advisory.predict(kind, task, branch_id) -> Prediction` + `PredictionKind` in `domain/work.py`.
  - [ ] Verification: `tests/contracts/test_port_shape.py` (dynamic enumeration) green; grep proves zero dangling imports; port count = 15.
- [ ] **Epic S2.2 — PURE argv allowlist (ADR-0020)** — `src/sagiha/kernel/policy/effects.py` (new, TCB-protected by existing `tcb-isolation` contract)
  - [ ] Subtask: `PURE_ARGV`, `PURE_GIT_OPS`, `classify_command(argv, declared)` (never widens; `bash -lc` never narrowed); `ToolRegistry` v2 gains `effect_for_call`; `RunLoop` + `GateEvaluator` classify `run_command` per invocation.
  - [ ] Verification: proving cassette — `["git","status"]` re-executes under `replay --verify`, `["rm","x"]` served from recording; re-execution fraction ≥ 60% on the pinned suite.
- [ ] **Epic S2.3 — Builtins corrected** — `src/sagiha/adapters/tools/builtins.py`
  - [ ] Subtask: delete the `app/` path-strip hack (grant-scope integrity — authorized path must equal effected path); fix the fixture instead.
  - [ ] Subtask: add `write_file` (DESTRUCTIVE, `x-sagiha-path`); reclassify `apply_edit` → DESTRUCTIVE; structured `DirEntry`/`Match` JSON returns.
  - [ ] Verification: new-file creation e2e passes; replay never re-executes `apply_edit`.
- [ ] **Epic S2.4 — Composition & config hardening** — `src/sagiha/composition.py`, `domain/config.py`
  - [ ] Subtask: derive `tool_schemas` from `BUILTIN_SCHEMAS` (single source, `sorted()` canonical order for cache stability — drift bug: composition's `apply_edit` schema currently omits `expected_occurrences`); `Kernel.workspace: Workspace` (port type, not `LocalWorkspace`).
  - [ ] Subtask: `validate_security_invariants` gains judge-separation refusal (`roles["judge"]` resolves to same (provider, model) as `execution` while `search.enabled` ⇒ `ValueError`); `SearchConfig.prune_on_first_gate_fail`; `ContextConfig` gains `keep_first_exchanges`/`keep_last_tokens`, `compact_at_headroom → 0.20`.
  - [ ] Verification: composition contract tests extended; a same-model judge config fails at load.
- [ ] **Epic S2.5 — Trajectory completeness for resume/replay/export**
  - [ ] Subtask: persist assistant `Message` on `TrajectoryStep` (schema addition + upcaster in `domain/upcasters.py`) so `_reconstruct_history` stops dropping text-only turns and resumed digests can match.
  - [ ] Verification: freeze → kill → resume → replay round-trip test with a text-turn-bearing cassette.

**Exit gate:** port count 15; three v2 bumps merged with migration notes; `lint-imports` 5/5 + `pyright` 0 sustained; resume/replay round-trip green; ADR-0019/0020 marked Accepted-Implemented.

---

# PHASE 3 — New Capabilities (competitive order: risk retired × value ÷ cost)

## Sprint v2-S3 — Context Engine & Safety (Compactor, TaintGate, FrozenRunState)

**Objective:** long runs stop dying at the window edge, and untrusted content stops being a silent write path. The two mechanisms ship together because taint must propagate *through* compaction (FI §R1).
**Dependencies:** v2-S1/S2. **This is the Spec's action-plan #1 — nothing in Sprints 4–7 produces trustworthy long-horizon numbers without it.**

- [x] **Epic S3.1 — `ContextAssembler`** — `src/sagiha/agency/context/assembler.py` (new package)
  - [x] Subtask: extract inline history/`ModelRequest` assembly from `RunLoop`; `from_trajectory()` absorbs `_reconstruct_history`; retrieval seed accepted **only at construction** (seed-only by shape — no public post-construction `RetrievalHit` method); `prefix_digest` emitted per assembly.
  - [x] Verification: contract test asserts no refresh surface; cache-stability regression signal (`prefix_digest` constant across steps) in e2e.
- [x] **Epic S3.2 — `ExchangeCompactor`** — `src/sagiha/agency/context/compactor.py`
  - [x] Subtask: `Exchange` unit (assistant + paired results + reasoning, never split); token-budgeted keep policy; middle-span → synthetic tagged summary turn; `TruncatingCompactor` (deterministic default) + `ModelCompactor` (compaction role); `CompactionApplied` event (`domain/events.py` + catalog regen).
  - [x] Verification: conformance — post-compaction request provider-valid (zero orphan `tool_result` ids; reasoning blocks intact or dropped whole-exchange); `total ≤ keep budgets ⇒ no-op`; 200-step synthetic run completes under a 128k window.
- [x] **Epic S3.3 — TaintGate v1** — `kernel/policy/engine.py`, `kernel/dispatch.py`, `adapters/tools/registry.py`, `domain/content.py`
  - [x] Subtask: `ToolResult.trusted` field; `register_handler(..., trusted_output)`; builtins flagged (read/list/grep/run untrusted; apply_edit/write_file trusted); `record_outcome` resolves `run_id` from the still-live grant and marks `_tainted_runs` (monotonic); `authorize()` denies tainted-run mutations with `requires_human=True` at every autonomy level; `MUTATION_TOOLS` in `kernel/policy/effects.py`; untrusted envelope at assembler prompt boundary (`result_message`); `TaintIntroduced` event from dispatch.
  - [x] Subtask: taint → compactor: tainted-span summaries carry the envelope (extends `test_external_provenance_survives_roundtrip` to the summary path).
  - [x] Verification: injection canary — planted hostile README instructs a write; the mutation is denied `requires_human=True`; zero tainted diffs land unapproved.
- [x] **Epic S3.4 — `FrozenRunState` + provider degradation** — `domain/control.py`, `agency/run_loop.py`, `adapters/model/fallback.py`
  - [x] Subtask: schema per FI §A3 (grants **absent by design** — contract test extends `test_no_grant_in_any_public_signature`); freeze/thaw path (thaw = rebuild kernel, re-materialize at `worktree_ref`, re-authorize on demand); consumers: budget-park, failover, future interrupt.
  - [x] Subtask: degradation policy — backoff-first economics rule; failover as checkpoint event (`ProviderFailover`), reasoning blocks dropped whole-exchange cross-provider; per-role `fallback` binding resolved at composition (replaces the current in-adapter blind chain semantics in `fallback.py` for role-level failover).
  - [x] Verification: freeze → `kill -9` → thaw → identical final `GateReport` ×3.

**Exit gate:** long-run e2e (200 steps) green; injection canary zero-leak; freeze/thaw deterministic; cache-hit-rate metric reported per run. **CLOSED 2026-07-31.**

## Sprint v2-S4 — Measurement Re-Baseline + Best-of-N (Block 2 + Block 3)

**Objective:** the E0 harness graduates from scaffolding to instrument, then Best-of-N ships against it — measurement strictly before the capability it measures, per the resequencing doctrine.

- [ ] **Epic S4.0 — Resolve `e0/` vs `adapters/benchmark/` duplication** — delete `adapters/benchmark/` & `ports/benchmark.py` (ADR-0024, port count 19 → 17); create agency-internal `e0/protocols.py` (`TaskHarvester`, `SuiteRunner`, `StatisticalTest`).
- [ ] **Epic S4.1 — E0 honesty (H5) + harvester validation** — `src/sagiha/e0/`
  - [ ] Subtask: rewrite `e0/statistics.py` in pure stdlib (~150 LOC) with McNemar exact binomial test (`math.comb`), seeded bootstrap CIs, Holm-Bonferroni correction, and `ComparisonResult.beats_noise_floor: bool | None = None` (absence of verdict is never a pass); harvester validation gate (`validate_task` with scratch worktree at `base_commit`, test checkout, revert check, determinism probe $k=3$); runner threading `task.base_commit` and real cost; publish `benchmarks/definitions/s0-core.json` (≥30 validated tasks) + CI `bench-aa` job + `docs/rationale/benchmarks/noise-floor.md` + close RC-7.
  - [ ] Verification: `sagiha bench --aa` report artifact in CI; pinned suite committed; statistics verified against textbook fixtures.
- [ ] **Epic S4.2 — Best-of-N over real worktrees** — `adapters/search/best_of_n.py`, `adapters/workspace/worktree.py`
  - [ ] Subtask: `CandidateSearch` v2 over real `GitWorktreeManager` worktrees (one kernel per active candidate); `adapters/search/protocols.py` (`CandidateExecutor`, `CandidateOutcome`); `SearchConfig.launch_mode` (`"sequential"` CPU default / `"parallel"` GPU opt-in with `CapacityLimiter`); candidate temperature ladder `candidate_temperatures` (default `0.0, 0.6, 0.9`) with diff-digest dedup and `diversity_ratio` reporting; early pruning (`prune_on_first_gate_fail`); sequential repair (`max_repair_rounds`); deterministic `should_escalate()` ladder.
  - [ ] Verification: S3 gate — BoN beats single-shot beyond the measured A/A floor; **zero grader modifications** (detectable thanks to v2-S1); parallel contention probe green; `diversity_ratio` materially above $1/N$.
- [ ] **Epic S4.3 — Scoring bootstrap S-0/S-1** — `adapters/search/scoring.py` (FI §A1)
  - [ ] Subtask: active S-0 deterministic proxy composite default ($w_{\text{pass}}\cdot\text{PassFraction} - w_{\text{diff}}\cdot\Delta\text{Diff}$, $w_{\text{cov}}$ and $w_{\text{supp}}$ default to `0.0` to avoid double-counting hard gates); `LocalJudgeScorer` (`backend="judge"`, ships OFF); judge≠generator enforced by S2.4 config refusal; learned ML scorers stubbed to `NotImplementedError("v2-S6+ — see ADR-0025")`.
  - [ ] Verification: proxies rank, never admit (contract test: `select()` cannot return a non-admitted candidate while an admitted one exists).
- [ ] **Epic S4.4 — Trace→dataset exporter** — `src/sagiha/outer_loop/export/`
  - [ ] Subtask: `sagiha export --format sft|dpo --min-gate admitted`; eligibility = admitted ∧ replay-verified (new `ReplayVerified` event) ∧ ¬tainted ∧ within-budget; `list_runs` port bump (PORT_VERSION 2 → 3); `sagiha replay <run_id> --verify` fix; DPO pairs grouped by parent task + `stable_prefix_digest`; secret redaction + license gate + per-provider reasoning flag.
  - [ ] Verification: schema-valid JSONL from existing bench cassettes; tainted-run exclusion tested against canary trajectory; eligibility ledger printed.

**Exit gate:** honest baseline + BoN delta published as $X \pm \sigma$ with cost-per-resolved-task alongside pass rate; `diversity_ratio` $> 1/N$; exporter emitting; the plan's first defensible external claim: "BoN beats single-shot by X ± σ over a floor of Y."

## Sprint v2-S5 — Perimeter & Isolation (B5a)

**Objective:** the sandbox the threat model has called "the perimeter" since ADR-0006 finally exists; `autonomous` autonomy unlocks.
**Dependencies:** v2-S3 (TaintGate — autonomy without it is refused), v2-S4 (worktrees to materialize).

- [ ] **Epic S5.1 — Rootless Podman `ContainerSandbox`** — `adapters/sandbox/container.py` (stub → real)
  - [ ] Subtask: lifecycle mgmt; worktree bind-mounts; `Workspace` conformance suite parametrized over `LocalWorkspace` + `ContainerSandbox` (the hexagon's payoff test); resource limits from `SandboxConfig`.
- [ ] **Epic S5.2 — Egress proxy + namespace firewall** — hostname allowlist at explicit proxy, direct outbound dropped; credential exclusion (no host secret reachable inside; per-grant short-lived injection).
- [ ] **Epic S5.3 — Config gating** — `subprocess`+`autonomous` refusal retained; container required from this sprint for `autonomous`/`scheduled`; `sagiha run --autonomy autonomous` legal for the first time.
  - [ ] Verification (sprint-wide): injection canary suite (hostile README / issue / fixture) across the pinned suite → **zero out-of-worktree effects, zero credential reads, zero non-allowlisted egress**; parallel sandboxed runs interference-free.

**Exit gate:** the S1-slice gate from the roadmap matrix, verbatim, now measurable — plus `autonomous` unlocked in config.

## Sprint v2-S6 — Retrieval, Code Graph & Cold-Start (Block 4)

**Objective:** the agent stops being file-blind; `sagiha init` closes the first-run competitive gap (W12).
**Dependencies:** v2-S3 (seed-only assembler — retrieval has a legal insertion point), v2-S4 (E0 to ablate against).

- [ ] **Epic S6.1 — FTS5 indexer + AST chunking** — `adapters/indexer/fts5.py` (stub → real): AST-bounded chunks with symbol-path prefixes; incremental file-watch update; `Indexer` conformance suite.
- [ ] **Epic S6.2 — Tree-sitter code graph** — `adapters/code_graph/treesitter.py` (stub → real): import/call/co-change edges from Tree-sitter + git; `impacted_by` for future risk gating; rebuildable-from-HEAD test.
- [ ] **Epic S6.3 — Code-intelligence tools** — register `find_symbols`, `get_skeleton`, `impacted_by` (`trusted_output=True` — harness-derived) within the 20-tool cap; retrieval seed wired into `ContextAssembler` (construction-time only).
- [ ] **Epic S6.4 — `sagiha init`** — `src/sagiha/cli.py` + `outer_loop/init/`: seed `AGENTS.md` from code graph + toolchain detection; output enters prompt Layer 4 verbatim.
- [ ] **Epic S6.5 — Retrieval honored in docs scoping** — indexer respects `retrieval: excluded` (S0.2).
  - [ ] Verification (sprint-wide): recall@10 ≥ target on a labelled query set; **retrieval-on beats retrieval-off** and **init-on beats init-off** ablations beyond the A/A floor — if either fails, the component does not become default-on (dense tier stays deferred per ADR-0014 regardless).

**Exit gate:** S2-slice gate met with ablation evidence; misses attributed (chunking vs vocabulary) before any dense-tier discussion.

## Sprint v2-S7 — Story-DAG, MCP & Interactive Surface (Block 4-macro + B5b/c)

**Objective:** the macro layer and the ecosystem — gated, as always, on planning proving it beats no-planning (ADR-0018).
**Dependencies:** v2-S4 (BoN + integration substrate), v2-S5 (MCP without a sandbox perimeter is refused), v2-S6 (decomposer needs file-closures from the code graph).

- [ ] **Epic S7.1 — Workflow runner + Story-DAG** — `src/sagiha/agency/workflow/`: `WorkflowStep`/`PipelineRunner` per `ports/workflow.py` (new, experimental); `PRDGeneratorStep`, `StoryDecomposerStep` (emits dependency edges + disjoint closures), `CodingStep` (inner loop unchanged), `VerifierStep`, `IntegrationStep` (rebase → re-gate → closure-invalidation ⇒ board), `ResolveConflictTask` **through the inner loop** (budget-capped, hunk-confined — never a gate-bypassing repair call); `PRDSpec`/`StorySpec`/`StoryBoard` in `domain/work.py`; step-boundary persistence ⇒ resumable/replayable pipelines.
  - [ ] Verification: **E0 ablation — planning beats feeding the raw prompt to the inner loop, beyond the floor, including 2-way parallel stories with IntegrationStep. If negative, the Protocol stays, the pipeline does not ship** (ADR-0018 honored to the letter).
- [ ] **Epic S7.2 — MCP client (B5b)** — `adapters/mcp/driver.py` (stub → real): stdio transport first; discovered tools register `trusted_output=False`, dispatch through the same choke point, grant-gated; taint applies.
  - [ ] Verification: external tool round-trip under grant + envelope; MCP tool output marked tainted end-to-end.
- [ ] **Epic S7.3 — Streaming + interrupt-and-steer (B5c fragment)** — `ModelProvider.stream` implemented in `adapters/model/openai.py`; exchange-boundary interrupt; steer = tail append (Layers 1–7 byte-identical — cache preserved); pause = `FrozenRunState`; minimal TUI in `cli.py`.
  - [ ] Verification: interrupt→steerable < 2s; steer turn shows tail-cache hit (`cache_read_tokens` ≥ prior tail); resumed-after-steer run replays.

**Exit gate:** ablation-positive (or honestly negative-and-shelved) macro layer; first external MCP tool executed under full policy; interactive steering demo against a live local model.

**→ Handoff:** with v2-S7 closed, Conductor phase C0 (`agi_evolution_path.md`) becomes startable — its hard deps (H1/H2 fixes, `FrozenRunState`, compactor, honest bench) are all above the line.

---

# MASTER TASK SUMMARY TABLE

| Sprint | Major Epic | Subtask / Item | Target Module / Path | Exit Gate Criteria |
| :--- | :--- | :--- | :--- | :--- |
| v2-S0 | Word budget | Budget script + CI ceiling; demotions | `scripts/docs_budget.py`, `docs/**` frontmatter | ≤15k normative words in CI |
| v2-S0 | rationale/ migration | Move reference/, legacy sprints, fe-sprints; retrieval-excluded key | `docs/rationale/`, `docs/README.md` | Zero broken links; sitemap regenerated |
| v2-S0 | SSOT consolidation | Seed-only ruling; R9→exchange compaction; TaintGate=T7; RHI tiers; FrozenRunState + distillation docs | `docs/02-architecture/*`, `docs/03-…/frozen-run-state.md`, `docs/04-…/*` | Reviews marked historical; single normative copy |
| v2-S0 | Decision records | ADR-0019…0023 | `docs/08-decisions/` | All with reversal conditions |
| v2-S0 | STATUS re-baseline | Honest capability table (H1 disclosed) | `docs/STATUS.md` | No claim contradicting the delta audit |
| v2-S1 | Gate honesty (H1) | base_commit; git-diff gates; required_gates set | `outer_loop/evaluator/gate_evaluator.py`, `domain/{control,work}.py`, `agency/run_loop.py` | tests/-edit ⇒ not admitted (e2e in CI) |
| v2-S1 | Cost honesty (H2) | ModelProvider v2 `Completion`; pricing; record_spend; wall-clock; cassette migration | `ports/model.py`, `adapters/model/openai.py`, `kernel/governor.py`, `scripts/migrate_cassettes_v2.py` | Budget break reachable; ledger ±5% of provider |
| v2-S1 | Syntax honesty (H4) | ast.parse pre-write, no-write-on-fail | `adapters/workspace/local.py` | Broken edit leaves disk unchanged |
| v2-S1 | Loud stubs (H3) | NotImplementedError; inverted scaffolding tests | `adapters/{sandbox,mcp,telemetry}/` | No stub returns success-shaped literal |
| v2-S1 | Honest re-measure | Before/after bench + A/A | `docs/rationale/benchmarks/` | Post-honesty floor published |
| v2-S2 | Port consolidation | Delete reviewer/embedding/ShortTermMemory; Advisory rewrite | `ports/`, `domain/work.py` | 15 ports; shape suite green; zero dangling imports |
| v2-S2 | PURE allowlist | effects.py; classify_command; ToolRegistry v2 | `kernel/policy/effects.py`, `ports/tool_registry.py` | ≥60% steps re-executed in replay --verify |
| v2-S2 | Builtins corrected | De-hack app/; write_file; apply_edit→DESTRUCTIVE | `adapters/tools/builtins.py` | New-file e2e; no apply_edit re-execution |
| v2-S2 | Composition/config | Schema SSOT + canonical order; Workspace port type; judge-separation refusal; new config fields | `composition.py`, `domain/config.py` | Same-model judge fails at load |
| v2-S2 | Trajectory completeness | Persist assistant Message; upcaster | `domain/{trajectory,upcasters}.py`, `adapters/trajectory/sqlite.py` | Freeze/resume/replay round-trip green |
| v2-S3 | ContextAssembler | Extract assembly; seed-only by construction; prefix_digest | `agency/context/assembler.py` | No post-construction retrieval surface (contract test) |
| v2-S3 | ExchangeCompactor | Exchange unit; keep policy; summary turn; two adapters | `agency/context/compactor.py`, `domain/events.py` | 200-step run under 128k; pairing conformance |
| v2-S3 | TaintGate v1 | trusted flag; monotonic run taint; mutation denial; envelope; summary propagation | `kernel/policy/{engine,effects}.py`, `kernel/dispatch.py`, `adapters/tools/registry.py`, `domain/content.py` | Injection canary: zero unapproved tainted diffs |
| v2-S3 | FrozenRunState + degradation | Schema (grants absent); freeze/thaw; failover-as-checkpoint | `domain/control.py`, `agency/run_loop.py`, `adapters/model/fallback.py` | kill -9 ×3 ⇒ identical GateReport |
| v2-S4 | E0 hardening | Harvest validation; A/A CI artifact; stats fixtures | `e0/`, `adapters/benchmark/` | Floor with CI on pinned suite |
| v2-S4 | Best-of-N | Worktree parallel; pruning; repair; stagger | `adapters/search/best_of_n.py`, `adapters/workspace/worktree.py` | BoN > single-shot beyond floor; zero grader edits |
| v2-S4 | Scoring S-0/S-1 | Deterministic composite; local judge; rank-never-admit | `adapters/search/scoring.py` | select() cannot bypass admission (contract test) |
| v2-S4 | Dataset exporter | sagiha export; SFT/DPO; taint/secret/license gates | `outer_loop/export/`, `cli.py` | Schema-valid JSONL; canary excluded |
| v2-S5 | Podman sandbox | Lifecycle; mounts; Workspace conformance ×2 adapters | `adapters/sandbox/container.py` | Conformance suite parametrized green |
| v2-S5 | Egress + secrets | Proxy allowlist; namespace drop; credential exclusion | sandbox infra + `domain/config.py` | Zero non-allowlisted egress in canary |
| v2-S5 | Autonomy unlock | Container-required gating | `domain/config.py` | autonomous legal; subprocess+autonomous still refused |
| v2-S6 | FTS5 + chunking | AST chunks; incremental update | `adapters/indexer/fts5.py` | recall@10 ≥ target on labelled set |
| v2-S6 | Code graph | TS+git edges; impacted_by; rebuildable | `adapters/code_graph/treesitter.py` | Rebuild-from-HEAD test |
| v2-S6 | Code-intel tools + seed | find_symbols/get_skeleton/impacted_by; assembler seed | `adapters/tools/builtins.py`, `agency/context/assembler.py` | Retrieval ablation positive beyond floor |
| v2-S6 | sagiha init | AGENTS.md generation | `cli.py`, `outer_loop/init/` | init-on beats init-off ablation |
| v2-S7 | Story-DAG | Steps + IntegrationStep + ResolveConflictTask (gated path) | `agency/workflow/`, `ports/workflow.py`, `domain/work.py` | Planning-beats-no-planning ablation, incl. 2-way parallel |
| v2-S7 | MCP client | stdio; untrusted registration; choke-point dispatch | `adapters/mcp/driver.py` | External tool under grant + taint end-to-end |
| v2-S7 | Streaming + steer | stream(); exchange-boundary interrupt; pause=freeze; TUI | `adapters/model/openai.py`, `agency/run_loop.py`, `cli.py` | <2s steerable; tail cache preserved on steer |

---

## Standing Rules (apply to every sprint)

1. **Regression protocol:** baseline test count is monotonic; `pytest` + `pyright` + `ruff` + `lint-imports` + `gen_event_catalog --check` + `replay --verify` on every PR; `bench --aa` at every sprint close, results committed.
2. **No periphery before the gate:** a sprint's exit gate is the only thing that closes it — MCP/OTel/frontend work inside an unrelated sprint is the anti-pattern two audits have now flagged; the seven `sprint-fe-*` files stay archived until v2-S7's TUI fragment creates a real consumer.
3. **Honest negatives are deliverables:** an ablation that fails ships as a published number and a shelved feature, not a retry with a friendlier prompt.
4. **STATUS.md is updated the day a gate closes**, in the v2-S series, and never claims what the delta audit's H-findings taught us to check first.

---

## Residual closeout — v2-S1 / v2-S2 (audit 2026-07-31)

Sprint status in `docs/STATUS.md` marks v2-S1/S2 **closed** for the primary H1–H4 and port-consolidation deliverables. A line-level re-audit against this plan + `refactor_sagiha_v2_guidelines.md` found **residuals that the written exit gates still require**. These are not new design decisions — they are unfinished items from the existing epics. Tracked as **RC-1…RC-8** in `docs/STATUS.md`. **Do not start v2-S3 until RC-1…RC-4 close.**

| ID | Epic source | Required fix (verbatim from plan/guidelines) | File(s) |
| :--- | :--- | :--- | :--- |
| RC-1 | S1.2 / PR-1.2 §7 | On stuck mid-`tool_use_blocks`, append synthetic `is_error=True` `ToolResultBlock`s for skipped calls **before** breaking | `agency/run_loop.py` |
| RC-2 | S1.2 / PR-1.2 §6 | Enforce `max_wall_clock_s` and step-token ceilings from `GovernorConfig` (fields exist, unenforced) | `kernel/governor.py`, `agency/run_loop.py` |
| RC-3 | S2.4 | `ContextConfig.keep_last_tokens: int = 24_000` (currently `20_000`) | `domain/config.py` |
| RC-4 | S2.5 | Persist assistant `Message` for text-only turns; `_reconstruct_history` must not skip empty `tool_calls` when `message` is present | `agency/run_loop.py` |
| RC-5 | Phase 2 exit | ~~Mark ADR-0019 / ADR-0020 `Accepted-Implemented`~~ **CLOSED 2026-07-31** | `docs/08-decisions/001{9,20}-*.md` |
| RC-6 | S2.2 exit metric | ~~Proving test asserts re-execution fraction `≥ 0.60` (currently `≥ 0.5`)~~ **CLOSED 2026-07-31** | `tests/unit/test_effect_classification.py` |
| RC-7 | S1.5 | Commit **before** + after honesty bench reports (only post exists today) | `docs/rationale/benchmarks/` |
| RC-8 | S2.4 soft | ~~Make `RunLoop.evaluator` required; stop agency default-constructing TCB~~ **CLOSED 2026-07-31** — `agency/run_loop.py` no longer imports `outer_loop` at all; `Kernel.evaluator` is non-optional; pinned by `tests/contracts/test_composition.py::test_agency_never_constructs_a_tcb_evaluator` | `agency/run_loop.py`, call sites |
