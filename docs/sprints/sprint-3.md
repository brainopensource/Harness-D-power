# **Sprint 3: Close the Loop — First Runnable, Replayable, Measured Agent Step Chain**

> **Status**: **3a closed (2026-07-30, exit test green in CI)** · **3b closed (2026-07-30)**
> **Source**: [2026-07-29 Foundation Review](../reviews/doing/2026-07-29-foundation-review.md) — Block 1,
> narrowed by the [2026-07-30 Final Review](../../final_review_sagiha_concept_and_plan.md) §5.6/§11 (**C3**).
> **Target**: `sagiha run` completes a small coding task end-to-end on a cassette in CI; `sagiha
> replay` verifies the recording. No new ports, no new subsystems. (Against local Ollama manually —
> the OpenAI-compatible adapter — is tracked separately below; it is not part of 3a's exit test.)

> [!IMPORTANT]
> **Sprint 3 is split into 3a and 3b.** The original single-sprint checklist packed 2–3 sprints of
> work behind one exit test (final review C3): kernel fixes, a run loop, five tools, an adapter, an
> evaluator, a CLI, resume, and a bus rewrite. **3a is the closed loop** — the smallest slice that
> makes the exit test below true. **3b is hardening** — resume, bus resilience, and deny-path
> coverage that must land before the loop is trusted with longer or riskier runs. 3a's exit test is
> green in CI; **3b's six items and the five remaining refactor debts (R1/R4/R5/R9/R11) are closed
> as of 2026-07-30** — see the 3b section below for evidence per item, and
> [`todo_list_development.md`](../../todo_list_development.md#-refactor-register--must-be-remade)
> for the refactor register.

---

## 🅰️ **Sprint 3a — Closed Runnable Loop — ✅ CLOSED (2026-07-30)**

**Exit test (the only definition of done for 3a):** an e2e test in CI where the agent, driven by a
committed cassette, fixes a failing test in a fixture repo through the dispatch choke point — with
the grant verified at the point of effect, not merely issued — the run is gate-evaluated with every
coding-profile gate `True`/`False` (never `None`), and `sagiha replay --verify` passes on the
recording.

> [!NOTE]
> **Closed 2026-07-30.** `tests/unit/test_sprint3a_e2e.py` runs in CI (the `tests` job, added with
> D29's fix) with `pytest-cov` enforcing the 80% floor, and a separate `replay` job exercises the
> real `sagiha replay --verify` CLI contract against a committed fixture cassette (D28's fix,
> `tests/fixtures/replay_smoke/`). The exit test is green in CI, not merely on a branch — the
> distinction the final review's C3 insisted on.
>
> Two items originally on this checklist are **explicitly not required by the exit test as
> written** and remain open, tracked separately rather than blocking closure:
>
> | Open, not blocking | Item | Where it goes |
> | :--- | :--- | :--- |
> | ~~OpenAI-compatible provider adapter~~ | B.12 | **Closed** — `OpenAIModelAdapter` in `adapters/model/openai.py`, 12 tests passing, `composition.py` wires live/record |
> | ~~`build_kernel` `live`/`record` binding~~ | A.4 | **Closed** — depends on B.12 above, both modes bind |
>
> Everything else 3a surfaced is tracked as **R1, R4, R5, R9, R11** in the
> [Refactor Register](../../todo_list_development.md#-refactor-register--must-be-remade) — shape
> debt rather than missing function. **R2, R3, R6, R7, and R8 closed alongside this sprint** (grant
> verification is now mandatory on the `PolicyEngine` Protocol, the path-scope fallback is deleted,
> the `import-linter` agency contract is enforced rather than warned, `ShortTermMemoryAdapter` is
> deleted, and port stability labels read `provisional`/`experimental` with no port claiming
> `stable`). Remake R1/R4/R5/R9/R11 before Block 2 records a corpus against them.

### A. Kernel defect fixes that block a dispatchable loop

- [x] **1. Tool-call parsing (D1/D11)** — `kernel/react.py` must collect `ToolUseBlock` from
  `Message.content` and resolve it to a `ToolCall`, with `effect` taken from
  `ToolRegistry.get_effect_class(tool_name)`, never from model output.
  - [x] Regression test: a cassette response containing a `tool_use` block results in a dispatched
    tool and a `ToolResult` recorded in the step.
    → `tests/unit/test_sprint3a_phase2_3.py::test_react_parses_tool_use_block`
- [x] **2. `ModelRequest` v2 (D10)** — add `system: str`, `tools: list[ToolSchema]` (name,
  description, JSON schema), `max_tokens`, `temperature`, and a `role: str` tier reference.
  **Must land before any cassette fixture is committed** — cassettes embed this shape.
- [x] **3. Digest cassette matching (D2)** — key replay on a canonical request digest; raise
  `CassetteMismatchError` on mismatch or exhaustion (no silent repeat of the last entry).
- [x] **4. `build_kernel` mode binding (D3)** — `live` binds the `OpenAIModelAdapter` via
  `_create_live_model_provider()`, `record` wraps it in the cassette recorder, `replay` requires
  a cassette path; misconfiguration fails at composition, not at first call.
  **Closed.** `composition.py` wires all three modes correctly. Tested in
  `test_openai_adapter.py::test_composition_live_mode` and `::test_composition_record_mode`.
- [x] **5. Typed event read path + `upcasters.py` stub (D6, C7)** — deserialize stored events
  through the `ALL_EVENTS` discriminated union so `events_for_run` returns concrete event types
  with payloads intact; create `sagiha/domain/upcasters.py` (identity-only upcasters are
  acceptable) in the **same PR**, since the versioning contract in
  [Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md) has
  nowhere to land otherwise the day an event shape changes.
- [x] **6. `call_id` on tool completion (D5, D21)** — add `is_error: bool` **and** `call_id: str` to
  `ToolResult`; add `call_id` to `ToolCallCompleted`/`ToolCallFailed`. Dispatch emits
  `ToolCallFailed` on error, `ToolCallCompleted` on success regardless of truncation; handler
  exceptions surface as `is_error=True`, not prose. Without `call_id`, multi-tool steps cannot be
  audited or mined — fixing D5 without D21 entrenches an unmineable event shape (final review
  §5.6).
- [x] **7. Tool input validation (D13)** — validate `call.arguments` against the registered JSON
  Schema at dispatch; schema violation → `is_error=True` result, handler never invoked.
  `DefaultToolRegistry.dispatch` calls `validate_arguments` (`adapters/tools/registry.py`) before
  the handler runs — a minimal type/required/array-item checker over the stored schema, not a
  `jsonschema` dependency, since the five built-in schemas use only `type`/`properties`/`required`/
  `items`. → `tests/unit/test_tool_validation.py`.
- [x] **8. Honest cassette `stream()` (D15)** — raise `NotImplementedError` (streaming is a sprint
  non-goal) rather than fabricating a non-conformant frame sequence.
- [x] **9. Wire or delete `ShortTermMemoryAdapter` (D12)** — if A.11 prompt assembly reads history
  through it, bind it in composition and add a `Kernel` field; otherwise delete it.
  **Deleted.** A.11 keeps history in a local `list[Message]` (`agency/run_loop.py`); the adapter was
  bound nowhere in `composition.py`. Removed from `adapters/memory/short_term.py` and
  `adapters/memory/__init__.py` rather than left as a dead second path (R7).

### B. Minimum closed loop

- [x] **10. `RunLoop` with stop conditions (C6)** — `RunLoop.run(task: TaskSpec, ctx: RunContext)`
  iterating `step()` with explicit stop conditions: model `end_turn`, `max_steps_per_run`, budget
  exhausted (governor consulted per step — wires `record_spend`/`remaining_budget`, currently dead
  code), cancellation, **and a minimal stuck signature**: the same tool name + argument hash
  repeating N times in a row surfaces the run rather than looping to exhaustion. Without this, D2's
  fix to stop silently repeating the last cassette entry still produces infinite green CI against a
  broken cassette or empty tool loop (final review D2/G21/C6). Emits `RunStarted`/`StepStarted`/
  `StepCompleted`/`ModelCallStarted`/`ModelCallCompleted`/`RunCompleted|RunFailed`.
- [x] **11. Minimal prompt assembly (G7, D18)** — system prompt template + tool schemas + trajectory
  history (prior steps and tool results — today each step is memoryless) packed into
  `ModelRequest` v2. Stable prefix ordering per `docs/02-architecture/prompt-architecture.md`;
  compaction and cache breakpoints are **out of scope**.
- [x] **12. OpenAI-compatible `ModelProvider` adapter (G8)** — `OpenAIModelAdapter` in
  `adapters/model/openai.py` covers Ollama/Qwen local (`base_url`), OpenAI, vLLM, and any endpoint
  exposing the `/v1/chat/completions` route. Uses `httpx.AsyncClient` with retry. The `openai`
  extra is declared in `pyproject.toml`; the adapter checks for it at construction and raises
  `OpenAIExtraMissingError` if missing. 12 tests in `test_openai_adapter.py`, all passing.
  Anthropic/Google adapters remain out of scope.
- [x] **13. Five built-in tools with schema path scoping and grant verification (C1, G2, G12)** —
  exactly five tools, registered at composition from the profile's tool list: `read_file`,
  `list_dir`, `grep`, `apply_edit` (uses `EditRequest`/`EditResult`), `run_command`. Implemented
  over a dev-mode subprocess `Workspace` adapter rooted at `workspace.root` (container sandbox is
  Block 5). Two conditions are **non-negotiable**, not follow-on polish:
  - [x] **Schema-declared path parameters.** Each tool's JSON Schema declares which argument(s) are
    paths (`x-sagiha-path: true`); `PolicyEngine` reads path scope from the schema, not from
    key-name guessing. **The fallback is now deleted (R3), not superseded**: a tool with no
    registered schema fails closed (`"No registered schema for tool '...' — cannot scope grant"`)
    rather than falling back to guessing `"path"`/`"file_path"`/… — which could not see into
    `EditRequest.path` and could mint an unscoped grant for a mutating tool (final review D8/G12).
  - [x] **`get_grant` verified at the point of effect.** `verify_grant(grant_id) -> bool` is now
    mandatory on the `PolicyEngine` Protocol (`ports/policy.py`) and `dispatch.py` calls it
    unconditionally before `registry.dispatch`, rejecting an expired or unknown grant. **R2 closed**:
    the prior `getattr(policy, "get_grant", None)` duck-typed lookup — which let a non-conforming
    engine skip verification silently — is gone; a `PolicyEngine` that cannot answer this fails at
    composition, not silently at dispatch. Regression test:
    `test_sprint3a_phase2_3.py::test_dispatch_rejects_expired_grant`.
- [ ] **14. Minimal `Evaluator` with non-`None` coding gates (D20, G3)** — runs each
  `AcceptanceCriterion.check` via the workspace, produces a real `GateReport`. Under the `coding`
  profile every code gate (`tests_pass`, `tests_unmodified`, `no_new_suppressions`,
  `coverage_not_decreased`) is set to `True` or `False` — **never left `None`** — because
  `GateReport.admitted` treats `g is not False` as passing, so a forgotten gate silently admits
  (final review D20/D25). Add a conformance assert: under `gates="full"`, `admitted` requires all
  four code gates non-`None`.
  **Behaviour done, location wrong — tracked as R4.** `GateReport.admitted` is tightened
  (`domain/work.py`) with tests in `test_sprint3a_phase1.py`, and all four coding gates are set
  explicitly (`agency/run_loop.py:246-290`). But the evaluator lives inside `RunLoop`, while
  `src/sagiha/outer_loop/evaluator/` is still an empty `__init__.py` — and that empty directory is
  what `.github/workflows/ci.yml:21` protects as trusted computing base. **Move the evaluator into
  `outer_loop/evaluator/` before recording anything**, or the grader sits outside the guard that
  exists to stop an agent editing its own grader.
- [x] **15. CLI (G4)** — `sagiha run <goal> [--acceptance <check>...]` and
  `sagiha replay <run_id> --verify` (L0/L1 fidelity per the foundation review §10; L2 deferred).
  `--resume` is **3b** (depends on A.7 below).
  Landed in `cli.py`. **Note the flag mismatch with CI (D28)**: the replay job invokes
  `sagiha replay --verify-all --fixtures …`, which the command does not accept.

### C. Security behavioral tests scoped to 3a (grant verification only)

- [x] **16.** Unknown tool → `is_error=True` result and `ToolCallFailed`.
  → `tests/unit/test_tool_validation.py::test_dispatch_unknown_tool_reaches_registry_and_emits_failed`
  (full path through `kernel.dispatch`, asserting the `ToolCallFailed` event itself, not only the
  result); `::test_dispatch_unknown_tool_returns_error_result` covers the registry in isolation.
- [x] **17.** Expired grant / forged `grant_id` is rejected at dispatch (regression test for B.13's
  `get_grant` verification, not new machinery).
  → `test_sprint3a_phase2_3.py::test_dispatch_rejects_expired_grant`. Path containment picked up
  extra coverage beyond the checklist in `tests/unit/test_path_containment.py` (traversal, sibling
  prefix, symlink escape) — keep it.

### D. CI for 3a

- [x] **18.** CI runs the **full** `pytest` suite with `pytest-cov` and enforces `fail_under = 80`.
  New `tests` job in `ci.yml` runs `pytest tests/ -v --cov=src/sagiha --cov-report=term-missing`;
  `fail_under = 80` from `pyproject.toml` applies automatically (measured: 87–88% at time of
  writing). Every test under `tests/unit/` — including the 3a e2e test — now runs on every push and
  PR, not only on a developer's machine.
- [x] **19.** CI replay job runs `sagiha replay --verify` against a committed cassette.
  Rewrote the `replay` job to invoke the real CLI contract (`sagiha replay <run_id> --verify
  --cassette … --workspace … --trajectory-db …`) against `tests/fixtures/replay_smoke/cassette.json`
  — generated deterministically by `scripts/gen_replay_fixture.py` through the same `RunLoop`/
  `build_kernel` path the CLI uses, not hand-written JSON. The job asserts `replay_ok` appears in the
  output. The old stub's `--verify-all --fixtures …` flags never existed on the command (**D28**);
  the always-skip `else` branch was dead the moment `sagiha replay` shipped, since `sagiha --help`
  already contains the literal substring `" replay "` (from the `run` command's own help text),
  so the stub's own detection logic always took the broken `if` branch.

**Items 18 and 19 are what converted 3a from "implemented" to "closed."** Per the final review's
C3, a partial implementation on a branch does not count — and until these landed, the e2e test
existed and nothing ran it, exactly the "green cassette that never exercised the deny path" failure
the review warned about, one step earlier.

### 🔎 Findings raised by the 3a implementation (2026-07-30) — all closed

`D22`–`D25` come from the final review §11.1; `D26`/`D27` were raised and closed by the
path-containment pass. Continuing the series:

| ID | Finding | Evidence | Resolution |
| :--- | :--- | :--- | :--- |
| **D28** | CI replay job invoked flags the CLI does not define | `.github/workflows/ci.yml` called `sagiha replay --verify-all --fixtures …`; `cli.py` defines `replay <run_id> --verify` | **Closed.** Job rewritten against the real CLI contract and a generated fixture cassette (item 19) |
| **D29** | CI never executed `tests/unit/` | `ci.yml` ran `pytest tests/contracts/ -v` only | **Closed.** New `tests` job runs the full suite with coverage (item 18) |

Shape debts this sprint surfaced — duck-typed grant verification, the surviving path key-guessing
fallback, the evaluator's location, and the unwired `ShortTermMemoryAdapter` — were **R2 / R3 / R4 /
R7** in the [Refactor Register](../../todo_list_development.md#-refactor-register--must-be-remade).
**R2, R3, and R7 closed alongside D28/D29** (mandatory `verify_grant`, deleted fallback, deleted
adapter); **R4** (evaluator location) remains open, tracked for Sprint 3b.

### 🚫 Explicit non-goals for 3a

Resume/`--resume` (3b), `anyio` bus rewrite + observer timeout/quarantine (3b), deny-path beyond
grant expiry (3b), NFS SQLite journal probe (3b), stdio MCP driver, OTel exporter, container
sandbox, worktree manager, LSP, retrieval/indexing, dense embeddings (ADR-0014), best-of-N with
N>1, model routing beyond role→tier lookup, AOI, RHI, prompt caching/compaction, A2A, streaming,
Workflow DAG / `PRDSpec` / `StoryBoard` (ADR-0018 — gated on Block 2 ablation, not 3a).

---

## 🅱️ **Sprint 3b — Hardening — ✅ CLOSED (2026-07-30)**

**Exit condition:** 3a's exit test is green in CI (not merely implemented on a branch), and the
items below land without reopening 3a's checklist. All six items and the five open refactor debts
(R1/R4/R5/R9/R11) landed in one pass; the full suite (`pytest tests/ --cov`, 76 tests), `ruff` +
`ruff format --check`, `pyright`, `lint-imports`, `gen_event_catalog.py --check`, and
`sagiha replay --verify` against the committed fixture were all re-run green afterward, matching
the same "CI green, not just implemented" bar the final review's C3 set for 3a.

- [x] **1. Resumable run state (D9)** — added a `runs` table (run_id, task_json, status,
  updated_at) to `SQLiteTrajectoryStore`, exposed as `TrajectoryStore.upsert_run`/`get_run`
  (`ports/trajectory.py` PORT_VERSION 2). `RunLoop.run(task, ctx, *, resume=True)` derives the
  starting `seq` from `steps_for_run`'s high-water mark — never from engine memory — and folds
  prior steps back into both the returned `steps` list and a reconstructed prompt history.
  `sagiha run --resume <run_id>` loads the stored `TaskSpec` and continues; `goal` becomes
  optional and is required only when `--resume` is absent.
  → `tests/unit/test_run_resume.py` (seq continuation, no primary-key collision, reconstructed
  history reaches the model), `tests/unit/test_cli_resume.py` (CLI argument handling plus a full
  two-phase cassette round trip through the CLI's own async entry point).
- [x] **2. `anyio` bus correctness (D16, D17)** — `kernel/dispatch.py` already constructed one
  `ToolCallRequested` for both `emit` and `intercept` (verified, not something this pass needed to
  fix). `EventBus` now runs observers inside an `anyio` task group with `anyio.fail_after` per
  observer; an observer that raises or times out is logged and **quarantined** — removed from the
  active set for the remainder of the bus's life — without blocking a healthy observer or failing
  the run. `intercept` moved from `asyncio.wait_for` to `anyio.fail_after`, same fail-closed
  semantics. The doc's eight hook points are marked "reserved" where unimplemented, since only
  `pre_tool` fires today (event-bus-and-hooks.md).
  → `tests/unit/test_event_bus_hardening.py`.
- [x] **3. Kernel required ports non-optional (D14)** — turned out already true in the `Kernel`
  dataclass (`model_provider`, `policy_engine`, `resource_governor`, `tool_registry`,
  `trajectory_store`, `memory`, `workspace` have no `None` default); only `evaluator`, `indexer`,
  `code_graph`, `lsp_adapter`, `worktree_manager` are profile-optional. This pass added the
  regression test that was missing, locking the property in via `dataclasses.fields` inspection
  plus a `TypeError`-on-missing-args check.
  → `tests/unit/test_kernel_sprint2.py::test_kernel_mandatory_ports_are_not_optional`.
- [x] **4. Security deny-path tests (U1, D8)** — both mechanisms already existed in
  `DefaultPolicyEngine.authorize` (`always_gate` → `requires_human=True`) and `EventBus.intercept`
  (timeout fails closed); this pass added the missing coverage:
  - [x] A tool in `always_gate` is refused with `requires_human=True` and emits `ToolCallDenied`.
  - [x] Interceptor denial and interceptor timeout both block execution (fail-closed).
  → `tests/unit/test_deny_path_security.py`.
- [x] **5. Provenance filtering (D7)** — `InMemoryMemory.recall` now ranks `Provenance` by trust
  (`OPERATOR` > `HARNESS` > `MODEL` > `EXTERNAL`) and filters out anything below
  `query.min_provenance`.
  → `tests/unit/test_memory_provenance.py`.
- [x] **6. NFS / non-local filesystem SQLite journal mode probe** — `_configure_connection` now
  disables `mmap_size` unconditionally (the SIGBUS vector on network filesystems, independent of
  journal mode) and probes the *actual* journal mode SQLite grants rather than trusting the
  request — WAL relies on shared memory that some filesystems silently refuse; when refused, it
  falls back explicitly to `DELETE` + `synchronous=FULL`.
  → `tests/unit/test_sqlite_journal_probe.py` (uses `:memory:`, which sqlite3 never grants WAL for,
  as a reproducible stand-in for a filesystem that rejects it).

### Refactor debts closed alongside 3b

**R1** (`kernel/react.py` deleted, its two tests migrated to drive `RunLoop`), **R4** (evaluator
moved to `outer_loop/evaluator/GateEvaluator`, bound through the `Evaluator` port — PORT_VERSION 2,
now takes `RunContext` instead of a bare `branch_id` since dispatching acceptance-criteria tool
calls needs the full context), **R5** (`car-model.md` and `runtime/__init__.py` now state plainly
that the Runtime layer has no code until Block 5's sandbox, rather than leaving the empty package
unexplained), **R9** (compaction's three numbers — headroom 20%, keep-first-N=2, keep-last-M=6 —
specified in `prompt-architecture.md`), **R11** (`mcp`/`opentelemetry-*`/`lsprotocol`/`watchfiles`
moved to optional extras; none was imported anywhere in `src/sagiha`). Full detail in
[`todo_list_development.md`](../../todo_list_development.md#-refactor-register--must-be-remade).
All 11 refactor debts are now closed; **R10** (unsandboxed `run_command`) is not a debt — it is a
documented hard constraint that stays open until Block 5.

### 🚫 Explicit non-goals for 3b

Everything listed as a 3a non-goal remains out of scope for 3b as well; 3b only hardens what 3a
ships, it does not grow the surface. The OpenAI-compatible provider adapter (B.12) and
`build_kernel`'s `live`/`record` binding (A.4) remain open — they were never 3b items, only 3a's
tracked fast-follow.

---

## 📏 **Sprint Metrics (recorded from the event log, per foundation review §10)**

- E2E cassette task: success, steps, wall-clock.
- Live Ollama smoke run: success, steps, wall-clock, token usage (documented in the PR, not gated).
- Replay fidelity level achieved (target: L1).
- Coverage % (gate: ≥80).

## ⛓️ **Dependency**

Sprint 2 kernel as-is. 3a depends on nothing beyond it. 3b depends on 3a's exit test being green.
Block 2 (E0-lite benchmark harness) builds directly on 3a's CLI and event log; it does not require
3b, though 3b should land before any run long enough to need resume or bus resilience.
