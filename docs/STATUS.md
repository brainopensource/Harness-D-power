---
status: normative
updated: 2026-07-31
---
# **SAGIHA — Current Status**

> [!IMPORTANT]
> This page is the single source of **implementation truth**. Architecture docs describe the SOTA
> *target*; this page says what exists today and what to build next. When a guide and this page
> disagree, this page wins.
>
> **Re-baselined 2026-07-31 for the v2 series.** Deleted in `2b80840`, restored in PR-0a and
> rewritten against a line-level audit of `src/sagiha` rather than sprint intent. **Several rows
> moved backwards** — the previous version reported capability the code did not support.

Authority: [`refactor_sagiha_v2_guidelines.md`](../refactor_sagiha_v2_guidelines.md) §2 (verified
baseline) · [ADR log](./08-decisions/README.md) · historical audits under [`reviews/`](./rationale/reviews/README.md).

## **Sprint Numbering**

Sprints 1–3b and 4 are **closed under the old numbering** and are not reopened. The v2 re-baseline
runs as a fresh series, **`v2-S0` … `v2-S7`**, mapping to the phases in the v2 guidelines:

| Series | Objective |
| :--- | :--- |
| `v2-S0` | Docs, governance, SSOT — **closed** |
| `v2-S1` | **Instrument honesty** — H1–H4 fixed, post-honesty baseline re-measured — **closed** |
| `v2-S2` | Port consolidation & kernel corrections — **closed** |
| `v2-S3` | Context engine (`ContextAssembler`, `ExchangeCompactor`) + TaintGate v1 + FrozenRunState — **closed** |
| `v2-S4` | Measurement re-baseline + Best-of-N |
| `v2-S5` | Container perimeter, egress allowlist |
| `v2-S6` | Retrieval, code graph, cold-start |
| `v2-S7` | Story-DAG, MCP, interactive surface |

## **The Honesty Caveat — read before citing any number from this repo**

**H1–H4 are FIXED and re-measured as of 2026-07-31** (`v2-S1`). This section is kept because it is
the reason every number recorded *before* that date must not be cited — not because the defects
are open.

> **Pass-rate drop note:** Post-honesty baseline re-measurement (`docs/rationale/benchmarks/s1_honest_baseline.md`)
> shows a pass rate of 0.0% on un-cassetted replay benchmark runs. The pass-rate drop is the fix: un-evaluated
> runs and missing base refs now fail closed (`admitted = False`) rather than fabricating success.

| ID | Defect (all fixed 2026-07-31) | Was at | Fixed by |
| :-- | :--- | :--- | :--- |
| **H1** | Three of four coding gates hardcoded `True` — including `tests_unmodified`, the gate T3 rests on | `outer_loop/evaluator/gate_evaluator.py` | PR-1a |
| **H2** | `record_spend()` called from nowhere; budget break unreachable; every step reported `TokenUsage(0,0)` / `$0.00` | `kernel/governor.py` · `agency/run_loop.py` | PR-1b |
| **H2b** | `acquire()` enforced neither `max_concurrent_sandboxes` nor the spend limit — both args stored, never read | `kernel/governor.py` | PR-1b |
| **H3** | `ContainerSandbox.apply_edit()` reported a landed edit for a file it never opened; `MCPClientDriver.invoke_tool()` returned `""` | `adapters/sandbox/` · `adapters/mcp/` | PR-1d |
| **H4** | `syntax_valid=True` hardcoded on **both** the success and failure paths | `adapters/workspace/local.py` | PR-1c |

**Consequence for readers:** any bench pass-rate, cost figure, or "gated" claim recorded before
`v2-S1` closes must not be cited. Pass-rates are **expected to fall** when the gates stop lying;
that fall is the deliverable, not a regression.

## **What Works Now**

Marked against code, not intent. "Implemented" means a line-level read supports the claim.

| Area | Status |
| :--- | :--- |
| Domain models & typed ports in `src/` | Implemented |
| Port-shape meta-conformance (`tests/contracts/`) | Implemented |
| Import-linter CAR layering (5/5 contracts) | Implemented |
| Config security refusals (subprocess+autonomous, host network, `tests_unmodified`) | Implemented |
| `ModelRequest` v2 (system, tools, sampling, role) | Implemented |
| Digest-keyed cassette replay + `CassetteMismatchError` | Implemented |
| `ToolUseBlock` → `ToolCall` resolution, effect from registry | Implemented |
| `call_id` + `is_error` on `ToolResult` and completion events | Implemented |
| Coding gates (`tests_unmodified`, `diff_within_bounds`, `no_new_suppressions`) | **Implemented (PR-1a)** — real `git diff` checks against `RunContext.base_commit`, routed through the dispatch choke point. `coverage_not_decreased` reports an honest `None`: no `Toolchain` adapter, no baseline |
| Typed event reads through `ALL_EVENTS` + `upcasters.py` | Implemented |
| `RunLoop` — max steps, `end_turn`, stuck signature, **budget** | Implemented — the budget break is reachable as of PR-1b |
| Prompt + history assembly into `ModelRequest` v2 | **Implemented (v2-S3)** — `agency/context/ContextAssembler` (seed-only Layer 6, `prefix_digest` / `stable_prefix_digest`); `ExchangeCompactor` |
| Five built-in tools over a root-confined local workspace adapter | Implemented |
| Schema-declared path scoping | Implemented |
| Path containment enforced before a grant is minted | Implemented (traversal, sibling-prefix, symlink escape) |
| Event bus + interceptors | Implemented — `anyio` task groups, per-observer timeout, quarantine |
| Capability dispatch choke point | Implemented — grant verified at the point of effect, unconditionally |
| SQLite-WAL trajectory store | Implemented (typed round-trip, NFS journal probe with fallback) |
| Resumable run state | Implemented — `runs` table, `RunLoop.run(resume=True)`, `sagiha run --resume` |
| OpenAI-compatible provider adapter | Implemented — covers Ollama/Qwen/OpenAI/vLLM. Reports real `usage` as of PR-1b |
| Cost & token telemetry | **Implemented (PR-1b)** — `ModelProvider` v2 returns `Completion(message, usage, model)`; `PricingConfig` converts usage to dollars; `record_spend()` is called after every completion |
| `syntax_valid` on edits | **Implemented (PR-1c)** — stdlib `ast.parse` before write; a syntax-breaking edit is not written |
| `sagiha run` / `replay --verify` / `harvest` / `bench` | Implemented and CLI-wired |
| E0-lite harness (`e0/`: harvester, runner, statistics, reporter) | Implemented — numbers taken **before** 2026-07-31 are over fabricated instruments and must be re-measured |

## **Scaffolding Present — Capability Pending**

Module shells, ports, and CLI stubs are **not** delivered capability. These rows were previously
reported as block-level progress; they are re-stated here honestly.

| Area | Reality | Lands |
| :--- | :--- | :--- |

| Block 2 — E0 benchmark | Real harness in `e0/`. `adapters/benchmark/` and `ports/benchmark.py` deleted ([ADR-0024](./08-decisions/0024-e0-is-a-tool-not-a-port.md)) — the layers contract forbade the adapter this port needed | `v2-S4` |
| Block 3 — Best-of-N search | **Mechanism complete.** `BestOfNSearch` over real `GitWorktreeManager` worktrees; sequential + parallel launch; temperature ladder; `diversity_ratio`; rank-never-admit `select()`; wired into `sagiha bench --compare single_shot,bon` with cost-per-resolved-task and a machine-checked verdict. **Never measured against a real suite** — 0/23 tasks validate from this repo's history ([findings](./rationale/benchmarks/s4-harvest-findings.md)), so `search.enabled` remains an untested default | `v2-S4` |
| Block 4 — retrieval / code graph | Ports only. No indexer, no FTS5, no Tree-sitter | `v2-S6` |
| Block 4 — Workflow DAG (ADR-0018) | Protocol only; gated on an E0 ablation that cannot be trusted until `v2-S1` | `v2-S7` |
| Block 5 — container sandbox | Stub — every method raises `NotImplementedError` (PR-1d) | `v2-S5` |
| Block 5 — MCP driver | Stub — `invoke_tool()` raises; `list_tools()` returns `[]`, a truthful null (PR-1d) | `v2-S7` |
| Block 5 — OTel exporter | Stub — `on_event()` raises (PR-1d) | `v2-S7` |
| Context compaction | `ExchangeCompactor` (`TruncatingCompactor` default + `ModelCompactor`); 200-step under 128k green | — |
| TaintGate / untrusted-data envelope | `ToolResult.trusted`; monotonic `_tainted_runs`; mutation deny `requires_human=True`; envelope at `assembler.result_message`; injection canary green | — |
| FrozenRunState + failover | Grants-absent freeze/thaw; budget-park; `ProviderFailover` + backoff-first role-level fallback; kill-9×3 GateReport green | — |

## **Explicitly Deferred**

Dense retrieval ([ADR-0014](./08-decisions/0014-defer-dense-retrieval.md)), AOI acting mode,
RHI Tier C ([ADR-0022](./08-decisions/0022-rhi-economic-refounding.md)), A2A remote pilots,
performance sidecars, warm LSP, and the Conductor — out of scope until Phase 7 closes.

## **Frozen Regression Signals**

Every PR holds or improves all of these. The test count is **monotonic** — it only rises.

| Signal | Baseline (2026-07-31) | Command |
| :--- | :--- | :--- |
| Tests | **266 passed** (253, 192, 174 at prior baselines; 158 at `v2-S1` close) | `uv run pytest -q` |
| Port count | **17 Protocols / 16 files** (ADR-0019 restated count; `CommitReplayHarvester`/`TaskRunner` deleted per [ADR-0024](./08-decisions/0024-e0-is-a-tool-not-a-port.md)) | `grep -rn "(Protocol)" src/sagiha/ports/ \| wc -l` |
| Type check | 0 errors, strict | `uv run pyright src/sagiha` |
| Lint | clean | `uv run ruff check && uv run ruff format --check` |
| Import contracts | **5/5** | `uv run lint-imports` |
| Event catalog | in sync (38 events) | `python scripts/gen_event_catalog.py --check` |
| Coverage | `fail_under = 80` | `pytest --cov=src/sagiha` |
| Replay | green | `uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json …` |

## **Commands Today vs Planned**

| Command | Availability |
| :--- | :--- |
| `sagiha version` | **Available now** |
| `sagiha run <goal> [--acceptance …]` | **Available now** (cassette or live) — reports real cost when `pricing` is configured |
| `sagiha replay <run_id> --verify` | **Available now** |
| `sagiha run --resume <run_id>` | **Available now** |
| `sagiha harvest [--repo …]` | **Available now** |
| `sagiha bench [--suite …] [--aa]` | **Available now** — post-honesty baseline at `docs/rationale/benchmarks/s1_honest_baseline.md` |
| `sagiha export --format sft\|dpo` | **Available now** — eligibility (admitted ∧ ¬tainted ∧ within-budget ∧ replay-verified), redaction, license gate |
| `sagiha init` | Planned — `v2-S6` |

## **Next Items, In Order**

1. ~~**`v2-S0` (Phase 0)**~~ — **closed 2026-07-31.** STATUS restored and re-baselined, docs budget and link gates in CI, v2 corpus folded into `01`–`08`, ADRs 0019–0023 recorded.
2. ~~**`v2-S1` (Phase 1)**~~ — **closed 2026-07-31.** H1–H4 fixed (PR-1a…PR-1d), `scripts/migrate_cassettes_v2.py` executed, `harvest` + `bench --aa` post-honesty baseline committed to `docs/rationale/benchmarks/s1_honest_baseline.md`.
3. ~~**`v2-S2` (Phase 2)**~~ — **closed.** Port consolidation & kernel corrections.
4. ~~**`v2-S3` (Phase 3)**~~ — **closed 2026-07-31.** ContextAssembler + ExchangeCompactor; TaintGate v1 (envelope at assembler prompt boundary); FrozenRunState freeze/thaw + role-level failover; 200-step / canary / kill-9×3 green.
5. **`v2-S4` (Phase 4)** — measurement re-baseline + Best-of-N. E0 honesty (H5), harvester
   validation, `BestOfNSearch`, scoring S-0, and the trace→dataset exporter are implemented
   (Epics S4.0–S4.4). The line-level audit in `docs/implementation/sprint_v2_s4_fixes.md`
   found eight defects in that first pass; all eight are now fixed: paired statistics
   aggregate `k>1` repetitions correctly, an uncomputable A/A floor stays `None` rather than
   trivially "beaten", `holm()` is actually invoked (`adjusted_p_value` populated;
   `holm_correct_family` added for real multi-treatment families), `diversity_ratio` is
   reported on `CandidateSelected` instead of being an uncalled method, `KernelCandidateExecutor`
   no longer recursively builds a `BestOfNSearch`/`GitWorktreeManager` per candidate
   (`build_kernel(..., include_search=False)`), and the parallel launch stagger sleeps before
   acquiring an inference-capacity slot rather than while holding one. RC-5 (ADR-0019/0020 →
   Accepted-Implemented), RC-6 (re-execution exit metric raised to `>= 0.60`), and RC-8
   (`RunLoop.evaluator` now required; `agency/run_loop.py` no longer imports the TCB at all,
   pinned by a contract test) are closed — **RC-1…RC-8 are all closed.** `sagiha bench --compare
   single_shot,bon` is wired end-to-end, publishing cost-per-resolved-task and `diversity_ratio`
   alongside pass rate, with `BenchmarkReporter.verdict` enforcing the honest-negative clause in
   code (NEGATIVE below the floor, COST LOSS on a pass-rate win at a cost regression, INVALID at
   the `1/N` diversity floor). The stale `tests/fixtures/replay_smoke/workspace` fixture was
   regenerated and tracked, closing the "not a tracked path" CI trap
   (`refactor_sagiha_v2_guidelines.md` §2.4/§11.6).

   **The empirical half of the exit gate is NOT met, and no number is published in its place.**
   Harvesting this repo's own history for the pinned ≥30-task suite exposed three further
   instrument defects — all now fixed — the most serious being that the venv's **editable
   install defeated worktree isolation**, so every worktree-scoped run (harvester validation,
   both bench arms, and every Best-of-N candidate) imported the live working tree instead of its
   own checked-out source. Best-of-N candidate diffs were therefore invisible to the gates
   scoring them. With the instrument repaired, `harvest --validate` reports **0/23 valid tasks**:
   this repo's history is sprint-sized commits, not the small fix-commits commit-replay
   harvesting requires. So `benchmarks/definitions/s0-core.json` does not exist, `bench-aa`
   remains a documented no-op, and the claim "BoN beats single-shot by X ± σ" is **not made**.
   Full write-up and unblock options: [s4-harvest-findings.md](./rationale/benchmarks/s4-harvest-findings.md).
   Closing that half needs a task corpus (external repo or a hand-authored suite), not more code.

### Known open item (Resolved in v2-S1)

`sagiha replay verify` against the committed fixture is **passing** post-cassette-migration (`scripts/migrate_cassettes_v2.py`) and workspace git initialization (`scripts/gen_replay_fixture.py`).

> **Standing rule.** This page is updated **the day a gate closes**, in the `v2-S` series, and it never makes a claim the delta audit contradicts.

