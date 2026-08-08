---
status: rationale
updated: 2026-08-07
---

# STATUS

**Phase 0 is locked** — see [`PHASE-0-LOCK.md`](./PHASE-0-LOCK.md) for what is settled, the nine recorded gaps, and what Phase 1 may change without an ADR. This file is the *implementation* record; the lock is the *constraint* record.

**Sprints 1, 2, 3, 3.5, and 4 are 100% COMPLETE.** Sprint 4 restored I7 enforcement (`tests_unmodified` gate), demoted test-source injection to a named ablation arm, hardened non-interactive subprocesses (`stdin=DEVNULL`, env allowlist, lease deadlines), achieved mechanical decoupling, and verified the A/A variance floor pipeline via dry-run rehearsal.

| Area | State |
| :--- | :--- |
| `src/aether/domain/` | **Implemented.** Pure Pydantic models (ids, task, taint, budget, gate, model_io, workspace, tools, events, sandbox, **effects**, **envelope**, **config**) |
| `src/aether/ports/` | **Implemented.** 9 wire-serializable protocols (`EvalSpec` updated with `base_commit` and `test_paths` for I7) |
| `src/aether/kernel/` | **Implemented.** Dispatch choke point, `DefaultPolicyEngine`, `ResourceGovernor`, `EventBus` |
| `src/aether/workflow/` | **Implemented.** `WorkflowStep` types, 5-check `TopologyValidator`, `WorkflowExecutor`, `DispatchFacade`, five nodes (`retrieve/generate/apply/evaluate/repair`), `edit_format.py` seam (guessing inferrers removed) |
| `src/aether/measurement/` | **Implemented.** Repo cache, TCB `Evaluator` (containerized + `tests_unmodified` I7 gate), F1 timers, `manifest.py` + `validity.py`, `statistics.py`, `pricing.py`, `runner.py` |
| `src/aether/adapters/` | **Implemented.** `ModelProvider`, `Workspace`/`WorktreeManager`, `ToolRegistry`, `TrajectoryStore`, `Indexer`, `sandbox/podman.py`, **`subprocess_env.py`** |
| `src/aether/kernel/` update | **Sprint 3.5.** `governor.spent()` split from `remaining()`; `dispatch.py` + `executor.py` emit dead events |
| `src/aether/domain/` update | **Sprint 4.** Effect payloads moved to `domain/effects.py`; single `worktree_path` on `WorktreeRef`; `Envelope` base for node sockets |
| `composition.py`, `engine.py` | **Implemented.** `engine.run()` takes `sandbox_runtime` and registry; returns governor's real `usage` and `GateReport`. Node registry keyed by kind |
| B3 evaluation container | **Closed.** `containers/eval/` + `adapters/sandbox/podman.py`: `--network none`, `--cap-drop all`, `--security-opt no-new-privileges`, `--read-only`, `--pids-limit`, exactly two host mounts |
| B3 canary | **Green in this environment.** 7/7 with `AETHER_REQUIRE_CONTAINER=1` — good candidate passes, **broken candidate fails**, host FS outside the worktree invisible, egress refused |
| Pinned manifest | **`benchmarks/manifests/internal-floor-01.yaml`**, `sha256:5076194a036081ac3d9eb041925cd4792e9f27a6849eaeca94489f38b2dfe6ae` — 84 tasks, 0 exclusions, splits pinned 50 dev / 21 holdout / 13 sealed, schema v1.1.0 with `test_paths` |
| Statistics | **Verbatim port green** against pinned fixtures (`tests/fixtures/aether_statistics/`). Derived-N simulation reproduces ADR-0003 rev. 2 |
| F1 timers result | **Measured, RT-3 not crossed.** See [`performance_timers.md`](benchmarks/results/performance_timers.md) |
| Benchmark results | **None.** No valid capability claim published before floor |
| A/A variance floor | **Rehearsed.** Pipeline dry-run verified 50/50 DEV tasks in 138.6s ($p_{01}=0, p_{10}=0$, McNemar $p=1.000$). See [`noise-floor.md`](benchmarks/results/noise-floor.md) |
| SWE-bench floor | **Blocked on per-task environment images.** |
| Phase 0 decisions | **Ratified and locked.** |
| Predecessor (`src/sagiha/`) | Reference material being retired |

## What CI currently proves

Commands were run and their output pasted; nothing here is typed from memory.

| Gate | State |
| :--- | :--- |
| `pytest tests/aether tests/conformance tests/integration` | **Green.** 408 passed, 6 skipped |
| `pytest tests/unit/test_path_constant_drift.py` | **Green.** 12 passed, 1 xfailed |
| `pyright src/aether/` | **Green.** 0 errors, 0 warnings |
| `lint-imports` | **Green. 10/10 contracts kept** |
| `ruff format --check .` | **Green.** 436 files formatted |
| `ruff check .` | **Green.** 0 errors |
| `python scripts/gen_event_catalog.py --check` | **Green.** 38 events up to date |
| `python scripts/check_links.py` | **Green.** 67 markdown files checked, 0 dead links |
| `python scripts/docs_budget.py` | **Green.** 12,501 / 15,000 words |
| Event catalog drift | **Green — and it was red when this table last claimed green.** `gen_aether_event_catalog.py` still wrote to `docs/development/generated/`, which the `development/ → architecture/` rename deleted, so `--check` reported the catalog stale against a path that did not exist. The generator's path constant is fixed; the catalog's *content* was already correct and was not regenerated |
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

## Instrument-integrity fixes (2026-08-07)

Eight defects found by a forensic audit of `src/aether/` and closed in the same
change. Four were unrecorded anywhere in this tree. **Each fix ships with a test
that fails against the pre-fix code** — the house rule applies to a fix exactly
as it does to a gate.

None of these changes the resolve rate of anything already measured, because
nothing has been measured. That is the point of doing them now.

| # | Defect | What it did | Fix | Proof it can fail |
| :--- | :--- | :--- | :--- | :--- |
| **F1** | **The harness had never been shown a problem statement.** `TaskCandidate` had no field for the issue text, so the manifest schema could not carry one. `runner.py` substituted `candidate.instance_id` in both places | The pre-registered baseline formatted the official SWE-bench template — held as a literal and hashed so "we used the standard prompt" is checkable — with a string like `django__django-11099`. `run_aa_floor.py` handed one hard-coded sentence to every task. Both arms equally uninformed, so lift would not have been *biased*; it would have been `0 − 0`, and the floor would have characterised the variance of a harness that was never told what to do | `TaskCandidate.problem_statement`; `build_manifest` refuses to admit a blank one; `candidate_to_task` and `BareModelHarness` raise `MissingProblemStatement` rather than defaulting; `run_aa_floor.py` reads it from the manifest entry | `test_manifest.py::test_a_task_with_no_problem_statement_cannot_enter_a_manifest`, `test_runner.py::test_the_baseline_is_posed_the_problem_not_the_instance_id` |
| **F2** | **A provider failure was scored as a failed task.** `StopEvent(reason="provider_error")` had no consumer anywhere in the tree | A 429, socket reset or read timeout produced an empty completion → "the model produced no edit" → the gate ran the tests on an unmodified worktree → `FAILED`. B4 was built for the evaluator and never for the provider, and the asymmetry was invisible because both paths end in a `GateReport`. On a rate-limited paid provider this depresses one arm's resolve rate silently while the per-arm instrument-error rate §4.1 requires reads zero | `GeneratedPatch.stop_reason` → `AppliedPatch.instrument_error` → `EvaluateStep` returns `GateStatus.NONE` **without running the tests**. The executor's existing "NONE never routes into repair" rule then covers it | `test_instrument_error_is_not_a_task_failure.py` (6 tests, incl. one asserting a *wrong but real* answer is still `FAILED` — the guard must not shrink the denominator) |
| **F3** | **The `usd_micros` ceiling could not fire.** `commit()` wrote actuals to `_spent`; `reserve()` decided against `_run_root_remaining`; nothing joined them | `commit()` clamped an overrun's refund to zero, so the excess was never debited. With every call site estimating `usd_micros=0`, the remaining balance stayed at exactly the seeded value for the whole run regardless of spend. `engine.py`'s "a real ceiling, not a comment" was not true when it was written | One line: the refund is `reserved − actual` **including when negative**. `BudgetOverrun`'s own docstring already said *"reality is debited regardless"*; the ledger now agrees with it | `test_governor_ledger.py` (6 tests). Honest bound: the denial lands on the effect *after* the one that broke the cap — `TASK-044` moves it onto the offending call |
| **F4** | **Lease leak at the choke point.** The adapter lookup sat between `reserve()` and the `try` that releases | An unknown `effect_class` raised `KeyError` while holding a lease that was never released and never committed — permanently subtracted from the run's ceiling. Unreachable with today's closed adapter table; reachable the moment MCP (ADR-0016), an attenuated subagent grant (ADR-0017) or `TASK-042`'s router adds one | Lookup moved **before** `reserve()`, raising typed `UnknownEffectClass` | `test_dispatch.py::test_an_unknown_effect_class_raises_before_a_lease_exists` |
| **F5** | **I11's predicate was unreachable on the tool loop.** `GenerateStep` built its spans once and passed that round-0 tuple as `justifying_spans` on every subsequent shell call | Tool output is `UNTRUSTED_EXTERNAL` at birth and is fed back to the model, so from round 2 it can steer a tool call — but `DefaultPolicyEngine` evaluated `any(span.label in UNTRUSTED …)` over a set that could not contain an untrusted span by construction. The `i11-untrusted-widen` branch was dead code | `justifying` accumulates each round's tool results, monotonically | `test_step.py::test_untrusted_tool_output_justifies_the_next_tool_call`. **Behaviourally inert today** — no shipped topology sets `params.tools: true` — so this makes the invariant reachable *before* the path that needs it is turned on |
| **F6** | **`NODE_SOCKETS` was a hand-written string map with nothing tying it to the steps.** `check_socket_compatibility` reads only that map | The validator was checking a shadow of the type system against itself. Changing a step's socket type left every topology validating against the stale pair, surfacing as an `AttributeError` several nodes downstream mid-run rather than at load | A test asserting `NODE_SOCKETS[kind] == (step.input_type.__name__, step.output_type.__name__)` for every registered kind | `test_step_registry.py::test_node_sockets_matches_what_the_steps_actually_declare` |
| **F7** | **The whole-file parser guessed write targets.** Two fallbacks: "the only `.py` token in the reply", then "the *first* `.py` token, prose included" | A repair prompt quotes the failing test output, so the first `.py` token in a repair reply is routinely the test file. This reproducibly rewrote `run_tests.py`. With I7 (`tests_unmodified`) still unenforced, a candidate could overwrite the tests grading it and score `PASSED` | Both guessing branches deleted. The three ways a model can *state* a path (fenced `python:<path>`, `# filename:` first line, `=== path ===` header) all still work; an unresolvable block is now **no edit**, which the repair edge can read | `test_edit_format.py` (3 tests, incl. one asserting a reply mentioning `run_tests.py` in prose produces no write) |
| **F11** | **The workflow validator and executor were in no TCB contract.** `spec.md` §6 lists them as immutable TCB; `PHASE-0-LOCK` L7 locks it | The strongest claim in the lock about topology validation was enforced by nothing while CI stayed green — the trap ADR-0006 names about itself | New `aether-workflow-tcb-isolation` contract. Separate from `aether-tcb-isolation` because that one forbids `aether.workflow`, which these two modules legitimately import | `lint-imports` — 10 contracts, 0 broken |

**Two documentation gates were reported green while red**, both from renames in
this branch; see the table above. Both are fixed, and the link gate now prints
how many files it did **not** check.

### Consequences that are not fixes

- **`benchmarks/manifests/internal-floor-01.yaml` can no longer carry a measured run.** It was
  pinned before `problem_statement` existed, and it is TCB data — L15 forbids editing it. It must
  be **rebuilt** (a new hash) with `scripts/build_floor_manifest.py`, which now emits per-task
  issue text. Until then `run_aa_floor.py` records each of its tasks as `NONE` with the reason,
  rather than running them against a hard-coded sentence. **This blocks the A/A floor**, and it is
  the honest state: the floor was not runnable before either, it just did not say so.
- **`TASK-044`'s recorded mechanism was wrong** and is corrected in the backlog. It described an
  overrun being "detected on the next reserve"; nothing detected it on any reserve. F3 makes that
  description true, and `TASK-044`'s remaining scope is to move the denial one call earlier.

## Deviations recorded rather than papered over

- **Tool execution is uncontained on the host.** `BuiltinToolRegistry` uses `create_subprocess_shell` while the evaluator is containerized. Asymmetric perimeter; `create_subprocess_shell` is shell-injection surface by construction. **Decision (Sprint 3.5): documented now, containerized at M2 with TASK-018's second half.**
- **Tool protocol was malformed and untested.** Sprint 2 appended tool *results* without the assistant `tool_calls` message preceding them, and no `tool_call_id` was sent. Every OpenAI-compatible endpoint requires both. Path had only run against respx mocks returning no tool calls. **Fixed in Sprint 3.5 (A5) + live round-trip test against Ollama.**
- **Container CPU/memory do not come from the governor lease.** `BudgetDims` has no memory or CPU dimension, so they are composition-frozen `ContainerLimits`. Wall-clock *is* lease-derived: `composition.py` clamps the eval timeout to the lease.
- **No `src/aether/agency/repair.py`.** `aether-layers` makes `aether.agency` and `aether.workflow` independent siblings, so a `WorkflowStep` importing prompt logic from `agency/` breaks a 9-for-9 contract. Splitting it is a lattice change and needs an ADR.
- **Two schema extensions**, both noted in the schema files: the manifest's exclusion enum gains `instrument_error` (B4 — an instrument failure is not the task's fault), and `repair.budget_per_iteration` is now **required** and must cover the chain it funds (an under-funded repair block is a silent no-op).
- **I9 mechanism pending (`rank()` / `admit()` type separation).** `spec.md` §2 names "Type-level `rank()` / `admit()` separation" as I9's mechanism. No ranker exists yet, so the type separation is pending implementation with `TASK-067` (Best-of-N candidate ranker).
- **I10 mechanism does not exist.** `spec.md` §2 names "CI floor on byte-identical-prefix rate over a fixed replay" as I10's mechanism. There is no assembler, no declared breakpoint set and no such CI job — one short frozen `system` message in `generate.py` is the whole of L1. This is the same class of gap as I7 and I9 and it had been recorded in neither this file nor `PHASE-0-LOCK.md` §4; it is now in both. Closed by `TASK-056`.
- **I11 is not enforced on the model path.** `DefaultPolicyEngine`'s predicate is correct, but nothing on that path produces untrusted spans, and repository content is labelled `AGENT` precisely so the tool loop keeps working. Labelling them as the spec requires would make `DefaultPolicyEngine` fail closed on every shell tool call. Sequenced behind `TASK-030a`/`TASK-048`/`TASK-054`. Recorded here because I11 otherwise reads as enforced.
- **Vacuous `aether.evolution` import-linter contract target.** `.importlinter` names `aether.evolution` in `aether-tcb-isolation`, but `src/aether/evolution/` has not landed yet. The contract target is currently vacuous until Milestone M5.
- **The measured path and the tested path are different code.** `scripts/run_aa_floor.py` calls `engine.run()` directly; `measurement/runner.py`'s `PairedRunner`/`HarnessUnderTest` seam — which is conformance-tested and inside the import lattice — is used by neither floor script, and has no AETHER arm at all, only `BareModelHarness`. The rig therefore cannot compute lift as it stands. `TASK-015` is marked ✅ with this unmet as well as the OpenHands arm. Closed by `TASK-083`.
- **`docs/overview/` is a quarantined stale snapshot.** Six files re-stating `spec.md`, `measurement.md`, the ADRs and the backlog — the duplication `README.md` forbids. Tagged `status: historical` + `retrieval: excluded` with a banner, so no retrieval surfaces it and the link gate does not check it. Not deleted; kept as a snapshot. `TASK-084` decides its fate.


## Rules this file is held to

- No claim here is unsupported by a line-level code read **or by running the gate and pasting what it said**.
- A gate that cannot fail is not counted as a gate.
- "Not implemented" is a legitimate and expected entry. A plausible-sounding estimate is not.
- A gate reported green here names the command that produced the green.
