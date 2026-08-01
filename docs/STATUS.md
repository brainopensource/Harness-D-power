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

Authority: [`refactor_sagiha_v2_guidelines.md`](implementation/refactor_sagiha_v2_guidelines.md) §2 (verified
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
| `v2-S4` | Measurement re-baseline + Best-of-N — **closed** (honest-negative empirical half) |
| `v2-S5` | Container perimeter, egress allowlist — **closed** |
| `v2-S6` | Retrieval, code graph, cold-start — **closed** (honest-negative empirical half) |
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
| Config security refusals (subprocess+autonomous, host network + interactive-only, `tests_unmodified`) | Implemented |
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
| Block 3 — Best-of-N search | **Mechanism complete; shipped off by default** (`search.enabled=false`). `BestOfNSearch` over real worktrees; sequential + parallel; `diversity_ratio`; rank-never-admit `select()`; `bench --compare single_shot,bon` with cost-per-resolved-task and machine-checked verdict. **Never measured against a real suite** — 0/23 tasks validate ([findings](./rationale/benchmarks/s4-harvest-findings.md)). Protocol and adapter retained; suite + any default-on flip are explicit **pre-S6** hard dependencies for ablation gates | `v2-S4` (closed) |
| Block 4 — retrieval / code graph | **Mechanism complete; shipped off by default** (`retrieval.enabled=false`). FTS5 indexer with AST-bounded chunks; Tree-sitter code graph with import/call/co-change edges; `find_symbols`/`get_skeleton`/`impacted_by` tools; construction-time Layer-6 seed; `sagiha init` generates `AGENTS.md`. **Never measured against a labelled recall@10 set or ablation suite** — empirical claims (recall@10, retrieval-on beats retrieval-off, init-on beats init-off) **not made**; `retrieval.enabled` defaults to **`false`**; ablation gates are explicit **pre-default-on** hard dependencies | `v2-S6` (closed) |
| Block 4 — Workflow DAG (ADR-0018) | Protocol only; gated on an E0 ablation that cannot be trusted until `v2-S1` | `v2-S7` |
| Block 5 — container sandbox | **Real** — rootless Podman `ContainerSandbox`; Workspace conformance ×2; egress allowlist proxy; `sagiha run --autonomy autonomous` legal with container | `v2-S5` (closed) |
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

> **Generated by `scripts/verify.sh`. Do not edit by hand.** Verbatim copy of a saved run:
> [`verify-W5-p0-complete.txt`](./rationale/done/verify-W5-p0-complete.txt). Typing these numbers
> from memory produced defect C-2 — STATUS claimed a clean typecheck and clean lint while 3 pyright
> and 34 ruff errors sat in the tree for a sprint.

At `51cfa24` (`refactor_aether_V210`), 2026-08-01. Host: Python 3.14.6 · podman 5.8.4.

| Signal | Result | Status | Command |
| :--- | :--- | :--- | :--- |
| Tests (full) | 358 passed, 0 failed | ✅ | `uv run pytest -q` |
| Tests (not podman) | 347 passed | ✅ | `uv run pytest -q -m "not podman"` |
| Type check | 0 errors | ✅ | `uv run pyright src/sagiha` |
| Import contracts | 5/5 kept | ✅ | `uv run lint-imports` |
| Lint | 0 errors | ✅ | `uv run ruff check .` |
| Format | 0 files would reformat | ✅ | `uv run ruff format --check .` |
| Docs budget | 14,899 normative words (ceiling 15,000) | ✅ | `python3 scripts/docs_budget.py --max 15000` |
| Link integrity | 0 dead relative links | ✅ | `python3 scripts/check_links.py` |
| Event catalog | in sync (38 events) | ✅ | `python3 scripts/gen_event_catalog.py --check` |

**Ports:** 17 Protocols across 16 files (ADR-0019 restated count; `CommitReplayHarvester`/`TaskRunner`
deleted per [ADR-0024](./08-decisions/0024-e0-is-a-tool-not-a-port.md)).
**Podman on this host:** present.

Not yet folded into `verify.sh`, and therefore still run by hand:

| Signal | Result | Command |
| :--- | :--- | :--- |
| Coverage | `fail_under = 80` | `pytest --cov=src/sagiha` |
| Replay | green | `uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json …` |

**Test arithmetic.** 347 non-Podman + 11 Podman = 358, Podman present. The prior "321 (310 + 11)"
neither added up nor matched the tree.

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
| `sagiha init` | **Available now** — generates `AGENTS.md` from toolchain + layout (`--force` to overwrite) |

## **Next Items, In Order**

1. ~~**`v2-S0` (Phase 0)**~~ — **closed 2026-07-31.** STATUS restored and re-baselined, docs budget and link gates in CI, v2 corpus folded into `01`–`08`, ADRs 0019–0023 recorded.
2. ~~**`v2-S1` (Phase 1)**~~ — **closed 2026-07-31.** H1–H4 fixed (PR-1a…PR-1d), `scripts/migrate_cassettes_v2.py` executed, `harvest` + `bench --aa` post-honesty baseline committed to `docs/rationale/benchmarks/s1_honest_baseline.md`.
3. ~~**`v2-S2` (Phase 2)**~~ — **closed.** Port consolidation & kernel corrections.
4. ~~**`v2-S3` (Phase 3)**~~ — **closed 2026-07-31.** ContextAssembler + ExchangeCompactor; TaintGate v1 (envelope at assembler prompt boundary); FrozenRunState freeze/thaw + role-level failover; 200-step / canary / kill-9×3 green.
5. ~~**`v2-S4` (Phase 4)**~~ — **closed 2026-07-31 (honest-negative empirical half).** Mechanism
   complete (Epics S4.0–S4.4, RC-1…RC-8, harvester D1–D3, `bench --compare` wiring,
   `BenchmarkReporter.verdict`). Empirical claim "BoN beats single-shot by X ± σ" **not made** —
   harvest yields 0/23 valid tasks from this repo; `search.enabled` defaults to **`false`**;
   `s4_bon_delta.md` intentionally unpublished; `bench-aa` stays a guarded no-op; live `--compare`
   remains the highest-risk untested path until a suite exists. Closeout write-up:
   [s4-harvest-findings.md](./rationale/benchmarks/s4-harvest-findings.md). Pinned ≥30-task suite +
   populated noise floor + measured delta are **pre-S6** hard dependencies (ablation gates).
6. ~~**`v2-S5` (Phase 5)**~~ — **closed 2026-07-31.** Rootless Podman `ContainerSandbox`;
   Workspace conformance parametrized over LocalWorkspace + ContainerSandbox; hostname
   CONNECT egress proxy with `--network=none` (direct outbound dropped); credential exclusion
   **as host-env scrub + `SECRET_MATERIALIZE_NAMES` path exclusion only — per-grant short-lived
   secret injection is not implemented** (m-8; v2-S7 candidate);
   `sagiha run --autonomy autonomous` legal with `sandbox.runtime=container`. CI Podman job
   is TCB — propose `podman-perimeter` job for human authorship (see `docs/implementation/ci-podman-perimeter.md`).
7. ~~**`v2-S6` (Phase 6)**~~ — **closed 2026-08-01 (honest-negative empirical half).** Mechanism
   complete (Epics S6.1–S6.5): FTS5 indexer + AST chunking + `retrieval: excluded` frontmatter;
   Tree-sitter code graph + shared `IndexService` walk + rebuild-from-HEAD; code-intelligence
   tools (`find_symbols`, `get_skeleton`, `impacted_by`) with `trusted_output=True`; construction-time
   Layer-6 retrieval seed; `sagiha init` generates `AGENTS.md` (Layer 4 verbatim when present).
   Empirical claims (recall@10 ≥ target, retrieval-on beats retrieval-off, init-on beats init-off)
   **not made** — no labelled query set or pinned ablation suite exists yet; `retrieval.enabled`
   defaults to **`false`**; dense tier stays deferred per ADR-0014. Closeout design:
   [`2026-07-31-v2-s6-retrieval-code-graph-design.md`](./superpowers/specs/2026-07-31-v2-s6-retrieval-code-graph-design.md).
   Labelled recall set + populated ablation suite are **pre-default-on** hard dependencies.
8. **`v2-S7` (Phase 7)** — Story-DAG, MCP, interactive surface

### Known open item (Resolved in v2-S1)

`sagiha replay verify` against the committed fixture is **passing** post-cassette-migration (`scripts/migrate_cassettes_v2.py`) and workspace git initialization (`scripts/gen_replay_fixture.py`).

> **Standing rule.** This page is updated **the day a gate closes**, in the `v2-S` series, and it never makes a claim the delta audit contradicts.

