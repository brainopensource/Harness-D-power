---
status: rationale
updated: 2026-07-31
retrieval: excluded
---
# Sprint v2-S4 — Measurement Re-Baseline, Best-of-N & Distillation Specification

**Basis (audited, cross-referenced):**
`i-want-to-implement-temporal-tarjan.md` (authoritative plan) ·
[development_plan_v2.md](development_plan_v2.md) ·
[refactor_sagiha_v2_guidelines.md §8](refactor_sagiha_v2_guidelines.md#8-phases-47--condensed-briefs) ·
[rhi-outer-loop.md](../04-workflows-and-loops/rhi-outer-loop.md) ·
[trace-distillation.md](../04-workflows-and-loops/trace-distillation.md) ·
[ADR-0005](../08-decisions/0005-best-of-n-not-mcts.md) ·
[ADR-0022](../08-decisions/0022-rhi-economic-refounding.md) ·
[ADR-0023](../08-decisions/0023-port-rent-rule.md)

---

## 1. Context & The H5 Honesty Defect

`docs/implementation/development_plan_v2.md` closes `v2-S3` and places `v2-S4` next: **harden the E0 measurement instrument, then ship Best-of-N against it — measurement strictly before the capability it measures.**

The exit gate is the project's first defensible external claim:
> *"BoN beats single-shot by X ± σ over a floor of Y."*

A line-level audit revealed that this claim is currently unmakeable due to **H5 — `src/sagiha/e0/statistics.py` fabricates its statistics** (same defect class as H1/H2):
- `p_value = 0.05` is a hardcoded literal (`statistics.py:42`).
- `confidence_interval = (0.0, delta * 1.5)` is invented arithmetic, not a CI (`:30`).
- `beats_noise_floor = delta > 0` **never consults the noise floor** (`:43`).
- `tests/unit/test_e0_statistics.py:44` currently pins that lie (`assert comp.beats_noise_floor is True` from a single-task delta).

Therefore, `v2-S4` proceeds strictly in sequence:
1. Make the instrument honest (**S4.0 / S4.1**).
2. Build the capability it measures (**S4.2 / S4.3**).
3. Harvest the byproduct (**S4.4**).

---

## 2. Core Decisions & Architectural Principles

1. **Delete `adapters/benchmark/` + `ports/benchmark.py` (Epic S4.0):** `e0/runner.py` imports `agency` and `composition`. The layers contract forbids `adapters → agency`, so the port's only legal adapter can never exist. ADR-0023's port-rent rule applies. **Port count 19 → 17.** New `src/sagiha/e0/protocols.py` defines agency-internal `TaskHarvester`, `SuiteRunner`, and `StatisticalTest` protocols (same pattern as `ExchangeCompactor`). Recorded in **ADR-0024** (`0024-e0-is-a-tool-not-a-port.md`).
2. **Pure-Stdlib Statistics, Zero Dependencies:** Rewritten `src/sagiha/e0/statistics.py` (~150 LOC) uses `math.comb` for exact two-sided McNemar binomial tests, a deterministic seeded percentile bootstrap for CIs (`random.Random(seed)`), and Holm–Bonferroni step-down correction. Replay determinism is preserved; scipy version drift is eliminated.
3. **One BoN Adapter, Two Launch Strategies (`launch_mode`):** `BestOfNSearch` in `adapters/search/best_of_n.py` implements `CandidateSearch` v2. `launch_mode` supports `sequential` (CPU default, running candidates one at a time in real worktrees) and `parallel` (GPU opt-in, using `anyio.create_task_group()` and `CapacityLimiter(min(governor, tier.max_concurrent_requests))`).
4. **Candidate Diversity (Load-Bearing):** Candidate $i$ is sampled at `candidate_temperatures[i % len(...)]` (default `(0.0, 0.6, 0.9)`). Diffs are hashed to compute `distinct_candidates` and `diversity_ratio = distinct / N`. Precondition on exit gate: `diversity_ratio` materially above $1/N$.
5. **Deterministic S-0 Composite Default:** `adapters/search/scoring.py` defaults to `w_pass·PassFraction − w_diff·ΔDiff` ($w_{\text{coverage}}$ and $w_{\text{suppression}}$ default to `0.0` so hard gates are not double-counted). `LocalJudgeScorer` ships OFF; `backend="learned"` raises `NotImplementedError("v2-S6+ — see ADR-0025")`. `select()` filters to the admitted set first, ranking within it (**proxies rank, never admit**). Recorded in **ADR-0025** (`0025-candidate-search-seams.md`).

---

## 3. Detailed Epic Breakdown

### Epic S4.0 — Resolve `e0/` vs `adapters/benchmark/` Duplication
- Delete `src/sagiha/adapters/benchmark/` and `src/sagiha/ports/benchmark.py` (removes H3-class stubs missed by PR-1.4).
- Add `src/sagiha/e0/protocols.py` for agency-internal runner/harvester seams.
- Add **ADR-0024** (`0024-e0-is-a-tool-not-a-port.md`). Update `docs/STATUS.md` (port count 19 → 17).

### Epic S4.1 — E0 Honesty (H5) + Harvester Validation
- **S4.1a (Real Statistics):** Rewrite `e0/statistics.py`. Mirror `GateReport` `None`-doctrine: absence of a verdict is never a pass (`ComparisonResult.beats_noise_floor: bool | None = None`). Fixture-backed tests in `tests/fixtures/statistics/*.json`.
- **S4.1b (Harvester Validation Gate):** `validate_task(task)` in `e0/harvester.py` allocates a scratch worktree at `base_commit`, checks out target test files, verifies `failing_test_cmd` fails, checks out source files, verifies clean pass, and runs determinism probe $k=3$.
- **S4.1c (Runner & Reporter Honesty):** `e0/runner.py` threads `task.base_commit`, records real cost, gate failure kinds, and cache hits. `e0/reporter.py` emits markdown and JSON reports. `tests_unmodified != 0` discards the run.
- **S4.1d (Pinned Suite & CI):** Commit `benchmarks/definitions/s0-core.json` (≥30 validated tasks). Add `bench-aa` CI job. Publish `docs/rationale/benchmarks/noise-floor.md`. Close **RC-7**.

### Epic S4.2 — Best-of-N over Real Worktrees
- **One Kernel per Active Candidate:** `composition.py` binds tool registry per worktree. `adapters/search/protocols.py` defines `CandidateExecutor` and `CandidateOutcome`.
- **`BestOfNSearch` (`adapters/search/best_of_n.py`):** Implements `CandidateSearch` v2 including `score()`.
- **Config & Profiles:** `SearchConfig` gains `launch_mode: Literal["sequential","parallel"]`, `stagger_s`, `cancel_on_clean_admit`, `n_policy`, `candidate_temperatures`. Two committed profiles: `sagiha.cpu.toml` and `sagiha.gpu.toml` (`OLLAMA_NUM_PARALLEL=2`).
- **Early Pruning & Sequential Repair:** `prune_on_first_gate_fail` releases worktree at first gate failure; `max_repair_rounds` re-enters failing output into worktree as revision $n+1$. Deterministic `should_escalate()` ladder.

### Epic S4.3 — Scoring Engine (S-0 Default, Seams)
- `DeterministicCompositeScorer` ($w_{\text{pass}}\cdot\text{PassFraction} - w_{\text{diff}}\cdot\Delta\text{Diff}$) active by default.
- `LocalJudgeScorer` (`backend="judge"`, shipped OFF) calls judge role (Ollama/Qwen). Config validator enforces `roles["scoring"] != roles["execution"]`.
- `backend="learned"` raises `NotImplementedError("v2-S6+")`. ADR-0025 documents seams.

### Epic S4.4 — Trace → Dataset Exporter
- `src/sagiha/outer_loop/export/` (`eligibility.py`). All 4 criteria required: `admitted`, `¬tainted`, `within_budget`, `replay_verified` (new `ReplayVerified` event).
- `ports/trajectory.py` `list_runs()` bump (PORT_VERSION 2 → 3). `sagiha replay <run_id> --verify` emits `ReplayVerified`.
- `sft.py` (reconstructs prompt via `ContextAssembler.from_trajectory`), `dpo.py` (groups siblings by `parent_task_id` + `stable_prefix_digest`), `redaction.py`, `license.py`, `schema.py`. CLI `sagiha export`.

---

## 4. The Scope Fence (Deliberately Deferred)

To keep the kernel lightweight and zero-dependency in `v2-S4`, these target capabilities are fenced until their explicit triggers:

| Deferred Capability | Target Sprint | Explicit Trigger |
| :--- | :--- | :--- |
| **Numba JIT** for AST traversal & PageRank | **v2-S6** | Requires Tree-sitter code graph and AST chunking to exist first. |
| **CUDA / FlashAttention-2 / vLLM serving** | **v2-S5 / v2-S7** | Serving infrastructure belongs behind container runtime boundary. |
| **Learned Scorers** (XGBoost / LightGBM) | **Post-v2-S6** | Requires 50–100 labeled traces produced by v2-S4 export. |
| **Calibrated PRM / Tree Search** | Trigger-gated | ADR-0005 reversal condition: demonstrated AUC + tree search beating BoN beyond floor at equal cost. |
| **RHI Tier C** (Mutation Search) | Dormant | ADR-0022 trigger: explicit funding against a named hypothesis. |

---

## 5. PR Execution Sequence

```
┌──────┬───────────────────────────────────────────────────────────────────────┐
│  PR  │                               Contents                                │
├──────┼───────────────────────────────────────────────────────────────────────┤
│ 4.0  │ Duplication resolution + e0/protocols.py + ADR-0024                   │
│ 4.1a │ Statistics honesty (H5) + fixtures + inverted tests                   │
│ 4.1b │ Harvester validation + runner base_commit/cost + reporter template    │
│ 4.1c │ Pinned suite + bench-aa CI job + noise-floor + RC-7                   │
│ 4.2a │ Worktree hardening + RunLoop(branch_id=)                              │
│ 4.2b │ BestOfNSearch sequential + composition wiring + events                │
│ 4.2c │ Parallel mode + inference-capacity limiter + cpu/gpu profiles + probe │
│ 4.2d │ Candidate temperature ladder + diff-digest dedup + diversity_ratio    │
│ 4.3  │ Scoring S-0 + judge (off) + rank-never-admit contract test + ADR-0025 │
│ 4.4a │ list_runs port bump + replay-verify fix + ReplayVerified event        │
│ 4.4b │ Exporter + CLI + hygiene gates                                        │
│ 4.5  │ STATUS/docs/ADR closeout, RC-5/RC-6                                   │
└──────┴───────────────────────────────────────────────────────────────────────┘
```

**Standing Rule:** Proving test first (must fail against branch point), then implementation, then all seven verification signals. Monotonic baseline test count from **192**.

---

## 6. Exit Gate Verification & Honest-Negative Clause

```bash
# S4.1 — The Instrument
uv run sagiha harvest --repo . --validate --min-tasks 30 --output benchmarks/definitions/s0-core.json
uv run sagiha bench --suite benchmarks/definitions/s0-core.json --aa --runs 2 \
    --output docs/rationale/benchmarks/noise-floor.md

# S4.2 / S4.3 — The Capability
uv run sagiha bench --suite benchmarks/definitions/s0-core.json --runs 3 \
    --compare single_shot,bon --output docs/rationale/benchmarks/s4_bon_delta.md

# S4.4 — The Byproduct
uv run sagiha replay <run_id> --verify --cassette …
uv run sagiha export --format sft --out data/sft/ && uv run sagiha export --format dpo --out data/dpo/

# Seven Signals
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q     # ≥ 192, monotonic
uv run pyright src/sagiha && uv run ruff check && uv run ruff format --check
uv run lint-imports && uv run python scripts/gen_event_catalog.py --check
uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json …
```

### Pass Conditions
- $\ge 30$ validated tasks, **zero** unclean reverts, zero flaky tasks admitted.
- A/A noise floor published with a stated bootstrap confidence interval, measured under the **same `launch_mode`** as the treatment run.
- BoN delta published as $X \pm \sigma$ against the floor, Holm-corrected, $k \ge 3$.
- **Cost-normalized comparison:** Publish **cost-per-resolved-task** alongside pass rate. A pass-rate win at a cost-per-resolved-task loss is reported as a cost loss, not a win.
- **`diversity_ratio` materially above $1/N$:** Validity precondition ensuring candidates are distinct solutions.
- `tests_unmodified` failure count **0** across every bench run (zero grader edits).
- Parallel contention probe green; zero leaked worktrees.
- `sagiha export` emits schema-valid SFT and DPO JSONL; taint-canary run excluded with explicit ledger reason.

**Honest-Negative Clause:** If BoN does not beat single-shot beyond the floor — or wins on pass rate but loses on cost-per-resolved-task — publish the number and ship BoN **off by default** (`search.enabled = false`). The Protocol and adapter stay; the default does not.
