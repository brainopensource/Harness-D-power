---
status: normative
updated: 2026-08-07
---

# STATUS

**Sprint 1 is 100% COMPLETE (7 of 7 tasks finished).** **Sprint 2 (Real Adapters & the Walking Skeleton) is 100% COMPLETE (all 9 backlog IDs landed: `TASK-011, 017, 018, 019, 020, 021, 022, 026, 034`).** The M1a four-node linear DAG (`retrieve → generate → apply → evaluate`) runs end to end through headless `engine.py`, over real adapters, for the first time. Per ADR-0002, no benchmark number is published from this — the honest result is a working pipeline, not a score.

| Area | State |
| :--- | :--- |
| `src/aether/domain/` | **Implemented.** Pure Pydantic models (ids, task, taint, budget incl. `BudgetOverrun`, gate, model_io, workspace, tools, events) |
| `src/aether/ports/` | **Implemented.** 9 wire-serializable protocols for core boundaries |
| `src/aether/kernel/` | **Implemented.** Dispatch choke point (`dispatch.py`, now carries `result_json`), `DefaultPolicyEngine` (`policy.py`), real `ResourceGovernor` (`governor.py`, TASK-034), `EventBus` (`bus.py`, TASK-022) |
| `src/aether/workflow/` | **Implemented.** `WorkflowStep[In, Out]` types (`step.py`), topology schema + 5-check `TopologyValidator` (`validator.py`, TASK-020), `WorkflowExecutor` (`executor.py`), `DispatchFacade`, four M1a nodes (`nodes/{retrieve,generate,apply,evaluate}.py`) |
| `src/aether/measurement/` | **Implemented.** Manifest-driven repository cache (`repo_cache.py`, `TASK-010`/B1), TCB `Evaluator` (`evaluator.py`, TASK-019), F1 timers (`timers.py`, TASK-021) |
| `src/aether/adapters/` | **Implemented.** Real adapters for all four M1a boundaries: `ModelProvider` (`model_provider/openai_compatible.py`, TASK-011, closes B2b), `Workspace`/`WorktreeManager` (`workspace/git_cli.py`, TASK-017), `ToolRegistry` (`tools/builtin.py`, TASK-018), plus `TrajectoryStore` (`trajectory_store/sqlite.py`, TASK-026) and `Indexer` (`indexer/tree_sitter.py`) |
| `src/aether/composition.py`, `src/aether/engine.py` | **Implemented.** Composition root wiring the `AdapterTable`/`Dispatcher`; headless `engine.run()` entrypoint (TASK-022) |
| F1 timers result | **Measured, RT-3 not crossed.** See [`performance_timers.md`](./rationale/benchmarks/performance_timers.md) — worktree creation 8.42ms mean, AST parse-and-validate 1.04ms mean on a 9-file sample. RT-1/RT-2 need a 1M-LOC corpus this sample doesn't provide; left open, not claimed. |
| Benchmark results | **None.** No valid number has ever been produced — see [`measurement.md`](./measurement.md) §1 |
| A/A variance floor | Not established. B2b now resolved (`TASK-011`); blocked on B4 (`TASK-013` domain complete, evaluator real) and the A/A floor work itself (Sprint 3) |
| Benchmark suite (`benchmarks/definitions/`) | Stratified 15-task samples mapped in [`swe_verified_sample.md`](./benchmarks/swe_verified_sample.md) & [`swe_pro_sample.md`](./benchmarks/swe_pro_sample.md) |
| Phase 0 decisions | **Ratified and locked.** |
| Documentation | **Phase 0 locked** (2026-08-06). Both docs gates green |
| Predecessor (`src/sagiha/`) | Reference material being retired |

## What CI currently proves

| Gate | State |
| :--- | :--- |
| `ruff check src/aether/ tests/conformance/ tests/aether/ ...` (Sprint 2 files) | **Green.** One pre-existing E501 in `measurement/repo_cache.py` (Sprint 1, `print` line) predates Sprint 2 and is out of this sprint's scope. |
| `pyright --strict src/aether/` | **Green.** 0 errors, 0 warnings — confirmed by running the gate. |
| `python -m lint_imports` (`.venv/bin/lint-imports`) | **Green.** 9/9 contracts kept, including `aether-tcb-isolation` (now covering `measurement.evaluator`) and `aether-layers` (all parens off except `aether.agency`, still unbuilt). |
| `tests/aether/` + `tests/conformance/` + `tests/integration/test_engine_smoke.py` + `tests/unit/test_event_catalog_drift.py` | **Green.** 135 passed, 1 skipped (the `@pytest.mark.live` smoke test — no local Ollama running). |
| M1a end-to-end smoke (`tests/integration/test_engine_smoke.py`) | **Green.** `engine.run()` against `workflows/linear_v1.yaml` completes, produces a `GateReport`, and events land in the `TrajectoryStore` (4× `NodeStarted`/`NodeCompleted`, `RunStarted`, `RunCompleted`). |
| Docs word budget (`--max 15000`) | **Green.** |
| Relative links | **Green.** |
| Docs gates can fail | **Green** — `tests/unit/test_docs_gates.py` |
| Path-constant drift | **Green** — `test_path_constant_drift.py` asserts `aether` module targets |
| Event catalog drift (`scripts/gen_aether_event_catalog.py --check`) | **Green** — `tests/unit/test_event_catalog_drift.py` |
| `tcb-check` | Green |

**Known pre-existing, out-of-scope failures** (present on the branch before Sprint 2, not touched by it): `tests/unit/test_harvester_validate_task.py::test_validate_task_passes_on_a_real_clean_fix`, `::test_validate_task_flaky_failure_rejected`, `tests/unit/test_sprint3a_e2e.py::test_e2e_cassette_fixes_failing_check` — all three fail because the sandbox has no `python` binary on `PATH` (only `python3`/`.venv/bin/python`), confirmed by reverting to the pre-Sprint-2 commit and re-running.

## Rules this file is held to

- No claim here is unsupported by a line-level code read **or by running the gate and pasting what it said**.
- A gate that cannot fail is not counted as a gate.
- "Not implemented" is a legitimate and expected entry. A plausible-sounding estimate is not.
- A gate reported green here names the command that produced the green.
