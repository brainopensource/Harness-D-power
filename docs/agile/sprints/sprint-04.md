---
status: rationale
updated: 2026-08-07
---

# Sprint 04 Plan — Instrument Restoration and the Floor

* **Goal**: Restore the validity guards Sprint 3.5 outpaced, get CI green at step one, and **take the A/A variance floor** — the number that unblocks every other number this project will publish.
* **Target Milestone**: [M1a++R](../roadmap.md#phase-matrix--dependencies) · **A/A floor**
* **Tripwire Window**: 6 Business Days
* **Entry condition**: Sprint 3.5 code complete (commit `23cd1b4`). B1, B2b, B4 green; B3 canary green in this environment.
* **Position in the plan**: this sprint is [`sprint-03.md`](./sprint-03.md)'s Task 5 finally executed, plus the repairs that make executing it meaningful.

> **Sprint 3.5 optimised the inner loop's win rate on an instrument whose validity guards were not extended in the same change.** The mechanisms it added are real and stay. What did not land alongside them is the enforcement that makes their results falsifiable. Until Tasks 1–2 close, a floor run characterises the variance of the wrong measurement, and every derived N inherits it.

---

## Sprint Backlog Items

### Task 1: I7 Enforcement — `tests_unmodified` (`TASK-049`) — **blocks Task 5**
* **Target Seam**: `src/aether/measurement/evaluator.py`, `src/aether/domain/gate.py`, `src/aether/workflow/edit_format.py`
* **Specification Pointer**: [`spec.md` §2 (I7)](../../spec.md#2-invariants), [`measurement.md` §5](../../measurement.md#5-gate-design)
* **Acceptance Criteria**:
  1. The evaluator hashes the manifest's pinned test files before running and **refuses to score a candidate that changed them**.
  2. A mismatch yields **`GateStatus.NONE` with `instrument_error` populated** — never `PASSED`, never `FAILED`. Same discipline as B4: an instrument failure is not a data point.
  3. **Negative test required.** Removing the gate must make the suite go red. `grep -rn "tests_unmodified" src/aether/` returns nothing today, so this gate has never existed here — the negative test is what proves it does now.
  4. The last-resort `.py`-token inferrer (`edit_format.py:198-202`) is **deleted**. An unlabelled fence with no resolvable target returns *no edit*. It selects the first `.py` token in the model's prose and reproducibly targeted `run_tests.py`.
* **Why it matters**: without this, the generator can edit its own evaluator. Every resolve rate measured on this instrument is unfalsifiable, and I7 is the invariant `vision.md` §2 calls the one whose failure is *retroactive, invalidating every number the project ever produced*.

### Task 2: Demote Test-Source Injection (`TASK-049b`) — **blocks Task 5**
* **Target Seam**: `scripts/run_local_check.py`, `src/aether/domain/config.py`
* **Specification Pointer**: [`measurement.md` §4.1](../../measurement.md#41-the-baseline-is-part-of-the-instrument)
* **Acceptance Criteria**:
  1. `build_task_instructions()` no longer injects `run_tests.py` by default. Injection is reachable **only** through `AblationFlags.inject_test_source`, default `False`.
  2. The flag is part of the run's config hash, so a run using it says so in its own instrument tuple.
  3. The run banner names which arm produced the output.
* **Why it matters**: the pre-registered baseline is *"no retrieval beyond benchmark-provided context."* With the assertions in the prompt, the harness measures whether a model can satisfy an assertion it was shown. `internal__clamp_low-046` — the model emitted `return b` and satisfied `assert f(6, 9) == 9` — is that mode in action, and the gate had no capability that could object.

### Task 3: CI Green at Step One, and Gates That Match Reality
* **Target Seam**: `.github/workflows/ci.yml`, `scripts/gen_event_catalog.py`, `docs/workflows/*.md`, `docs/STATUS.md`
* **Specification Pointer**: [`measurement.md` §5](../../measurement.md#5-gate-design), [ADR-0009](../../decisions/0009-gates-are-the-schedule.md)
* **Acceptance Criteria**:
  1. `ruff format .` across the tree (**43 files** as of 2026-08-07) and the **16** `ruff check` errors fixed. **CI dies at step one today**, so `pyright` and `lint-imports` have never actually executed in CI despite passing locally and being recorded Green.
  2. The event-catalog gate stops pointing at `docs/_archive/04-workflows-and-loops/event-catalog.md` — an archived file it exits 1 on. `gen_event_catalog.py --check` exits **1** today.
  3. `check_links.py` exits 0. One dead link remains: `proposal_architectural_abstraction_and_harness_engineering_gem.md` uses absolute `file:///home/rocha/...` URLs, which is the exact defect the gate was written to catch. *(The `status:` taxonomy failures recorded in earlier audits were fixed in commit `37ffef9`; `docs_budget.py` now exits 0 and normative sits at 13,687/15,000.)*
  4. `TCB_PATHS` extended to select the evaluator, manifests, families, validator and executor — **it selects none of them today**; it names `src/aether/kernel/policy`, `src/aether/kernel/dispatch`, and three `src/sagiha/` paths from the retiring tree — plus the **reverse** drift test (spec → fragment), which does not exist.
  5. `implemented_sprint_3.5_complete_report.md` moves from `normative` to `rationale`, and its resolve-rate table is re-captioned as wiring verification: N=1–5, no family declared, assertions injected.
  6. `STATUS.md`'s deviations section records that **I11 is not enforced on the model path** — `DefaultPolicyEngine`'s predicate is correct, but nothing produces untrusted spans there, and repo content is labelled `AGENT` precisely so the tool loop keeps working.
* **Why it matters**: a gate reported green that never ran is the D15 defect class. Four of these were recorded Green in `STATUS.md` while exiting non-zero.

### Task 4: Mechanical Decoupling (`TASK-050`, `TASK-051`, `TASK-052`)
* **Target Seam**: `src/aether/domain/{effects,envelope,workspace}.py`, `composition.py`, `workflow/nodes/*`
* **Specification Pointer**: [`spec.md` §3](../../spec.md#3-structure), [`proposal_abstraction_and_harness_composition.md` §4.2](../../fixes/proposal_abstraction_and_harness_composition.md)
* **Acceptance Criteria**:
  1. `import aether.workflow.nodes.retrieve` **does not import `httpx` or any `aether.adapters` module**. It imports three of them today, because the effect payload types live in `composition.py` beside the concrete adapter closures.
  2. One `worktree_path`, not four. One copy is inside the TCB evaluator; the judge and the tool registry must be structurally unable to disagree.
  3. Four payload types share one envelope, and socket types stay distinguishable — collapsing them would defeat `check_socket_compatibility`.
* **Why it is in this sprint**: it is pure deletion of duplication, it carries no behaviour change, and it is the precondition for Sprint 5 and for any out-of-process extraction under [ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md).

### Task 4b: Non-Interactive Subprocess Hardening (`TASK-062`) — **blocks Task 5**
* **Target Seam**: `src/aether/adapters/subprocess_env.py` (new), `adapters/tools/builtin.py`, `measurement/evaluator.py`, `adapters/workspace/git_cli.py`
* **Specification Pointer**: [`measurement.md` §2 (B4)](../../measurement.md#2-instrument-blockers), [`measurement.md` §6](../../measurement.md#6-what-a-claim-needs-before-it-is-published)
* **Acceptance Criteria**:
  1. `stdin=DEVNULL` at every host-side spawn site. `builtin.py:110-120` inherits stdin today, so `git push`, `apt`, or a paged `git log` blocks on a terminal the harness does not drive.
  2. An **environment allowlist**, replacing `_EVAL_ENV = {**os.environ, ...}` (`evaluator.py:56`) and `builtin.py`'s inherited environment. Model-written code currently executes uncontained on the host with the operator's `OPENROUTER_API_KEY` in scope.
  3. Every subprocess carries an `asyncio.wait_for` deadline **derived from the lease**. `builtin.py::_bash` has none; the `BudgetDims(wall_clock_ms=30000)` at `generate.py:189` is a cost estimate the governor reserves against and nothing enforces.
  4. **Negative test**: a command that would block on stdin fails fast instead of running to the timeout.
* **Why it blocks the floor**: a hung tool call runs to the evaluation timeout, returns `GateStatus.NONE`, and `NONE` is excluded from the resolve-rate denominator. An interactive prompt nobody answers therefore shrinks N **non-randomly** — repositories that prompt get systematically dropped — and it is invisible in the aggregate. That is a selection effect entering the sample through a subprocess default.

### Task 5: Run the A/A Variance Floor — **the sprint's reason to exist**
* **Target Seam**: `docs/rationale/benchmarks/noise-floor.md`
* **Specification Pointer**: [`measurement.md` §3](../../measurement.md#3-the-aa-variance-floor), [ADR-0002](../../decisions/0002-no-number-before-the-floor.md)
* **Acceptance Criteria**:
  1. **Blocking preconditions**: Tasks 1 and 2 closed, and the B3 canary executes **in the floor environment** with a deliberately broken candidate failing there. If it passes, the floor is blocked on B3 regardless of anything else in this plan.
  2. Two identical configurations, paired: same tasks, same order, same seeds. N ≥ 50 at the smoke floor, DEV split.
  3. **The run reports its discordance rates (p₀₁, p₁₀).** These are the input to every derived N under [ADR-0003](../../decisions/0003-statistical-admission-protocol.md) rev. 2 — without them no later admission run can be sized.
  4. Per-task wall-clock recorded. **This is what sizes M2-abl**, currently unsized in [`roadmap.md`](../roadmap.md).
  5. The run names its instrument: manifest hash, split, model fingerprint, topology hash, container digests, lockfile hash, seed.
* **On the result**: a wide floor is not a failure of this sprint. It is a measurement, and it changes N rather than invalidating the work. **A run that shows nothing is recorded as showing nothing.**

---

## Exit Gates

| Gate | Closed by | How it is verified |
| :--- | :--- | :--- |
| I7 enforced in `src/aether/` | Task 1 | `grep -rn tests_unmodified src/aether/measurement/evaluator.py` + the negative test going red when the gate is removed |
| Baseline matches `measurement.md` §4.1 | Task 2 | Default run shows no test source; the ablation flag appears in the config hash |
| CI reaches `pyright` and `lint-imports` | Task 3 | `ruff format --check . && ruff check . && pyright --strict src/aether/ && lint-imports` all exit 0 |
| `TCB_PATHS` selects the TCB | Task 3 | `tests/unit/test_path_constant_drift.py`, both directions |
| Non-interactive subprocesses | Task 4b | `stdin=DEVNULL` everywhere; env is an allowlist; the blocked-command negative test goes red without the fix |
| Nodes are adapter-free | Task 4 | `test_node_imports_are_pure` |
| **A/A floor taken** | Task 5 | `noise-floor.md` contains p₀₁/p₁₀ and per-task wall-clock |

## What is explicitly out of scope

- **Any hybrid or routing work** (`TASK-042`–`TASK-045`). `hybrid_architect_editor_v1.yaml` currently reports **$0.00 spend for real DeepSeek charges**, which passes ADR-0003's cost non-inferiority check vacuously. Running it before the floor is worse than not running it.
- **The capability layer** (`TASK-053`–`TASK-058`) — Sprint 5.
- **`TASK-036`** (SWE-bench per-instance images). Deferred to post-floor, unchanged.
