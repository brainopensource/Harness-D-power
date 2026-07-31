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
> **Re-baselined 2026-07-31 for the v2 series.** This page was deleted in `2b80840` and restored in
> PR-0a. The capability table below was rewritten against a line-level audit of `src/sagiha`, not
> against sprint intent. **Several rows moved backwards.** That is the point: the previous version
> of this page reported capability that a line-level read of the code does not support.

Authority: [`refactor_sagiha_v2_guidelines.md`](../refactor_sagiha_v2_guidelines.md) §2 (verified
baseline) · [ADR log](./08-decisions/README.md) · historical audits under [`reviews/`](./rationale/reviews/README.md).

## **Sprint Numbering**

Sprints 1–3b and 4 are **closed under the old numbering** and are not reopened. The v2 re-baseline
runs as a fresh series, **`v2-S0` … `v2-S7`**, mapping to the phases in the v2 guidelines:

| Series | Phase | Objective |
| :--- | :--- | :--- |
| `v2-S0` | Phase 0 | Docs, governance, SSOT — normative word budget, link gate, ADRs 0019–0023 |
| `v2-S1` | Phase 1 | **Instrument honesty** — H1–H4. Every number the system reports becomes true |
| `v2-S2` | Phase 2 | Port consolidation & kernel corrections |
| `v2-S3` | Phase 3 | Context engine (`ContextAssembler`, `ExchangeCompactor`) + TaintGate v1 |
| `v2-S4` | Phase 4 | Measurement re-baseline + Best-of-N |
| `v2-S5` | Phase 5 | Container perimeter (rootless Podman), egress allowlist |
| `v2-S6` | Phase 6 | Retrieval, code graph, cold-start |
| `v2-S7` | Phase 7 | Story-DAG, MCP, interactive surface |

## **The Honesty Caveat — read before citing any number from this repo**

Four defects mean that measurements taken before `v2-S1` closes are **uninterpretable**. They are
not "known issues"; they invalidate the instruments.

| ID | Defect | Verified at | Fixed in |
| :-- | :--- | :--- | :--- |
| **H1** | Three of four coding gates are hardcoded `True`. `no_new_suppressions`, `tests_unmodified`, `coverage_not_decreased`, and `diff_within_bounds` are literals — including `tests_unmodified`, the gate the T3 evaluation-capture threat model rests on and the one `Config` refuses to let you disable. | `outer_loop/evaluator/gate_evaluator.py:74-81` | `v2-S1` (PR-1a) |
| **H2** | `record_spend()` is correct but **called from nowhere** in `src/`. `remaining_budget()` therefore always returns the full budget, and the loop's budget break is unreachable. The loop emits `TokenUsage(0,0)` / `CostSummary(usd=0.0)` every step. | `kernel/governor.py:30-36` (no callers) · `agency/run_loop.py` | `v2-S1` (PR-1b) |
| **H2b** | `DefaultResourceGovernor.acquire()` mints a lease and enforces neither `max_concurrent_sandboxes` nor the spend limit. Both constructor args are stored and never read. | `kernel/governor.py:21-25` | `v2-S1` (PR-1b) |
| **H3** | `ContainerSandbox.apply_edit()` returns a success-shaped `EditResult` without touching anything; `write()` is `pass`; `MCPClientDriver.invoke_tool()` returns `""`. A stub that lies is worse than an absent adapter. | `adapters/sandbox/container.py` · `adapters/mcp/driver.py` | `v2-S1` (PR-1d) |
| **H4** | `LocalWorkspace.apply_edit` hardcodes `syntax_valid=True` on **both** the success and failure paths, while the tool catalog normatively promises a structural check before write. | `adapters/workspace/local.py` | `v2-S1` (PR-1c) |

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
| `GateReport.admitted` refuses to admit on a `None` coding gate | Implemented — but see **H1**: the gates it reads are literals |
| Typed event reads through `ALL_EVENTS` + `upcasters.py` | Implemented |
| `RunLoop` — max steps, `end_turn`, stuck signature | Implemented — the **budget** break is unreachable (**H2**) |
| Prompt + history assembly into `ModelRequest` v2 | Implemented, inline in the loop body; no `agency/context/` package |
| Five built-in tools over a root-confined local workspace adapter | Implemented |
| Schema-declared path scoping | Implemented |
| Path containment enforced before a grant is minted | Implemented (traversal, sibling-prefix, symlink escape) |
| Event bus + interceptors | Implemented — `anyio` task groups, per-observer timeout, quarantine |
| Capability dispatch choke point | Implemented — grant verified at the point of effect, unconditionally |
| SQLite-WAL trajectory store | Implemented (typed round-trip, NFS journal probe with fallback) |
| Resumable run state | Implemented — `runs` table, `RunLoop.run(resume=True)`, `sagiha run --resume` |
| OpenAI-compatible provider adapter | Implemented — covers Ollama/Qwen/OpenAI/vLLM. Drops `response.usage` on the floor (**H2**) |
| `sagiha run` / `replay --verify` / `harvest` / `bench` | Implemented and CLI-wired |
| E0-lite harness (`e0/`: harvester, runner, statistics, reporter) | Implemented — but every number it produces is taken over **H1**/**H2** instruments |

## **Scaffolding Present — Capability Pending**

Module shells, ports, and CLI stubs are **not** delivered capability. These rows were previously
reported as block-level progress; they are re-stated here honestly.

| Area | Reality | Lands |
| :--- | :--- | :--- |
| Coding gates (`tests_unmodified`, `diff_within_bounds`, `no_new_suppressions`) | **Fabricated** — hardcoded `True` (**H1**) | `v2-S1` |
| Cost & token telemetry | **Fictional** — always `TokenUsage(0,0)` / `$0.00` (**H2**) | `v2-S1` |
| `syntax_valid` on edits | **Constant `True`** on both branches (**H4**) | `v2-S1` |
| Block 2 — E0 benchmark | Real harness in `e0/`; a **parallel stub** implementation also exists under `adapters/benchmark/`. Duplication unresolved | `v2-S4` |
| Block 3 — Best-of-N search | Port + `GitWorktreeManager` stub with open SENIOR TODOs. `N>1` never executed | `v2-S4` |
| Block 4 — retrieval / code graph | Ports only. No indexer, no FTS5, no Tree-sitter | `v2-S6` |
| Block 4 — Workflow DAG (ADR-0018) | Protocol only; gated on an E0 ablation that cannot be trusted until `v2-S1` | `v2-S7` |
| Block 5 — container sandbox | **Lying stub** (**H3**) — returns fabricated success | `v2-S5` |
| Block 5 — MCP driver | **Lying stub** (**H3**) — `invoke_tool()` returns `""` | `v2-S7` |
| Block 5 — OTel exporter | Stub | `v2-S7` |
| Context compaction | Algorithm specified (R9, superseded by exchange-granular in `v2-S3`); **zero implementation**. Runs past the window die | `v2-S3` |
| TaintGate / untrusted-data envelope | Documented only; no `ToolResult.trusted`, no envelope at dispatch | `v2-S3` |

## **Explicitly Deferred**

Dense retrieval ([ADR-0014](./08-decisions/0014-defer-dense-retrieval.md)), AOI acting mode,
RHI Tier C (mutation search — dormant behind a funding trigger), A2A remote pilots, performance
sidecars, warm LSP, and the Conductor (`C0`) phase — the last of which is out of scope until
Phase 7 closes, because a Conductor scheduling against fictional zero-cost telemetry would be a
random-walk allocator.

## **Frozen Regression Signals**

Every PR holds or improves all of these. The test count is **monotonic** — it only rises.

| Signal | Baseline (2026-07-31) | Command |
| :--- | :--- | :--- |
| Tests | **127 passed** | `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q` |
| Type check | 0 errors, strict | `uv run pyright src/sagiha` |
| Lint | clean | `uv run ruff check && uv run ruff format --check` |
| Import contracts | **5/5** | `uv run lint-imports` |
| Event catalog | in sync (34 events) | `python scripts/gen_event_catalog.py --check` |
| Coverage | `fail_under = 80` | `pytest --cov=src/sagiha` |
| Replay | green | `uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json …` |

## **Commands Today vs Planned**

| Command | Availability |
| :--- | :--- |
| `sagiha version` | **Available now** |
| `sagiha run <goal> [--acceptance …]` | **Available now** (cassette or live) — reports `$0.00` until `v2-S1` |
| `sagiha replay <run_id> --verify` | **Available now** |
| `sagiha run --resume <run_id>` | **Available now** |
| `sagiha harvest [--repo …]` | **Available now** — numbers uninterpretable until `v2-S1` |
| `sagiha bench [--suite …] [--aa]` | **Available now** — numbers uninterpretable until `v2-S1` |
| `sagiha export --format sft\|dpo` | Planned — `v2-S4` |
| `sagiha init` | Planned — `v2-S6` |

## **Next Items, In Order**

1. **`v2-S0` (Phase 0)** — restore and re-baseline this page, ship the docs budget and link gates,
   demote rationale mass, fold the v2 corpus into `01`–`08`, record ADRs 0019–0023.
2. **`v2-S1` (Phase 1)** — H1–H4. Nothing downstream is measurable until this closes.
3. **`v2-S2` (Phase 2)** — port consolidation while every affected port still has ≤1 stub adapter.
4. **`v2-S3` (Phase 3)** — context engine and TaintGate, shipped together.

> **Standing rule.** This page is updated **the day a gate closes**, in the `v2-S` series, and it
> never makes a claim the delta audit contradicts. That is the review criterion for any edit here.
