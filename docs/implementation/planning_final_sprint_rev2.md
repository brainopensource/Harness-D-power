---
status: rationale
retrieval: excluded
updated: 2026-08-01
---

# Planning Rev2: Final Sprints (S7a → S7g) — Closing V2 and Reaching 80% on SWE-bench

> Supersedes `planning_final_sprints.md` as the executable plan. That document was planning
> *input* (a prompt plus a parity wishlist); this one is the buildable specification. Where the
> two disagree, this one wins, and §9 records why.
>
> **Scope:** everything required for v2-S1 → v2-S7 to be genuinely done, and for SAGIHA to post a
> defensible SWE-bench Verified / Terminal-Bench number in the 80% band alongside Hermes and
> Claude Code CLI.

---

## 1. The Central Finding

Sprints S0–S6 built a **correct** agent. They did not build a **converging** one.

`RunLoop.run()` (`src/sagiha/agency/run_loop.py:262-548`) has this shape:

```
for seq in range(start_seq, start_seq + max_steps):
    ...model call...
    if not tool_use_blocks:
        break                      # ← model says "done"; loop exits
    ...dispatch tools...
gate_report = await self._evaluator.evaluate(task, ctx)   # ← line 540, AFTER the loop
return RunLoopResult(gate_report=gate_report, ...)
```

The gate runs **once, after the loop has already exited**. Its verdict is returned to the caller
and shown to nobody. The agent never learns that its patch failed the test. There is no path from
`GateReport.admitted == False` back into another model call.

This is the single largest score lever in the tree, and it is not currently anyone's sprint.
Every published 70-80% result — Claude Code, OpenHands CodeAct, Hermes — is produced by an agent
that runs the tests, *reads the traceback*, and edits again inside the same task. A one-shot
agent with a perfect sandbox, honest gates, and a good model lands in the 20-40% band. The
difference is not model quality; it is the feedback edge that S0-S6 never closed.

Four supporting gaps compound it, all verified in the current tree:

| # | Gap | Evidence | Score impact |
|---|-----|----------|--------------|
| G1 | **No repair loop** — gate is terminal, not a control signal | `run_loop.py:540` | **Decisive** |
| G2 | **No `PASS_TO_PASS` regression check** — only `failing_test_cmd` is graded | `harvester.py:171`, `runner.py:142` | High (false positives) |
| G3 | **Retrieval off by default**; agent edits before it reads | `config.py:266` `enabled: bool = False` | High |
| G4 | **No `Orchestrator` adapter** — port has zero implementations | `ports/orchestrator.py` | Blocks sub-agents + C0 |
| G5 | **MCP driver is a 37-line stub**; no streaming in any model adapter | `adapters/mcp/driver.py` | Parity, not score |

Sprint S7 as currently written in `development_plan_v2.md` schedules G4 and G5 and **does not
schedule G1, G2, or G3 at all**. Rev2 reorders around that.

### 1.1 What is already good enough — do not rebuild

Verified present and sound; these are assets, not work items:

- `adapters/search/best_of_n.py` (356 lines) — Best-of-N is implemented and already wired into
  `BenchmarkRunner._run_single_task_bon` (`runner.py:114`). It needs a *default policy*, not code.
- `GateEvaluator` tri-state `bool | None` grading with `None`-never-passes (`gate_evaluator.py`).
- `e0/statistics.py` — exact McNemar + Holm-Bonferroni + seeded bootstrap, pure stdlib.
- Rootless Podman `ContainerSandbox`, `--network=none` + CONNECT-proxy allowlist.
- TaintGate v1, `FrozenRunState` freeze/thaw, PURE/DESTRUCTIVE per-invocation classification.
- `ExchangeCompactor` — exchange-granular, token-budgeted.
- `repo_cache.py` — landed in `3073823`; the W9 blocker is cleared.

---

## 2. Goals and Exit Criteria

### 2.1 Primary goal

Post a SWE-bench Verified pass rate **≥ 80%** with a published confidence interval, plus a
Terminal-Bench number, both reproducible from a committed suite definition and a seeded runner.

### 2.2 Non-negotiable quality bar

The honest-measurement discipline is the differentiator, not an obstacle to it. A claimed 80%
with a real CI outranks a claimed 80% without one. Concretely:

- No gate may report `True` unless it ran. `None` is never a pass. (Existing invariant — keep.)
- Every published number carries N, the A/A noise floor, and a Holm-corrected p-value.
- `resolved == True` requires **both** `FAIL_TO_PASS` green **and** `PASS_TO_PASS` green (G2).
- The suite definition, model id, temperature, and seed are committed alongside the result.

### 2.3 Definition of Done for V2

| Exit criterion | Measured by |
|---|---|
| `scripts/verify.sh` green: pytest 0 fail · pyright 0 · ruff 0 · format 0 · imports 5/5 · budget ≤15k · links 0 | CI |
| A/A noise floor published with real numbers | `docs/rationale/benchmarks/noise-floor.md` |
| SWE-bench Lite ≥ 80% on the 30-task core suite | `sagiha bench --suite s0-core.json` |
| SWE-bench Verified ≥ 80% on 500 tasks | `sagiha bench --suite verified-500.json` |
| Terminal-Bench ≥ 50% (stretch: 60%) | `sagiha bench --suite terminal-bench.json` |
| Every port in `ports/` has a conformance assertion or is deleted | `tests/contracts/` + `check_port_rent.py` |
| Cost and wall-clock per task in every bench report | `e0/reporter.py` |

---

## 3. Architectural Decisions (binding — do not re-litigate during implementation)

These are decided. Implement them as written; if a decision proves wrong, log a deviation in
§8 rather than improvising.

**AD-1 — The repair loop lives inside `RunLoop`, not above it.**
Rejected alternative: put retry in `BenchmarkRunner` or in `LocalOrchestrator`. Reason: the
repair must share the *same* transcript, the same compaction budget, and the same trajectory
`run_id`, so the model sees its own prior failure as conversation history rather than as a fresh
cold-start prompt. Retrying above `RunLoop` throws away the context that makes repair work.

**AD-2 — The gate result re-enters the loop as a tool-result-shaped message, not as a new system
prompt.** It appends to the transcript through the existing `assembler.append_exchange` path so
compaction, taint, and digesting all apply unchanged. A second system prompt would fork the
stable prefix and destroy prompt-cache hit rate.

**AD-3 — Gate feedback is `trusted=True`.** It is harness-authored text derived from the
repository's own test output. It is *not* a `TaintGate` trigger. (Test *stdout* can contain
attacker-controlled strings in principle; we accept this — the alternative is that every repair
cycle marks the run tainted and requires a human, which makes autonomous benchmarking impossible.
Recorded as a knowingly-accepted risk in §7 R-3.)

**AD-4 — `PASS_TO_PASS` is a first-class field on `HarvestedTask`, graded as a required gate.**
Not an acceptance criterion string. Reason: acceptance criteria are agent-visible and
agent-influencable; regression gates must be structural, alongside `tests_unmodified`.

**AD-5 — Retrieval-before-edit is a default-on loop *step*, not a tool the model may skip.**
The first turn of a coding run is preceded by a harness-issued `Indexer.search(task.goal)` whose
hits are passed as `retrieval_seed`. This preserves ADR-0021 seed-only-by-shape exactly: the seed
is still constructor-time-only, we just stop constructing it empty.

**AD-6 — `LocalOrchestrator` is a thin adapter over `RunLoop`, holding no tools and no grants.**
It converts `RunLoop`'s imperative run into `AsyncIterator[Event]` by subscribing to the bus. It
is the Conductor's entire downward surface (per `agi_evolution_path.md` §2.1) and must stay
free of authority so the C0 milestone does not inherit a privileged scheduler.

**AD-7 — Best-of-N becomes the default for `bench`, gated on the S7a ablation.** If the ablation
shows BoN does not beat N=1 at p<0.05 after Holm correction, it stays off and we say so publicly.
The decision is data-driven but the *wiring* is built now either way.

**AD-8 — No new heavy dependencies.** Specifically: no LangGraph (native orchestration is
already better-typed), no Temporal (`FrozenRunState` already does durable suspension), no Ray
(single-host concurrency suffices at N≤8), no Neo4j / LanceDB (SQLite FTS5 + Tree-sitter is
adequate and boring). This restates the `concept_review.md` Chapter 3 reassessment. The two
adoptions that *are* approved: **DuckDB** (read-only, offline trajectory mining, S9) and
**Promptfoo** (injection regression CI, S10).

**AD-9 — Per-task budgets are a `ResourceGovernor` concern, extended by one method.** Terminal-
Bench tasks are long-horizon (dozens of commands); a global concurrency limit does not bound
them. Add `remaining_steps(run_id)` alongside the existing `remaining_budget`. Do not add a
second governor.

**AD-10 — Shell session state persists per run for Terminal-Bench.** `cwd`, exported env vars,
and background PIDs survive across `run_command` calls within one `run_id`. Implemented in the
sandbox adapter as a per-run session, not by making tools stateful.

---

## 4. Technical Specification

### 4.1 S7a — Measurement Closeout (no new features)

Prerequisite for every "did it help?" question downstream. `repo_cache.py` already landed
(`3073823`), so this is now purely execution.

```bash
sagiha bench --suite benchmarks/definitions/s0-core.json --aa --k 5 \
  --model-name qwen2.5-coder:7b --base-url http://localhost:11434/v1 --api-key-env OLLAMA_KEY
```

Deliverables:
1. A/A noise floor with real numbers in `docs/rationale/benchmarks/noise-floor.md`, replacing the
   current honest refusal.
2. Three ablations, each Holm-corrected: Best-of-N (N=1 vs N=4), retrieval ON/OFF, cold-start
   `init` ON/OFF.
3. Un-guard `bench-aa` in `scripts/verify.sh`.

**Do not proceed to S7f without these numbers.** S7f's whole claim is "the score moved", which is
unmeasurable against an unknown floor.

### 4.2 S7f — The Repair Loop (**the critical sprint**)

Renumbered to run early; `planning_final_sprints.md` §2.3 had it last, which was wrong.

#### 4.2.1 New domain types

```python
# domain/work.py
class RepairContext(BaseModel):
    """What the agent is told after a failed gate. Structural, not free text."""

    model_config = ConfigDict(frozen=True)
    attempt: int  # 1-based; attempt N of max_repair_attempts
    failed_criteria: tuple[CriterionResult, ...]
    failed_gates: tuple[str, ...]  # e.g. ("tests_unmodified",)
    truncated_output: str  # last N lines of the failing check's stdout/stderr
```

#### 4.2.2 `GovernorConfig` / `Config` additions

```python
# domain/config.py
class RepairConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    enabled: bool = True  # default ON — this is the score lever
    max_attempts: int = 3  # total gate evaluations = max_attempts + 1
    output_tail_lines: int = 120  # how much failure output re-enters the prompt
    stop_on_no_progress: bool = True  # identical failure signature twice ⇒ give up
```

#### 4.2.3 `RunLoop` restructure

Extract the existing `for seq in ...` body into `_step_phase()`, then wrap:

```python
async def run(self, task, ctx, *, resume=False) -> RunLoopResult:
    ...existing setup: trajectory upsert, base_commit checkpoint, assembler build...

    gate_report = None
    repair_signatures: set[str] = set()

    for attempt in range(1, self._repair.max_attempts + 2):   # 1 initial + N repairs
        # -- run steps until the model ends its turn / budget / stuck --
        outcome = await self._step_phase(task, ctx, assembler, steps, ...)
        if outcome.parked or outcome.failed:
            break                                  # budget/stuck/wall-clock: no repair

        gate_report = await self._evaluator.evaluate(task, ctx)
        await self._bus.emit(GateEvaluated(run_id=ctx.run_id, gate_report=gate_report,
                                           attempt=attempt))
        if gate_report.admitted or not self._repair.enabled:
            break
        if attempt > self._repair.max_attempts:
            break

        repair = self._build_repair_context(attempt, gate_report)
        sig = self._repair_signature(repair)       # hash of failed gate names + output tail
        if self._repair.stop_on_no_progress and sig in repair_signatures:
            await self._bus.emit(RepairAbandoned(run_id=ctx.run_id, reason="no_progress",
                                                 attempt=attempt))
            break
        repair_signatures.add(sig)

        # AD-2: re-enter as a normal user-role exchange, preserving the stable prefix.
        assembler.append_repair_turn(render_repair_prompt(repair))   # trusted=True per AD-3
        await self._bus.emit(RepairAttemptStarted(run_id=ctx.run_id, attempt=attempt,
                                                  failed_gates=repair.failed_gates))

    ...existing status/cost/emit/return, using the final gate_report...
```

`_step_phase` returns a small frozen dataclass (`parked`, `failed`, `stuck`, `frozen_snap`) so
the outer loop stays readable and the budget/stuck breaks keep their exact current semantics.

#### 4.2.4 The repair prompt

Kept deliberately plain; the model does not need coaching, it needs the traceback.

```python
def render_repair_prompt(r: RepairContext) -> str:
    lines = [
        f"Your previous attempt did not pass. This is repair attempt {r.attempt}.",
        "",
    ]
    for c in r.failed_criteria:
        lines += [f"FAILED CHECK: {c.check}", "```", c.output.strip()[-4000:], "```", ""]
    if r.failed_gates:
        lines += [f"FAILED GATES: {', '.join(r.failed_gates)}", ""]
    lines += [
        "Diagnose the failure from the output above and fix it. "
        "Do not modify test files. Do not add suppressions (# type: ignore, # noqa, "
        "pytest.mark.skip) — those fail the gate.",
    ]
    return "\n".join(lines)
```

#### 4.2.5 New events

Add to `domain/events.py`, register in the catalog (`scripts/gen_event_catalog.py --check`
must stay green):

- `RepairAttemptStarted(run_id, attempt, failed_gates)`
- `RepairAbandoned(run_id, reason: Literal["no_progress","max_attempts"], attempt)`
- `GateEvaluated` gains `attempt: int = 1` (backward-compatible default).

#### 4.2.6 Self-validation before submission (G2)

`HarvestedTask` gains `regression_test_cmd: str | None`. `GateEvaluator` gains a
`regression_tests_pass: bool | None` gate, added to `required_gates` whenever the field is set:

```python
async def _regression_tests_pass(self, cmd, ctx) -> bool | None:
    if not cmd:
        return None
    ok, _ = await self._run(["bash", "-lc", cmd], ctx)
    return ok
```

The importer (`scripts/import_swebench_lite.py`) derives it from `PASS_TO_PASS` exactly as
`failing_test_cmd` is derived from `FAIL_TO_PASS`. This closes the false-positive hole where a
patch makes the target test pass by breaking three others.

#### 4.2.7 Retrieval-before-edit (G3)

In `composition.py`, when building a coding-profile `RunLoop`:

```python
seed: tuple[RetrievalHit, ...] = ()
if config.retrieval.enabled and indexer is not None:
    hits = await indexer.search(task.goal, limit=config.retrieval.seed_limit)
    seed = tuple(hits[: config.retrieval.seed_limit])
loop = RunLoop(..., retrieval_seed=seed)
```

Flip `RetrievalConfig.enabled` default to `True` **only after** the S7a retrieval ablation shows
a positive effect. Until then it stays `False` and the honest-negative doctrine holds.

#### 4.2.8 Cost and latency in the report

`BenchmarkResult` already carries a `CostSummary`. Extend `e0/reporter.py` to emit
`usd_per_task`, `wall_clock_s_per_task`, and `model_calls_per_task` (mean + p50 + p95) in the
markdown table. Leaderboards report these now; a SAGIHA+free-model number is only comparable to
a Kimi/Hermes number on more than one axis if we publish them.

### 4.3 S7b — `LocalOrchestrator` and Sub-Agent Delegation

```python
# adapters/orchestrator/local.py
class LocalOrchestrator:
    """Orchestrator port impl. Holds no tools, no grants, no shell (AD-6)."""

    def __init__(self, loop_factory: Callable[[TaskSpec, RunContext], RunLoop], bus: EventBus) -> None: ...

    async def execute(self, task: TaskSpec, context: RunContext) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event | None] = asyncio.Queue()
        unsubscribe = self._bus.subscribe(context.run_id, queue.put_nowait)
        runner = asyncio.create_task(self._loop_factory(task, context).run(task, context))
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
                if isinstance(event, (RunCompleted, RunFailed)):
                    break
        finally:
            unsubscribe()
            await runner
```

`spawn_subagent` tool in `adapters/tools/builtins.py`:

- Child receives a **subset** of the parent's grants — never a superset, enforced at construction.
- Child receives a **carved slice** of the parent's remaining budget, deducted from the parent up
  front so the pair cannot jointly overspend.
- Child gets a fresh `run_id` with `parent_run_id` recorded in the trajectory.
- Child's final message returns to the parent as a `ToolResult` with `trusted=False` if the child
  ever touched untrusted content (taint is monotonic and propagates upward).
- Enforce the **20-tool per-kernel registry cap** in `DefaultToolRegistry.register`, raising at
  registration time, not at dispatch.

### 4.4 S7c — Streaming and Steerable TUI

- Wire `stream=True` in the OpenAI-compatible adapter; yield `TokenDelta` events on the bus.
- `SteerEvent` tail-appends to the assembler at the next exchange boundary (never mid-turn — a
  mid-turn splice invalidates the `tool_use` id pairing).
- Target: interrupt acknowledged in <2s.
- Independent of the benchmark; ship whenever convenient.

### 4.5 S7d — MCP Client Driver

Fill in the 37-line stub: stdio transport, `initialize`/`tools/list`/`tools/call`, grant-gated
registration of untrusted tools. Every MCP-sourced `ToolResult` is `trusted=False` by
construction. Counts against the 20-tool cap from §4.3.

### 4.6 S7e — Story-DAG Macro Layer

`WorkflowStep`, integration rebasing over worktrees, automated `ResolveConflictTask` inner-loop
repair. Needs S7a's numbers to justify the complexity; sequence last within S7.

### 4.7 S7g — Terminal-Bench Adaptation

- Per-run shell session: `cwd`, env, background PIDs persist across `run_command` (AD-10).
- `ResourceGovernor.remaining_steps(run_id)` + `GovernorConfig.max_steps_per_task` (AD-9).
- Raise `RunLoop.max_steps` default for the terminal profile to 100 (SWE-bench keeps 20-30).
- Suite definition `benchmarks/definitions/terminal-bench.json` in the same shape as `s0-core`.

### 4.8 S8 — Contract Surface Truth-Up

- Extend `tests/contracts/test_adapter_conformance.py` from 7 of 17 ports to **all** ports with a
  live adapter: add `ModelProvider`, `ToolRegistry`, `Memory`, `Evaluator`, `WorktreeManager`,
  `Orchestrator`.
- Execute ADR-0023 port rent: `advisory`, `meta_improver`, `toolchain` have zero importers across
  two closed blocks. Delete them.
- Add `scripts/check_port_rent.py` to `verify.sh` so the rule enforces itself.

### 4.9 S9 / S10 — Observability and Prompt Regression CI

- **S9:** OTel spans, DuckDB read-only trajectory mining, cost attribution, RHI Tier-B failure
  taxonomy.
- **S10:** Promptfoo injection regression suite in CI — RHI Tier A. Roughly 90% of
  self-improvement's defensive value at CI cost.

---

## 5. Task Order

Strictly sequential within a wave; waves R2 and R3 may run in parallel with R1 once R0 lands.

| Wave | Sprint | Tasks | Gate to advance |
|---|---|---|---|
| **R0** | S7a | Run A/A + 3 ablations; publish noise floor; unguard `bench-aa` | Real numbers committed |
| **R1** | S7f | `RepairConfig` → `_step_phase` extract → repair loop → events → `PASS_TO_PASS` gate → retrieval seed → cost in report | S7a ablation re-run shows movement |
| **R2** | S7b | `LocalOrchestrator` → `spawn_subagent` → 20-tool cap | Conformance test for `Orchestrator` |
| **R3** | S7c | Streaming → `SteerEvent` | <2s interrupt demonstrated |
| **R4** | S7d | MCP stdio driver | Untrusted tools register `trusted=False` |
| **R5** | S7g | Shell sessions → per-task budgets → terminal-bench suite | Terminal-Bench runs end-to-end |
| **R6** | S7e | Story-DAG | Integration rebase green |
| **R7** | S8 | Full conformance + port rent + `check_port_rent.py` | 17/17 ports asserted or deleted |
| **R8** | — | Repo hygiene: delete 868 MB vendored trees under `src/`; drop pyright + ruff exclusion lists | Gates mean what they say |
| **R9** | S9/S10 | OTel + DuckDB; Promptfoo CI | — |
| **R10** | — | Full SWE-bench Verified (500) + Terminal-Bench publication run | ≥80% with CI |

**Commit one wave per commit. Never push.** Run `bash scripts/verify.sh` after every wave.

---

## 6. Test Plan

Every item below is a required test, not a suggestion.

### 6.1 S7f — repair loop

| Test | Asserts |
|---|---|
| `test_repair_reenters_on_failed_gate` | Failing gate ⇒ a second `_step_phase` runs; ≥2 `GateEvaluated` events |
| `test_repair_stops_on_admitted` | Passing gate ⇒ exactly one gate evaluation, no repair turn |
| `test_repair_respects_max_attempts` | Always-failing gate ⇒ exactly `max_attempts + 1` evaluations |
| `test_repair_no_progress_abandons` | Identical failure signature twice ⇒ `RepairAbandoned` |
| `test_repair_prompt_contains_failure_output` | Rendered prompt includes the failing check's stdout |
| `test_repair_disabled_matches_legacy` | `enabled=False` ⇒ byte-identical behaviour to pre-S7f |
| `test_repair_preserves_stable_prefix` | `prefix_digest` unchanged across repair turns (cache) |
| `test_repair_does_not_run_on_budget_park` | Parked run ⇒ no repair attempt, `parked=True` preserved |
| `test_repair_does_not_run_on_stuck` | Stuck detection ⇒ no repair attempt |
| `test_repair_turn_is_trusted` | Repair exchange has `tainted=False` (AD-3) |

### 6.2 S7f — regression gate

| Test | Asserts |
|---|---|
| `test_regression_gate_none_when_unset` | No `regression_test_cmd` ⇒ `None`, not in `required_gates` |
| `test_regression_gate_blocks_admission` | `PASS_TO_PASS` failing ⇒ `admitted is False` even with target test green |
| `test_importer_derives_regression_cmd` | `PASS_TO_PASS` in the SWE-bench record ⇒ populated field |

### 6.3 S7b — orchestrator and sub-agents

| Test | Asserts |
|---|---|
| `test_local_orchestrator_yields_terminal_event` | Stream ends on `RunCompleted` or `RunFailed` |
| `test_local_orchestrator_conforms_to_port` | Static assignability to `Orchestrator` Protocol |
| `test_subagent_grants_are_subset` | Child grant set ⊆ parent; superset raises |
| `test_subagent_budget_carved_from_parent` | Parent's remaining budget decreases by the carve |
| `test_subagent_taint_propagates_upward` | Tainted child ⇒ parent `ToolResult.trusted is False` |
| `test_tool_registry_caps_at_20` | 21st registration raises at registration time |

### 6.4 S7g — terminal profile

| Test | Asserts |
|---|---|
| `test_shell_session_persists_cwd` | `cd /tmp` then `pwd` ⇒ `/tmp` across two tool calls |
| `test_shell_session_persists_env` | `export X=1` then `echo $X` ⇒ `1` |
| `test_per_task_step_budget_halts` | `max_steps_per_task` exceeded ⇒ run halts, not silently continues |

### 6.5 Statistical

| Test | Asserts |
|---|---|
| `test_aa_floor_is_nonzero_and_reported` | A/A run produces a floor; reporter prints it |
| `test_holm_correction_applied_to_ablations` | ≥2 comparisons ⇒ corrected p-values in the report |
| `test_reporter_emits_cost_and_latency` | Report table has `usd_per_task` and `wall_clock_s_per_task` |

### 6.6 Regression guards (must stay green throughout)

`verify.sh`: pytest · pyright 0 · ruff 0 · format 0 · `lint-imports` 5/5 · `docs_budget.py --max
15000` · `check_links.py` 0 · `gen_event_catalog.py --check` · new `check_port_rent.py`.

---

## 7. Risk Register

| # | Risk | Mitigation |
|---|---|---|
| R-1 | Repair loop multiplies cost 3-4× per task | `max_attempts=3` default; per-task budget (AD-9); publish $/task so the cost is visible not hidden |
| R-2 | Repair loop blows the context window on long tracebacks | `output_tail_lines=120`; `ExchangeCompactor` already handles the rest |
| R-3 | Test stdout could carry injected instructions, and AD-3 marks it trusted | Knowingly accepted. Revisit if S10's Promptfoo suite finds a live vector; the alternative blocks autonomous benchmarking entirely |
| R-4 | 80% is not reachable with a free/local model regardless of harness quality | Report harness-attributable delta (ablation) separately from absolute score; run the headline number on a frontier model and say which |
| R-5 | `_step_phase` extraction regresses budget/stuck/failover semantics | `test_repair_disabled_matches_legacy` pins byte-identical legacy behaviour |
| R-6 | Deleting 868 MB vendored trees loses reference material | They are untracked; move to a sibling directory outside `src/`, do not delete outright |
| R-7 | S7e Story-DAG is speculative complexity | Sequenced last; may be cut if S7a-S7g reach 80% without it |

---

## 8. Deviation Log

Record any departure from §3's binding decisions here, with reason and date. Empty at authoring
time.

| Date | Decision | Deviation | Reason |
|---|---|---|---|
| — | — | — | — |

---

## 9. What Changed From `planning_final_sprints.md`

| Change | Reason |
|---|---|
| Repair loop promoted from a §2.3 checklist bullet to **S7f, the critical sprint**, sequenced second | It is the decisive score lever and was scheduled nowhere in `development_plan_v2.md` |
| W9 removed from the critical path | `repo_cache.py` landed in `3073823`; N-C1/N-C2 are resolved |
| `PASS_TO_PASS` promoted to a structural required gate (AD-4) | Grading only `FAIL_TO_PASS` admits patches that break the rest of the suite |
| Added **S7g Terminal-Bench adaptation** | The old plan named Terminal-Bench as a target but scheduled no work for it |
| Retrieval-before-edit made a loop step, not a tool (AD-5) | "Confirm the loop calls them" was left as an open question; it does not, and a tool the model may skip does not close the gap |
| Best-of-N reframed as a default-policy decision, not new code | 356 lines already exist and are already wired into the bench runner |
| Explicit no-new-dependency decision (AD-8) | The briefing's stack recommendations were never formally declined; now they are |
