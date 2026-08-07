---
status: normative
updated: 2026-08-07
---

# STATUS

**Sprints 1, 2, 3, and 3.5 are 100% COMPLETE.** Sprint 3's A/A floor instruments are built and green; Sprint 3.5 (Phase 0 lock & Inner Loop Lift) fixed six correctness defects, decoupled node/edit-format seams, added auto-discovery of task entry files, and enabled full worktree file re-reading on repair edges ([TASK-039..041](./fixes/sprint-3.5-inner-loop-improvements.md)). **The validation ladder local sweeps (qwen2.5, qwen3.6) and paid DeepSeek runs are verified against the inner loop improvements.** B3 is closed: the evaluation container exists and its canary passes here.

| Area | State |
| :--- | :--- |
| `src/aether/domain/` | **Implemented.** Pure Pydantic models (ids, task, taint, budget, gate, model_io, workspace, tools, events, **sandbox**) |
| `src/aether/ports/` | **Implemented.** 9 wire-serializable protocols. Unchanged in Sprint 3 — the container is *not* a tenth port ([ADR-0005](./decisions/0005-eight-ports-adapter-first.md) rev. 2); it reaches the TCB as a structural `SandboxRunner` over `domain/sandbox.py` payloads |
| `src/aether/kernel/` | **Implemented.** Dispatch choke point, `DefaultPolicyEngine`, `ResourceGovernor`, `EventBus` |
| `src/aether/workflow/` | **Implemented.** `WorkflowStep` types, 5-check `TopologyValidator`, `WorkflowExecutor` with the **bounded repair unroll** (TASK-023), `DispatchFacade`, five nodes (`retrieve/generate/apply/evaluate/repair`), **`edit_format.py` seam** (TASK-037) |
| `src/aether/measurement/` | **Implemented.** Repo cache, TCB `Evaluator` (now containerized), F1 timers, **`manifest.py` + `validity.py`** (TASK-014), **`statistics.py` + `outcomes.py` + `families/`** (TASK-012), **`pricing.py`** (A4), **`runner.py`** (TASK-015) |
| `src/aether/adapters/` | **Implemented.** `ModelProvider`, `Workspace`/`WorktreeManager`, `ToolRegistry`, `TrajectoryStore`, `Indexer`, plus **`sandbox/podman.py`** (TASK-016) |
| `src/aether/kernel/` update | **Sprint 3.5.** `governor.spent()` split from `remaining()` (A3); `dispatch.py` + `executor.py` emit dead events (A1–A2) |
| `src/aether/domain/` update | **Sprint 3.5.** `ModelMessage` gains `tool_calls` + `tool_call_id` fields (A5) |
| `composition.py`, `engine.py` | **Implemented.** `engine.run()` takes `sandbox_runtime` and registry; returns governor's real `usage` and `GateReport`. **Node registry keyed by kind** (TASK-038) |
| B3 evaluation container | **Closed.** `containers/eval/` + `adapters/sandbox/podman.py`: `--network none`, `--cap-drop all`, `--security-opt no-new-privileges`, `--read-only`, `--pids-limit`, exactly two host mounts, image **by digest, never tag**. Rootless Podman is the ratified runner; this host has only Docker, so the canary ran under the documented `--runtime docker` fallback |
| B3 canary | **Green in this environment.** 7/7 with `AETHER_REQUIRE_CONTAINER=1` — good candidate passes, **broken candidate fails**, host FS outside the worktree invisible, egress refused, plus two negative tests proving the leak and egress probes can go red |
| Pinned manifest | **`benchmarks/manifests/internal-floor-01.yaml`**, `sha256:7c2c2467…` — 84 tasks, 0 exclusions, splits pinned 50 dev / 21 holdout / 13 sealed, every task screened bidirectionally (gold passes **and** empty fails) through the container |
| Statistics | **Verbatim port green** against pinned fixtures (`tests/fixtures/aether_statistics/`). The derived-N power simulation **reproduces ADR-0003 rev. 2's published table in all twelve cells** (`scripts/verify_power_table.py`, largest deviation 0.0049) |
| F1 timers result | **Measured, RT-3 not crossed.** See [`performance_timers.md`](./rationale/benchmarks/performance_timers.md). RT-1/RT-2 need a 1M-LOC corpus; left open, not claimed |
| Benchmark results | **None.** No valid number has ever been produced — see [`measurement.md`](./measurement.md) §1 |
| A/A variance floor | **Not taken.** Instrument complete and rehearsed (`scripts/run_aa_floor.py --dry-run`, zero API calls); the arms are deferred. See [`noise-floor.md`](./rationale/benchmarks/noise-floor.md) |
| SWE-bench floor | **Blocked on per-task environment images.** The 15-task samples are indexed with pinned base commits, but no image exists for any of them, so the validity canary would exclude all 15 as `instrument_error` |
| Phase 0 decisions | **Ratified and locked.** |
| Predecessor (`src/sagiha/`) | Reference material being retired |

## What CI currently proves

Commands were run and their output pasted; nothing here is typed from memory.

| Gate | State |
| :--- | :--- |
| `pytest tests/aether tests/conformance tests/integration` | **Green.** 314 passed, 4 skipped. Identical under `AETHER_REQUIRE_CONTAINER=1 AETHER_REQUIRE_LIVE_MODEL=1` — both perimeters really run here rather than skipping |
| `pytest` (whole tree) | **689 passed, 11 skipped, 1 xfailed, 4 failed.** All four failures are the same pre-existing environmental cause in the retiring `sagiha` tree: this sandbox has no `python` binary on `PATH`, only `python3` — `test_workspace_conformance.py::test_run_argv_list[local]`, `test_harvester_validate_task.py` (×2), `test_sprint3a_e2e.py::test_e2e_cassette_fixes_failing_check` |
| `pytest tests/integration/test_b3_canary.py` with `AETHER_REQUIRE_CONTAINER=1` | **Green.** 7 passed |
| B2b live endpoint (`test_model_provider_live.py`) | **Green, and now actually exercised.** It had only ever skipped; with a real local endpoint up it failed, because it demanded a hardcoded `qwen2.5-coder-32b`. `tests/live_support.py` now resolves the model the endpoint really serves, so "serves something else" reads as an environment mismatch instead of an adapter failure |
| `pyright --strict src/aether/` | **Green.** 0 errors, 0 warnings |
| `lint-imports` | **Green.** 9/9 contracts kept. `aether-tcb-isolation` now also covers `measurement.manifest` and `measurement.statistics` |
| `ruff check src/aether tests/` | **Green.** The pre-existing `repo_cache.py` E501 is fixed |
| `ruff check .` | **13 errors, all pre-existing**, in helper scripts untouched by this sprint (`generate_swe_sample.py`, `generate_swe_pro_sample.py`, `extract_gemini_share.py`, `find_pro_dataset.py`, `resolve_swebench_bases.py`). The newly vendored `src/{kimi_cli,openhands,reasonix}` trees were added to ruff's existing third-party exclude list |
| Relative links | **Green** — was red with 10 dead links before this sprint (`docs/benchmarks/README.md` used `../../` one level too deep, and three links were absolute `file:///F:/…` Windows paths); fixed |
| Docs word budget (`--max 15000`) | **Green** |
| Event catalog drift | **Green** — 8 events, `RepairIterationStarted` added and regenerated |
| Docs gates can fail · path-constant drift · `tcb-check` | Green |

## Local end-to-end check against a real model (2026-08-07)

Ollama on the Windows host, reached from WSL at `127.0.0.1:11434/v1`, evaluator
contained under Docker, topology `linear_repair_v1.yaml`, 3 DEV tasks from the pinned manifest.
**Wiring verified; capability not claimed.**

| Model | Tasks | Result | Wall-clock |
| :--- | :---: | :--- | :--- |
| `qwen2.5:1.5b` | 3 | 3 FAILED (honest verdicts) | 5.0–5.4 s each |
| `llama3.2:3b` | 3 | 3 FAILED (honest verdicts) | 4.4–9.1 s each |
| `deepseek-r1:1.5b` | 2 | 2 FAILED | 58–92 s each |

Each task ran generate → apply → contained evaluate → 3 repair iterations → re-evaluate,
i.e. 4 model calls and 4 container evaluations, and every one produced a typed tri-state
verdict. Two findings, both about the harness rather than the models:

1. **`RetrieveStep` reads exactly one entry file.** With the default `README.md` the model
   never sees the code it is asked to patch and hallucinates a file; pointed at `mod.py` it
   emits a well-formed diff against the real source. Retrieval beyond the entry file is
   out of M1a's scope — this is the shape of that gap, not a defect.
2. **Ollama reports no token usage on the streamed OpenAI-compatible endpoint**, so
   `RunResult.usage` comes back zeroed there. Cost-per-resolved-task needs a provider that
   reports usage, or a token counter on our side.

At 1.5–3B the diffs are well-formed but wrong (one "fixed" the function signature and left
the buggy body). That is a capability observation about those models on this instrument,
**not a benchmark number** — N is 3, no family was consulted, and nothing was published.

## Deviations recorded rather than papered over

- **Tool execution is uncontained on the host.** `BuiltinToolRegistry` uses `create_subprocess_shell` while the evaluator is containerized. Asymmetric perimeter; `create_subprocess_shell` is shell-injection surface by construction. **Decision (Sprint 3.5): documented now, containerized at M2 with TASK-018's second half.**
- **Tool protocol was malformed and untested.** Sprint 2 appended tool *results* without the assistant `tool_calls` message preceding them, and no `tool_call_id` was sent. Every OpenAI-compatible endpoint requires both. Path had only run against respx mocks returning no tool calls. **Fixed in Sprint 3.5 (A5) + live round-trip test against Ollama.**
- **Container CPU/memory do not come from the governor lease.** `BudgetDims` has no memory or CPU dimension, so they are composition-frozen `ContainerLimits`. Wall-clock *is* lease-derived: `composition.py` clamps the eval timeout to the lease.
- **No `src/aether/agency/repair.py`.** `aether-layers` makes `aether.agency` and `aether.workflow` independent siblings, so a `WorkflowStep` importing prompt logic from `agency/` breaks a 9-for-9 contract. Splitting it is a lattice change and needs an ADR.
- **Two schema extensions**, both noted in the schema files: the manifest's exclusion enum gains `instrument_error` (B4 — an instrument failure is not the task's fault), and `repair.budget_per_iteration` is now **required** and must cover the chain it funds (an under-funded repair block is a silent no-op).
- **I9 mechanism pending (`rank()` / `admit()` type separation).** `spec.md` §2 names "Type-level `rank()` / `admit()` separation" as I9's mechanism. No ranker exists yet, so the type separation is pending implementation with `TASK-067` (Best-of-N candidate ranker).
- **Vacuous `aether.evolution` import-linter contract target.** `.importlinter` names `aether.evolution` in `aether-tcb-isolation`, but `src/aether/evolution/` has not landed yet. The contract target is currently vacuous until Milestone M5.


## Rules this file is held to

- No claim here is unsupported by a line-level code read **or by running the gate and pasting what it said**.
- A gate that cannot fail is not counted as a gate.
- "Not implemented" is a legitimate and expected entry. A plausible-sounding estimate is not.
- A gate reported green here names the command that produced the green.
