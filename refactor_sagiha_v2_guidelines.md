# SAGIHA v2 — Refactor & Improvement Guidelines

**Audience:** the senior developer (or coding agent) who will execute the v2 re-baseline.
**Status:** execution guide. Synthesises `docs/reviews/{critical_gaps_analysis,next_gen_architecture_specs,codebase_delta_refactor,agi_evolution_path}.md` and `docs/implementation/development_plan_v2.md` into an ordered, verifiable sequence.
**Baseline audited:** `main` @ `a1ea590`, `src/sagiha` ~5.7k LOC / 84 files, **127/127 tests passing** (re-verified during this write: `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q` → `127 passed in 0.96s`).

> Read §1–§3 before touching anything. Then work §4 onward in order. Every claim about current behaviour in this document carries a `file:line` anchor and was verified against the tree, not copied from a review.

---

## 1. The thesis, in one paragraph

The v2 corpus does not change where SAGIHA is going — same four properties, same L0→L4 ladder, same eighteen ADRs. It changes what must be true before the next capability ships. A line-level audit found that **three of four coding gates are hardcoded `True`, budget accounting is dead code, `syntax_valid` is a constant, and Block-5 stubs return fabricated success**. Every measurement taken over those instruments — every "gated" claim, every bench number, every cost figure — is uninterpretable. So the order is: **make the instruments honest, consolidate the contract surface while it is still cheap, then build the context and safety engine everything downstream stands on.** Capability work (Best-of-N, sandbox, retrieval, Story-DAG) resumes only after those three are done, and each ships against a measurement that existed before it.

Two second-order rules follow, and they are the ones most likely to be violated under pressure:

1. **Bench pass-rates will fall when the gates stop lying.** That fall is the deliverable. Publish before/after numbers in the same PR, or the next reader reverts your fix as a regression.
2. **Honest negatives ship.** An ablation that fails becomes a published number and a shelved feature — not a retry with a friendlier prompt.

---

## 2. Verified baseline — do not re-derive this

### 2.1 The honesty defects (H-series)

| ID | Defect | Verified at |
| :-- | :--- | :--- |
| **H1** | `GateEvaluator.evaluate()` returns `no_new_suppressions=True, tests_unmodified=True, coverage_not_decreased=True, diff_within_bounds=True` unconditionally. `tests_unmodified` — the gate the T3 evaluation-capture threat model rests on, the one `Config` refuses to let you disable — is a literal. | `src/sagiha/outer_loop/evaluator/gate_evaluator.py:75-81` |
| **H2** | `record_spend()` is implemented and correct but **called from nowhere in `src/`**. `remaining_budget()` therefore always returns the full budget and the loop's budget break at `run_loop.py:163-174` is unreachable. The loop emits `TokenUsage(0,0)` / `CostSummary(usd=0.0)` on every step. | `kernel/governor.py:30-36` (no callers) · `agency/run_loop.py:206-214`, `:291-303` |
| **H2b** | *Not in the review corpus.* `DefaultResourceGovernor.acquire()` mints a lease and stores it — it enforces neither `max_concurrent_sandboxes` nor the spend limit. Both constructor args are stored and never read in `acquire`. | `kernel/governor.py:21-25` |
| **H3** | `ContainerSandbox.apply_edit()` returns `EditResult(hunks=(HunkResult(applied=True,…),), syntax_valid=True)` without touching anything; `write()` is `pass`; `MCPClientDriver.invoke_tool()` returns `""`. A stub that lies is worse than an absent adapter. | `adapters/sandbox/container.py` · `adapters/mcp/driver.py` |
| **H4** | `LocalWorkspace.apply_edit` hardcodes `syntax_valid=True` on **both** the success and failure paths, while the tool catalog normatively promises a structural check before write. | `adapters/workspace/local.py` (both branches of the `for…else`) |

### 2.2 Structural defects folded into the plan

| Defect | Verified at |
| :--- | :--- |
| `apply_edit` handler strips an `app/` prefix **after** the PolicyEngine authorized the original path string — the authorized path and the effected path differ. Grant-scope integrity violation, small but real. | `adapters/tools/builtins.py:99-102` |
| Tool schemas exist in two places and have already drifted: `composition.py`'s hand-written literal omits `expected_occurrences` on `apply_edit`, omits `offset`/`limit` on `read_file`, and carries no `x-sagiha-path` markers at all. | `composition.py:100-151` vs `builtins.py:12-66` |
| `Kernel.workspace` is typed as the concrete `LocalWorkspace`, not the `Workspace` port. | `composition.py:48` |
| `agency` constructs a TCB object: `RunLoop.__init__` defaults `evaluator` to a freshly built `GateEvaluator`. | `agency/run_loop.py:93` |
| `ModelRequest` assembly is inline in the loop body; there is no `agency/context/` package. | `agency/run_loop.py:184-189` |
| `_reconstruct_history` drops assistant text-only turns (steps persist only `tool_calls`/`tool_results`), so a resumed run's request digest can never match a recorded one. | `agency/run_loop.py:101-133` |
| `apply_edit` is registered `IDEMPOTENT`; re-applying a landed search/replace yields `anchor_not_found`, not convergence. Replay is currently *permitted* to re-run it. | `adapters/tools/builtins.py:147-153` |
| `ports/` holds **24 Protocols across 20 files** — not 21. The consolidation target must be restated against the real count (see §6.1). | `grep -rn "(Protocol)" src/sagiha/ports/` |
| `e0/` (real: harvester, runner, statistics, reporter) and `adapters/benchmark/` (stubs) are two parallel implementations of the same idea. | `src/sagiha/e0/` vs `adapters/benchmark/` |

### 2.3 Two docs findings the review corpus does not account for

**A. `docs/STATUS.md` does not exist.** It was deleted in `2b80840 "docs: folder organization"`. Sprint S0.5 in `development_plan_v2.md` says "rewrite `docs/STATUS.md`" — as written that task is impossible, because there is nothing to rewrite. It must be **restored first** (`git show 2b80840^:docs/STATUS.md`), then rewritten. This blocks more than itself: `docs/README.md` links to `./STATUS.md` **four times** (sitemap row, Start Here item 1, Build Readiness ×2), `docs/reviews/README.md` twice more, and every downstream sprint has an "update STATUS the day the gate closes" standing rule pointing at a dead file.

**B. The 15,000-word normative ceiling is a 3.6× overshoot, not a trim.**

| Scope | Files | Words |
| :--- | ---: | ---: |
| Whole `docs/` tree | 110 | 184,054 |
| Tagged `status: normative` | 69 | **53,989** |
| S0.1 ceiling | — | 15,000 |

Additionally: **23 files carry no `status:` key at all** (all of `sprints/`, 5 reviews, all 4 `reference/harness_examples/`, `implementation/development_plan_v2.md`), and **10 files use `draft` or `advisory`** — values `docs/README.md` does not declare in its taxonomy. `docs/README.md` asserts "Every file declares `status:` in front matter"; that is false for 21% of the tree. S0.1 as written ("inventory and demote") understates the work by an order of magnitude. §4.3 gives the arithmetic that actually closes the gap.

### 2.4 Frozen regression numbers

Every PR must hold or improve all five:

| Signal | Baseline | Command |
| :--- | :--- | :--- |
| Tests | **127 passed** (monotonic — count only rises) | `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q` |
| Type check | 0 errors, strict | `uv run pyright src/sagiha` |
| Lint | clean | `uv run ruff check && uv run ruff format --check` |
| Import contracts | **5/5** (`car-layering`, `ports-are-pure`, `domain-is-pure`, `tcb-isolation`, `layers`) | `uv run lint-imports` |
| Event catalog | in sync | `python scripts/gen_event_catalog.py --check` |
| Replay | green | `uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json …` |
| Coverage | `fail_under = 80` (currently ~89%) | `pytest --cov=src/sagiha` |

> **Known environment trap:** the suite passes under Python 3.12 despite the `requires-python >= 3.13` pin (ADR-0009 binds 3.13). Either the pin is doing no work or CI's 3.13 masks a latent 3.12 incompatibility. Pick deliberately — see §11.
>
> **Known CI trap:** the replay job passes `--workspace tests/fixtures/replay_smoke/workspace`, which is not a tracked path. Verify the job actually exercises what it claims before you trust it as a gate.

---

## 3. Execution model

**Shape:** one coder agent, working sequentially on a branch off `main`, **one PR per epic**, human review at each phase exit gate. This matches the corpus's own "regression protocol per phase" rule and respects the hard sequencing dependency (H1 → H2 → everything else).

**Per-PR protocol.** Every PR, without exception:

1. Write the proving test **first** — it must fail against `main`.
2. Make the change.
3. Run all seven signals in §2.4. Test count must not fall.
4. State in the PR body: what got more honest, and what number moved as a result.

**Parallel-safety.** If you later fan work out, these files are contention hotspots and their epics must stay serialized:

- `agency/run_loop.py` — touched by S1.1, S1.2, S2.5, S3.1, S3.4
- `composition.py` — touched by S1.2, S2.3, S2.4, S3.3
- `domain/config.py` — touched by S1.2, S2.4, S3.2
- `domain/events.py` — touched by S3.2, S3.3, S3.4 (each addition forces a catalog regen)

Genuinely parallel-safe leaves: S1.3 (`workspace/local.py`), S1.4 (three stub adapters), S2.1 (port deletions), PR-0b (scripts).

**TCB rule — absolute.** `src/sagiha/kernel/policy/` and `src/sagiha/outer_loop/evaluator/` are Trusted Computing Base. The `tcb-isolation` import contract protects them structurally, and `.github/workflows/ci.yml`'s `tcb-check` job hard-fails any diff touching them authored by `sagiha-agent`. A human authors every TCB change in this plan (S1.1, S2.2, S3.3 all land there). An agent may *propose* the diff; it may not be the commit author.

---

## 4. Phase 0 — Docs, governance, and the SSOT

**Scope:** `docs/` and `scripts/` only. **Zero `src/` changes.** One short phase — this is the cheapest-leverage work in the plan and must not balloon.
**Why first:** without it, every later sprint re-litigates decisions against 54k words of partially superseded prose, and the agent maintaining this repo retrieves contradictions.

### PR-0a — Restore `docs/STATUS.md` and repair dead links  *(do this before anything else)*

```bash
git show 2b80840^:docs/STATUS.md > docs/STATUS.md
```

Then rewrite it for the v2 series:

- Sprint series relabelled `v2-S0 … v2-S7` (historical sprints 1–3b are closed under the old numbering; the prefix prevents collision).
- **Honest capability table.** Coding gates listed as *fabricated until v2-S1* per H1. Cost telemetry listed as *fictional until v2-S1* per H2. Blocks 2–5 relabelled "scaffolding present / capability pending" — module shells, ports, and CLI stubs are not delivered capability.
- STATUS makes **no claim the delta audit contradicts.** That is the review criterion.

Repair the seven known dead links: `docs/README.md` ×4 → `./STATUS.md`; `docs/reviews/README.md` ×2 → `../STATUS.md`; `docs/README.md` sitemap → `implementation/development-plan-and-prompts.md`, which now lives only under `implementation/_archive/`.

**Exit:** `docs/STATUS.md` exists; zero dead relative links in `docs/` (verify by hand this PR, mechanically from PR-0b onward).

### PR-0b — Budget and link-check scripts, CI-wired

Neither exists today. `scripts/` currently contains exactly two files (`gen_event_catalog.py`, `gen_replay_fixture.py`).

- `scripts/docs_budget.py` — walks `docs/`, parses frontmatter, emits per-directory and per-file word counts, and fails non-zero when the sum over `status: normative` files exceeds a ceiling passed as `--max`. Report format should be committable into `docs/STATUS.md`.
- `scripts/check_links.py` — resolves every relative markdown link in `docs/`; fails on any that does not resolve.

Wire both as a `docs-budget` job in `.github/workflows/ci.yml`. **Set `--max` to the current measured normative total in this PR** so the gate is green on merge, then ratchet it down in PR-0c. A gate that lands red is a gate that gets disabled.

### PR-0c — The demotion program (54k → ≤15k)

This is the real work of Phase 0. Create `docs/rationale/`, add a `retrieval: excluded` frontmatter key (documented in `docs/README.md`, honored by the future indexer at v2-S6), and move:

| Move to `docs/rationale/` | Files | Words |
| :--- | ---: | ---: |
| `reviews/done/` (historical record) | 5 | 34,531 |
| `reference/` (long-form derivations) | 5 | 27,753 |
| `reference/harness_examples/` (competitor teardowns) | 4 | 14,736 |
| `frontend/` (no consumer until v2-S7's TUI) | 6 | 9,020 |
| `sprints/` incl. all seven `sprint-fe-*` | 10 | 8,275 |
| `implementation/_archive/` | 3 | 6,256 |
| `reviews/` top-level v2 corpus (mark `historical` — normative copy lives in 01–08 after PR-0d) | 5 | ~19,700 |

Then, from what remains in `01`–`08`: demote `02-architecture/performance-sidecars.md`, `05-tech-stack/aoi-coprocessors.md`, and any long-form derivation an ADR already states. **ADRs are exempt from the budget** — they are cheap and high-value.

Also in this PR:

- Backfill `status:` on the 23 files missing it.
- Collapse the undocumented `draft` / `advisory` values into the declared taxonomy (`normative` / `rationale` / `historical`), or amend `docs/README.md` to declare them. Do not leave both broken.
- Resolve the half-applied review kanban: six review files sit loose at `docs/reviews/` top level while `todo/` is empty and `doing/` holds one file. Pick one convention.
- `docs/frontend/`, `docs/sprints/`, and `docs/07-roadmap/` are missing from or stale in the README sitemap — regenerate it.
- Ratchet `docs_budget.py --max` down to 15000 (or to the number §11 settles on).

**Adopt the standing docs-shrink rule:** a PR adding N normative words deletes N elsewhere. ADRs exempt.

### PR-0d — Fold the v2 corpus into normative SSOT (no duplication)

Each amendment is a paragraph, cites the review doc it implements, and the review doc is then marked `historical`. One normative copy, in `01`–`08` only.

- `02-architecture/context-and-cache-engineering.md` + `prompt-architecture.md` — **the seed-only Layer 6 ruling**: pre-assembled retrieval is computed once at task start and never refreshed mid-task; all subsequent retrieval is agentic and tail-resident. **R9 superseded** by exchange-granular, token-budgeted compaction (`keep_first_exchanges=2`, `keep_last_tokens=24_000`, headroom 20%).
- `02-architecture/security-and-threat-model.md` — TaintGate v1 as **T7**: monotonic taint, propagation into summaries and anchored state, mutation-approval rule.
- `04-workflows-and-loops/rhi-outer-loop.md` — Tier A/B/C economic re-founding; Tier C (mutation search) dormant behind an explicit funding trigger.
- New `03-contracts-and-models/frozen-run-state.md` — schema pointer into `src/`, grants-absent invariant.
- New `04-workflows-and-loops/trace-distillation.md` — exporter spec pointer.

### PR-0e — Decision records

ADR-0019 through ADR-0023, continuing cleanly from the existing 0001–0018 (all `Accepted`, no gaps). **Every ADR carries reversal conditions.**

| ADR | Subject |
| :-- | :--- |
| 0019 | Port consolidation (deletions, `Advisory` merge, re-promotion conditions) |
| 0020 | Per-invocation effect classification + PURE allowlist placement in the TCB |
| 0021 | Seed-only Layer-6 retrieval |
| 0022 | RHI economic re-founding (Tier A/B scheduled, Tier C trigger-gated) |
| 0023 | Port-rent rule — zero non-test adapters for two consecutive blocks ⇒ automatic demotion to `experimental` and deletion review |

Note the existing ADRs carry status in **two** places (frontmatter `status:` and a body `**Status**: Accepted` line). Pick one and normalise, or the next audit flags it.

**Phase 0 exit gate:** normative word count ≤ ceiling in CI · zero dead links · `docs/STATUS.md` restored and re-baselined · ADRs 0019–0023 merged. **No `src/` PR merges before this gate.** One phase of doc discipline buys every later phase an uncontested spec.

---

## 5. Phase 1 — Instrument honesty

**Objective:** every number the system reports becomes true. This is the hard prerequisite for all measurement.
**Sequencing:** S1.1 and S1.2 land **before** anything else in `src/`. S1.3 and S1.4 are parallel-safe leaves and may land in any order.

### PR-1.1 — Real gates (H1) · *TCB, human-authored*

**Files:** `outer_loop/evaluator/gate_evaluator.py` · `domain/control.py` · `domain/work.py` · `agency/run_loop.py`

Prerequisite plumbing (both additive, non-breaking — `RunContext` is a frozen model, the new field defaults):

1. `RunContext.base_commit: str | None = None` in `domain/control.py`.
2. `RunLoop` calls `workspace.checkpoint("run-start")` before step 1 and threads the sha through `RunContext`.

Then replace the four literals at `gate_evaluator.py:75-81`. Every check runs through the existing `dispatch()` path — same choke point the criteria checks already use (`gate_evaluator.py:46-59`), so no new authority path is created:

| Gate | Implementation |
| :--- | :--- |
| `tests_unmodified` | `git diff --name-only <base_ref> -- tests/` → gate passes iff output empty. Constructor gains `test_paths: tuple[str, ...] = ("tests/",)` and `base_ref`. |
| `diff_within_bounds` | `git diff --numstat <base_ref>` → sum adds+dels ≤ `GatesConfig.max_diff_lines` (exists, `domain/config.py`, default 1000). |
| `no_new_suppressions` | `git diff <base_ref> -U0`, scan **added lines only** for `(# type: ignore\|# noqa\|# pragma: no cover\|pytest.mark.skip)` → gate passes iff zero new matches. |
| `coverage_not_decreased` | The one gate that legitimately cannot be honest yet (no `Toolchain` adapter, no baseline). Set honest **`None`**, gated by the existing `GatesConfig.require_coverage_not_decreased`. |

Because `GateReport.admitted` correctly refuses `None`, honest `None` needs a companion: add **`GateReport.required_gates: frozenset[str]`** (`domain/work.py`, default = the current four) so `admitted` computes over the *evaluable* set instead of hardcoded field names. Emit per-gate results as `CriterionResult`-style entries so the E0 reporter can attribute failures.

**Proving tests** (extend `tests/unit/test_sprint3a_e2e.py`):
- A run that edits any file under `tests/` yields `tests_unmodified=False` **and** `admitted=False`.
- A run whose diff exceeds `max_diff_lines` fails `diff_within_bounds`.
- A run adding `# type: ignore` fails `no_new_suppressions`.

### PR-1.2 — Live budget and cost telemetry (H2 + H2b)

**Files:** `ports/model.py` · `domain/trajectory.py` · `domain/config.py` · `adapters/model/openai.py` · `adapters/model/cassette.py` · `agency/run_loop.py` · `kernel/governor.py` · `scripts/migrate_cassettes_v2.py` (new)

1. **`ModelProvider` → v2.** `complete()` returns `Completion(message: Message, usage: TokenUsage, model: str)` instead of a bare `Message`. Bump `PORT_VERSION` to 2 with a one-line migration note (the port is `provisional`; the policy permits this).
   *Rejected alternative, recorded so it is not re-proposed:* adding `usage` to `Message`. Usage is a property of the **call**, not the message, and it would leak into history and cassette digests.
2. **`adapters/model/openai.py`** already receives `response.usage.prompt_tokens` / `completion_tokens` and drops them. Populate `usage`.
3. **Cassette migration.** `scripts/migrate_cassettes_v2.py` wraps recorded messages, `usage=TokenUsage(0,0)` for legacy entries. Replay determinism is unaffected because digests hash the **request**. Migrate `tests/fixtures/replay_smoke/cassette.json` **in this same PR** or CI's replay job goes red.
4. **`PricingConfig`** in `domain/config.py` — per-tier `usd_per_1m_input` / `usd_per_1m_output`, default `0.0` for local tiers. Thread through `composition.py`.
5. **`agency/run_loop.py`** — replace the zeroed literals at `:206-214` and `:291-303` with real `TokenUsage` / `CostSummary`; call `await self._governor.record_spend(ctx.run_id, cost_usd)` after each completion. The `remaining_budget <= 0` break at `:163-174` becomes reachable for the first time.
6. **`kernel/governor.py`** — enforce what the constructor already accepts: `max_concurrent_sandboxes` in `acquire()` for `kind="sandbox"` (H2b — currently stored and never read), plus `max_wall_clock_s` and step-token ceilings from `GovernorConfig` (fields exist, unenforced).
7. **Fix the stuck-break hazard.** When `stuck` triggers mid-`tool_use_blocks` (`run_loop.py:230-233`), the assistant message with unanswered `tool_use` blocks is already in `history`. Append synthetic `is_error=True` `ToolResultBlock`s for the skipped calls **before** breaking, so a later resume reconstructs provider-valid history.

**Proving tests:** unit — a governor with a `$0.01` cap aborts at step 2 via the now-reachable budget break. Live smoke — the ledger lands within 5% of provider-reported usage.

### PR-1.3 — Real `syntax_valid` (H4) · *parallel-safe*

**File:** `adapters/workspace/local.py`

In `apply_edit`, before the final `write_text`: if `target.suffix == ".py"`, run `ast.parse(text)`. On `SyntaxError` — **do not write** — return `EditResult(hunks=…applied=False, reason=f"syntax_error:{e.lineno}", syntax_valid=False)`. Non-Python files keep `syntax_valid=True`; no claim is being made there.

Use stdlib `ast`, not Tree-sitter. Tree-sitter is the Block-4 multi-language upgrade, not a prerequisite for honesty.

**Proving test:** a broken edit leaves the file on disk byte-identical, and the model receives the failing line number in the result.

### PR-1.4 — Stubs fail loud (H3) · *parallel-safe*

**Files:** `adapters/sandbox/container.py` · `adapters/mcp/driver.py` · `adapters/telemetry/otel.py`

Every unimplemented method body becomes `raise NotImplementedError("v2-S5 — see docs/STATUS.md")`. Keep the files; placement is correct and `tests/unit/test_block5_scaffolding.py` pins their existence. **Invert that test** to assert the methods raise.

Exception: `MCPClientDriver.list_tools()` returning `[]` may keep its shape — empty discovery is a truthful null. `invoke_tool()` returning `""` may not.

Add a grep gate to CI: no stub returns a success-shaped literal.

### PR-1.5 — Honest re-measure

Run `sagiha harvest` + `sagiha bench --aa` **before** merging PR-1.1 and **again after** PR-1.4. Commit both reports to `docs/rationale/benchmarks/`. Update `docs/STATUS.md` with the post-honesty baseline **and an explicit note that the drop is the fix.**

**Phase 1 exit gate:** ≥127 tests green · replay green post-cassette-migration · live smoke shows non-zero cost telemetry · gate-dishonesty e2e tests in CI · A/A noise floor re-measured on honest gates.

---

## 6. Phase 2 — Port consolidation & kernel corrections

**Objective:** lock the v2 contract surface **before** Phase 4 writes real consumers against the old one. Every break here is on a `provisional` port with ≤1 stub adapter — the cheapest they will ever be.

### 6.1 PR-2.1 — Deletions and merge (ADR-0019)

**Restate the target.** The corpus says "21 → 15"; the tree holds **24 Protocols across 20 files**. Recount in the PR and state the real number in ADR-0019, or the exit gate is unverifiable.

`tests/contracts/test_port_shape.py` enumerates ports **dynamically** via `pkgutil` + `importlib`, so file deletions self-heal the shape suite — no test edits needed for removals. None of the deleted Protocols is imported by `composition.py`, `run_loop.py`, `dispatch.py`, or any adapter; deletion breaks no execution flow.

| Action | Detail |
| :--- | :--- |
| **Delete** `ports/reviewer.py` | Zero adapters, zero external imports. Semantics (frontier judge ≠ generator, soft-score-never-gates) move to `ports/search.py` and the new `score()` method. `domain/work.py::ReviewReport` **stays** — it becomes `score()`'s return type. |
| **Delete** `ports/embedding.py` | Zero adapters, zero importers. ADR-0014 already defers the dense tier; re-create the Protocol *inside* the future dense adapter when the recall@10 trigger fires. Record the re-promotion condition in ADR-0019. |
| **Edit** `ports/memory.py` | Delete the `ShortTermMemory` Protocol (`:17`). Its adapter was removed under R7; the Protocol is a contract with no implementation and no consumer. Remove the now-unused `TrajectoryStep` import. `Memory` stays. |
| **Rewrite** `ports/advisory.py` | Three Protocols → one. `Advisory.predict(kind: PredictionKind, task, branch_id) -> Prediction`; `PredictionKind = Literal["reward","failure","cost_performance"]` in `domain/work.py`. `PORT_VERSION = 2`. Zero adapters, zero call sites — no breakage possible. |
| **Keep** `ports/meta_improver.py` | Dormant per the Tier-C ruling. It costs 22 LOC; the rent rule (ADR-0023) governs it. |

**Verification:** `tests/contracts/test_port_shape.py` green · `grep` proves zero dangling imports · port count matches the restated target.

### 6.2 PR-2.2 — PURE argv allowlist (ADR-0020) · *TCB, human-authored*

**New file:** `src/sagiha/kernel/policy/effects.py` — placed here deliberately: the `tcb-isolation` contract already forbids `agency`/`aoi`/`adapters` imports from `kernel.policy`, so the allowlist becomes agent-unwritable for free, with no new mechanism.

```python
PURE_ARGV: Final[frozenset[str]] = frozenset({"ls", "cat", "head", "tail", "wc", "git"})
PURE_GIT_OPS: Final[frozenset[str]] = frozenset({"status", "diff", "log", "show", "blame"})
MUTATION_TOOLS: Final[frozenset[str]] = frozenset({"apply_edit", "write_file", "run_command"})

def classify_command(argv: Sequence[str], declared: EffectClass) -> EffectClass:
    """Narrow run_command's declared DESTRUCTIVE to PURE for allowlisted read-only argv.
    NEVER widens. Anything unmatched keeps `declared`. `bash -lc` is never narrowed."""
```

**Wiring.** `DefaultToolRegistry.dispatch` is the wrong place — adapters are not TCB. Instead `agency/run_loop.py` and `GateEvaluator` construct `ToolCall.effect` via `classify_command(args["command"], registry_effect)` when `tool_name == "run_command"`. `ToolCall.effect` is already recorded per-call in the trajectory, so **replay needs zero changes** — it reads the recorded per-call class and simply starts re-executing the newly-PURE majority. `ToolRegistry` gains `effect_for_call(call_args) -> EffectClass` as the extension seam (`PORT_VERSION = 2`), defaulting to `get_effect_class` + `classify_command`.

**Proving cassette:** record `["git","status"]` and `["rm","x"]`; `replay --verify` must re-execute the first and serve the second from the recording.
**Exit metric:** ≥60% of steps re-executed under `replay --verify` on the pinned suite.

### 6.3 PR-2.3 — Builtins corrected

**File:** `adapters/tools/builtins.py`

- **Delete the `app/` path-strip hack** (`:99-102`). The grant is minted for the pre-stripped path and the handler then mutates a different one. Fix the fixture repo instead; do not carry a benchmark-specific rewrite in the production tool path.
- **Add `write_file(path, content) -> EditResult`**, `EffectClass.DESTRUCTIVE`, `x-sagiha-path` on `path`. The catalog specifies it and today the agent **cannot create a file** (`apply_edit` → `read_text` on a missing path → error).
- **Reclassify `apply_edit` → `DESTRUCTIVE`** (currently `IDEMPOTENT` at `:147-153`). Under the current class, replay is permitted to re-run it — a live correctness bug the moment PR-2.2 makes `replay --verify` re-execute idempotent calls.
- `list_dir` / `grep` return `str(list)`. Switch to `model_dump_json` of the `DirEntry` / `Match` models that already exist in `domain/content.py` and are currently unused.

### 6.4 PR-2.4 — Composition and config hardening

**Files:** `composition.py` · `domain/config.py`

- **Delete the hand-written `tool_schemas` literal** (`composition.py:100-151`) and derive from `BUILTIN_SCHEMAS`, using `sorted()` for canonical alphabetical order — the prompt-architecture doc makes that a cache-stability requirement. This kills the confirmed drift and makes `builtins.py` the single source.
- **`Kernel.workspace: LocalWorkspace` → `Workspace`** (`:48`). Nothing accesses `LocalWorkspace`-only members through the kernel; `workspace.root` is used only inside `builtins.py`, which receives the concrete instance directly at registration — acceptable, that *is* the adapter layer.
- **Judge-separation refusal.** Extend the existing `@model_validator` on `Config` (`domain/config.py:363-380`, which already refuses three insecure states): if `search.enabled` **and** `model.roles["judge"]` resolves to the same `(provider, model)` tuple as `roles["execution"]` → `ValueError`. Additive.
- **New config fields:** `SearchConfig.prune_on_first_gate_fail: bool = True`; `ContextConfig` gains `keep_first_exchanges: int = 2` and `keep_last_tokens: int = 24_000`, and `compact_at_headroom` moves `0.15 → 0.20` to align with the amended R9 default.
- Thread `PricingConfig` (PR-1.2) and `trusted_output` flags (PR-3.3) through registration.
- Consider moving the `GateEvaluator` construction out of `RunLoop.__init__` (`run_loop.py:93`) — agency should not construct a TCB object. Composition already builds one at `composition.py:207`; make it required, not defaulted.

**Proving test:** a same-model judge config fails at load.

### 6.5 PR-2.5 — Trajectory completeness for resume/replay/export

**Files:** `domain/trajectory.py` · `domain/upcasters.py` · `adapters/trajectory/sqlite.py` · `agency/run_loop.py`

Persist the full assistant `Message` on `TrajectoryStep` (schema addition + upcaster following the existing `domain/upcasters.py` pattern) so `_reconstruct_history` stops dropping text-only turns and resumed digests can match. This is also exactly what the v2-S4 dataset exporter needs — do it once, here.

**Proving test:** freeze → kill → resume → replay round-trip with a text-turn-bearing cassette.

**Phase 2 exit gate:** port count at the restated target · three v2 bumps merged with migration notes · `lint-imports` 5/5 and `pyright` 0 sustained · resume/replay round-trip green · ADR-0019/0020 marked Accepted-Implemented.

---

## 7. Phase 3 — Context engine & safety

**Objective:** long runs stop dying at the window edge, and untrusted content stops being a silent write path. **These ship together** — taint must propagate *through* compaction, or the compactor launders it.
**This is the corpus's action-plan #1.** Nothing in Phases 4–7 produces trustworthy long-horizon numbers without it.

### 7.1 PR-3.1 — `ContextAssembler`

**New package:** `src/sagiha/agency/context/` (does not exist today — prompt assembly is inline at `run_loop.py:184-189`).

```python
class AssembledPrompt(BaseModel):
    request: ModelRequest
    prefix_digest: str      # layers 1–7 hash — the cache-stability regression signal
    tail_tokens: int

class ContextAssembler:
    def __init__(self, *, system_prompt: str, tool_schemas: tuple[ToolSchema, ...],
                 task: TaskSpec,
                 retrieval_seed: tuple[RetrievalHit, ...] = (),   # Layer 6: set once, frozen
                 config: ContextConfig) -> None: ...
    def append_exchange(self, assistant: Message, results: tuple[Message, ...]) -> None: ...
    def anchored(self) -> AnchoredState: ...   # plan, open-file set, unresolved diagnostics
    def assemble(self, role: str) -> AssembledPrompt: ...   # checks compaction pre-assembly
```

**Seed-only is enforced by shape, not by discipline:** the retrieval seed is accepted *only at construction*, and there is no public post-construction method taking a `RetrievalHit`. `RunLoop` delegates its inline `history` list and `ModelRequest` construction here; `_reconstruct_history` moves in as `ContextAssembler.from_trajectory(...)`. Tool schemas consume the canonical sorted order from PR-2.4.

**Verification:** contract test asserts no public method accepts `RetrievalHit` post-construction; e2e asserts `prefix_digest` is constant across steps.

### 7.2 PR-3.2 — `ExchangeCompactor`

**File:** `src/sagiha/agency/context/compactor.py`

The unit of compaction is the **exchange** — one assistant message plus all its paired `tool_result`s and any signed reasoning block. Boundaries never fall inside one, so provider block-pairing is preserved **by construction**. This is the fix for the R9 spec's two latent structural bugs (turn-count policies have unbounded token variance; summarising across a `tool_use`/`tool_result` pair produces provider-rejected requests).

```python
class Exchange(BaseModel):        # never split
    assistant: Message
    results: tuple[Message, ...]
    tokens: int
    tainted: bool                 # taint survives into the summary

class ExchangeCompactor(Protocol):   # agency-internal protocol, NOT a hexagonal port
    async def compact(self, exchanges, *, keep_first: int, keep_last_tokens: int) -> tuple[Exchange, ...]: ...
```

Keep policy: `keep_first_exchanges` verbatim (intent anchor) + most recent exchanges up to `keep_last_tokens`, whole exchanges only. Middle span → one synthetic tagged summary turn. Two implementations: **`TruncatingCompactor`** (deterministic, no model call — v1 default, ships with the module) and **`ModelCompactor`** (uses the `compaction` role). Token counting via a `len(text)//4` estimator behind a single function so a real tokenizer swaps in later. New `CompactionApplied` event in `domain/events.py` + catalog regen.

**Anchored artifacts survive outside the transcript:** `TaskSpec` + acceptance criteria, plan state, and two lifted artifacts — the open-file set and unresolved diagnostics — are structured state re-rendered every assembly, never entrusted to the summary.

**Conformance tests:** post-compaction request is provider-valid (zero orphan `tool_result` ids; reasoning blocks intact or dropped whole-exchange) · `total ≤ keep budgets ⇒ no-op` · a 200-step synthetic run completes under a 128k window.

### 7.3 PR-3.3 — TaintGate v1 · *TCB, human-authored*

**Files:** `domain/content.py` · `adapters/tools/registry.py` · `kernel/policy/engine.py` · `kernel/policy/effects.py` · `kernel/dispatch.py` · `domain/events.py`

**No new module and no new gate class.** The choke point already provides every hook needed; a separate gate would create a second authorization path, which is the one thing the architecture forbids.

1. `ToolResult.trusted: bool = False` (additive, default-safe for existing cassettes). `register_handler(..., trusted_output: bool)`; `dispatch` stamps `result.trusted` from registration. Builtins: `read_file`/`list_dir`/`grep`/`run_command` → `False` (they surface repo content); `apply_edit`/`write_file` → `True`.
2. `DefaultPolicyEngine` gains `self._tainted_runs: set[str]`. In `record_outcome(grant_id, result)` the grant is still in `_active_grants` at that moment (the pop happens in the same method, `engine.py:154`) — resolve `run_id` from it and, if `not result.trusted`, add it. **Monotonic:** nothing removes an entry until the run terminates. Expose `is_tainted(run_id)` as a concrete-class helper like the existing `get_grant` — deliberately **not** on the Protocol; taint is Control-internal state.
3. `authorize()` gains a pre-grant check: tainted run **and** tool ∈ `MUTATION_TOOLS` → `Decision(allowed=False, requires_human=True, reason="tainted-context mutation requires approval")`, **at every autonomy level**.
4. `dispatch()` wraps untrusted text content in the `<untrusted-data source=…>` envelope before returning to the loop (the envelope currently exists only in docs) and emits a new `TaintIntroduced` event.
5. **Taint → compactor:** tainted-span summaries carry the envelope. Extend `test_external_provenance_survives_roundtrip` to the summary path — the summary of untrusted content is untrusted.

Until the CLI approval loop exists (v2-S7), `requires_human=True` denials flow back as `is_error` tool results the model can see, and tainted mutations fail closed. That is the correct pre-sandbox posture.

**Proving test — injection canary:** a planted hostile README instructs a write; the mutation is denied with `requires_human=True`; zero tainted diffs land unapproved.

### 7.4 PR-3.4 — `FrozenRunState` + provider degradation

**Files:** `domain/control.py` · `agency/run_loop.py` · `adapters/model/fallback.py`

- `FrozenRunState` with **grants absent by design**. Extend the existing `test_no_grant_in_any_public_signature` contract test to assert no field of `FrozenRunState` is `Grant`-typed. Freeze/thaw path: thaw = rebuild kernel, re-materialize at `worktree_ref`, re-authorize on demand. Consumers: budget-park, failover, future interrupt.
- Degradation policy: backoff-first economics; failover as a checkpoint event (`ProviderFailover`); reasoning blocks dropped whole-exchange across providers; per-role `fallback` binding resolved at composition, replacing the current blind-chain semantics in `adapters/model/fallback.py` for role-level failover.

**Proving test:** freeze → `kill -9` → thaw → identical final `GateReport`, three times.

**Phase 3 exit gate:** 200-step long-run e2e green · injection canary zero-leak · freeze/thaw deterministic · cache-hit-rate reported per run.

---

## 8. Phases 4–7 — condensed briefs

Detail deliberately omitted: it will be stale by arrival. Dependencies and exit gates are what matter now.

**Phase 4 — Measurement re-baseline + Best-of-N.** *Depends on 1, 2, 3.* Harden E0 first, then ship the capability it measures — measurement strictly before the thing measured. E0 hardening: harvester validation gate (≥30 tasks, clean reverts, reproducing failing test), A/A floor with a CI-committed confidence interval, paired stats + multiple-comparison correction verified against fixtures. **Resolve the `e0/` vs `adapters/benchmark/` duplication here** (see §11). Then worktree-parallel Best-of-N over `GitWorktreeManager` (currently a stub with four SENIOR TODOs) with early pruning, sequential repair, staggered launch with clean-admit cancellation. Scoring bootstrap S-0/S-1: deterministic proxy composite that **ranks but never admits** (contract test: `select()` cannot return a non-admitted candidate while an admitted one exists). Trace→dataset exporter: `sagiha export --format sft|dpo`, eligibility = admitted ∧ replay-verified ∧ ¬tainted ∧ within-budget; DPO pairs from BoN siblings on identical prefixes. **Gate:** BoN beats single-shot beyond the measured A/A floor, with zero grader modifications — now actually detectable, thanks to Phase 1.

**Phase 5 — Perimeter (B5a).** *Depends on 3 (TaintGate — autonomy without it is refused) and 4 (worktrees to materialize).* Rootless Podman `ContainerSandbox` replacing the stub; the `Workspace` conformance suite parametrized over `LocalWorkspace` **and** `ContainerSandbox` — the hexagon's payoff test. Egress proxy with hostname allowlist, direct outbound dropped, no host credential reachable inside. `subprocess`+`autonomous` refusal retained; container required for `autonomous`/`scheduled`. **Gate:** injection canary suite across the pinned suite → zero out-of-worktree effects, zero credential reads, zero non-allowlisted egress. `autonomous` becomes legal for the first time.

**Phase 6 — Retrieval, code graph, cold-start.** *Depends on 3 (the seed-only assembler gives retrieval a legal insertion point) and 4 (E0 to ablate against).* FTS5 indexer with AST-bounded chunks; Tree-sitter code graph with import/call/co-change edges and `impacted_by`; register `find_symbols`/`get_skeleton`/`impacted_by` (`trusted_output=True` — harness-derived) within the 20-tool cap; `sagiha init` seeding `AGENTS.md` from the code graph + toolchain detection, entering prompt Layer 4 verbatim. **Gate:** recall@10 ≥ target on a labelled set; retrieval-on beats retrieval-off **and** init-on beats init-off beyond the floor. If either fails, that component does not become default-on. Dense tier stays deferred per ADR-0014 regardless.

**Phase 7 — Story-DAG, MCP, interactive surface.** *Depends on 4, 5 (MCP without a perimeter is refused), 6 (the decomposer needs file-closures).* `WorkflowStep`/`PipelineRunner`, `StoryDecomposerStep` emitting dependency edges and disjoint closures, and the load-bearing `IntegrationStep` (rebase → re-gate → closure-invalidation ⇒ back to the board, never a silent merge). MCP stdio client — discovered tools register `trusted_output=False` and dispatch through the same choke point. Streaming + interrupt-and-steer: steering is a **tail append** so Layers 1–7 stay byte-identical and the tail cache survives — only possible because retrieval was ruled seed-only. **Gate:** ADR-0018 honored to the letter — planning must beat feeding the raw prompt to the inner loop, beyond the floor, including 2-way parallel stories. **If negative, the Protocol stays and the pipeline does not ship.**

**Handoff.** With Phase 7 closed, the Conductor's C0 phase (`docs/reviews/agi_evolution_path.md`, moved to `docs/rationale/` by PR-0c) becomes startable — its hard dependencies (H1/H2 fixes, `FrozenRunState`, compactor, honest bench) are all above that line. It is **out of scope until then**; a Conductor scheduling against fictional zero-cost telemetry would be a random-walk allocator.

---

## 9. Coder-agent operating guide

### 9.1 Per-epic prompt skeleton

```
CONTEXT TO LOAD (nothing else):
  - refactor_sagiha_v2_guidelines.md §<n>  (this epic)
  - docs/STATUS.md                          (current honest capability table)
  - the files listed in FILES IN SCOPE

FILES IN SCOPE:   <explicit list — do not edit outside it>
FORBIDDEN:        src/sagiha/kernel/policy/**, src/sagiha/outer_loop/evaluator/**
                  (TCB — propose the diff, a human authors the commit)
                  docs/**  (Phase 0 is closed; docs changes are separate PRs)

TASK:
  1. Write the proving test FIRST. Run it. It MUST fail against main.
  2. Implement the change.
  3. Run the seven signals (§2.4). Test count must not fall.
  4. Report: what got more honest, and which number moved as a result.

DO NOT:
  - widen scope to "while I'm here" fixes — file them, don't fix them
  - make a test pass by weakening the test
  - return a success-shaped literal from anything unimplemented (that is H3)
```

### 9.2 Standing rules

1. **Regression protocol.** All seven signals on every PR; baseline test count is monotonic; `bench --aa` at every phase close, results committed.
2. **No periphery before the gate.** A phase's exit gate is the only thing that closes it. MCP/OTel/frontend work inside an unrelated phase is the anti-pattern two audits have now flagged. The seven `sprint-fe-*` docs stay archived until Phase 7's TUI creates a real consumer.
3. **Honest negatives are deliverables.**
4. **`docs/STATUS.md` is updated the day a gate closes**, in the `v2-S` series, and never claims what the delta audit taught us to check first.
5. **The TCB is never agent-authored.** `.github/workflows/ci.yml`'s `tcb-check` enforces this for author `sagiha-agent`; do not weaken it.

---

## 10. Risk register & sequencing rationale

| Risk | Why the plan orders things this way |
| :--- | :--- |
| **Measuring over fabricated instruments** | H1/H2 strictly precede all else. Any bench number taken before Phase 1 is uninterpretable and must not be cited afterward. |
| **The honest-drop revert** | Phase 1's pass-rate fall looks exactly like a regression. PR-1.5 publishes before/after in the same commit range precisely so nobody reverts the fix. |
| **Port churn once consumers exist** | The three v2 bumps (`ModelProvider`, `ToolRegistry`, `CandidateSearch`) are taken in Phase 2 while each has ≤1 stub adapter and zero external consumers. After Phase 4 they cost 10× more. |
| **Compaction without taint** | Shipped together in Phase 3. A compactor that summarises tainted spans without re-wrapping them is a laundering channel — the exact failure the provenance conformance test was written to catch, moved one layer down. |
| **Context exhaustion kills runs today** | No compaction exists. Any task past ~50 steps hits the window and dies. This is the only defect class that hard-kills runs right now, which is why Phase 3 precedes all capability work. |
| **Block 5 mega-scope** | Decomposed into Phases 5/6/7 with the sandbox alone and first — it is the perimeter and the unblock for `autonomous`, not a peer of MCP and streaming. |
| **Doc mass outrunning code** | Phase 0's ratchet plus the shrink rule (add N words, delete N). Without the CI gate the ratio reverts within two sprints. |
| **Conductor started too early** | Out of scope until Phase 7 closes. Its C0 exit gate requires honest cost telemetry, which does not exist until Phase 1. |

---

## 11. Open questions for the tech lead

These are genuinely undecided in the corpus. Answer before the phase that depends on each.

1. **The 15k ceiling vs. a 54k reality.** §4.3's demotion program gets normative mass down substantially, but 15,000 is an assertion, not a derivation. Is it the target, or should the ratchet stop at a defensible measured number (e.g. "≤ 2× the LOC count")? *Blocks: PR-0c.*
2. **Python pin.** The suite passes on 3.12 despite `requires-python >= 3.13` (verified). Either the pin does no work, or CI's 3.13 masks a latent incompatibility. Recommendation: keep the pin (ADR-0009 binds it) and add a 3.13 matrix assertion. *Blocks: nothing; decide anyway.*
3. **`e0/` vs `adapters/benchmark/`.** Two parallel implementations of the same idea — `e0/` is real and CLI-wired, `adapters/benchmark/` is stubs behind a port. Delete the stubs and drop the port, or make `e0/` the adapter behind it? *Blocks: Phase 4.*
4. **`docs/frontend/` and `sprint-fe-*`.** §4.3 archives them to `rationale/`. Should they instead be deleted? They describe a surface with no consumer until Phase 7 and no current owner. *Blocks: PR-0c.*
5. **Port count target.** The corpus says 21→15; the tree holds 24 Protocols / 20 files. Confirm the real target so ADR-0019's exit gate is checkable. *Blocks: PR-2.1.*
6. **CI replay fixture.** The replay job references `tests/fixtures/replay_smoke/workspace`, which is not tracked. Is that job actually gating anything today? *Blocks: PR-1.2's cassette migration verification.*
7. **ADR dual status.** ADRs carry status in frontmatter *and* in a body line. Normalise to one, or document the duality. *Blocks: PR-0e.*
