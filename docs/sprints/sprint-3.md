# **Sprint 3: Close the Loop — First Runnable, Replayable, Measured Agent Step Chain**

> **Status**: Planned
> **Source**: [2026-07-29 Foundation Review](../reviews/doing/2026-07-29-foundation-review.md) — Block 1,
> narrowed by the [2026-07-30 Final Review](../../final_review_sagiha_concept_and_plan.md) §5.6/§11 (**C3**).
> **Target**: `sagiha run` completes a small coding task end-to-end on a cassette in CI and against
> local Ollama manually; `sagiha replay` verifies the recording. No new ports, no new subsystems.

> [!IMPORTANT]
> **Sprint 3 is split into 3a and 3b.** The original single-sprint checklist packed 2–3 sprints of
> work behind one exit test (final review C3): kernel fixes, a run loop, five tools, an adapter, an
> evaluator, a CLI, resume, and a bus rewrite. **3a is the closed loop** — the smallest slice that
> makes the exit test below true. **3b is hardening** — resume, bus resilience, and deny-path
> coverage that must land before the loop is trusted with longer or riskier runs, but that must not
> block declaring 3a's exit test green. Do not call "the loop" closed until 3a's exit test passes;
> do not call Sprint 3 closed until 3b also lands.

---

## 🅰️ **Sprint 3a — Closed Runnable Loop**

**Exit test (the only definition of done for 3a):** an e2e test in CI where the agent, driven by a
committed cassette, fixes a failing test in a fixture repo through the dispatch choke point — with
the grant verified at the point of effect, not merely issued — the run is gate-evaluated with every
coding-profile gate `True`/`False` (never `None`), and `sagiha replay --verify` passes on the
recording.

> [!NOTE]
> **Progress as of 2026-07-30** — commit `7d8956a` landed the bulk of 3a. The checklist below is
> marked against the code, not against intent. **The exit test is not yet green in CI**: it exists
> as `tests/unit/test_sprint3a_e2e.py`, but CI runs only `tests/contracts/`, so nothing enforces it.
>
> | Remaining for the 3a exit test | Item | Blocks |
> | :--- | :--- | :--- |
> | 1. CI runs `tests/unit/` + the replay job | D.18, D.19 | **Nothing enforces the exit test** — and the replay job's flags don't match the CLI (**D28**) |
> | 2. OpenAI-compatible provider adapter | B.12 | `model.mode=live` fails closed; no local-LLM run possible |
> | 3. `build_kernel` `live`/`record` binding | A.4 | Depends on B.12 |
> | 4. Tool input schema validation | A.7 | D13 unfixed — handlers run on unvalidated arguments |
> | 5. Unknown-tool deny test | C.16 | The only 3a checklist test never written |
>
> Item 1 is what converts 3a from *implemented* to *closed*; items 2–3 are the path to a run against
> a real model. Everything else 3a surfaced is shape debt rather than missing function, and is
> tracked as **R1–R11** in the
> [Refactor Register](../../todo_list_development.md#-refactor-register--must-be-remade) — notably
> **R2** (grant verification reached by duck typing), **R3** (path-scope key-guessing fallback
> survives), **R4** (evaluator lives in `agency/`, not `outer_loop/evaluator/`), and **R7**
> (`ShortTermMemoryAdapter` wired zero times). Remake those before Block 2 records a corpus against
> them.

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
- [ ] **4. `build_kernel` mode binding (D3)** — `live` binds the OpenAI-compatible adapter (A.5
  below), `record` wraps it in the cassette recorder, `replay` requires a cassette path;
  misconfiguration fails at composition, not at first call.
  **Partial (`composition.py:136-155`).** `replay` binds and validates the cassette path correctly.
  `record` and `live` both raise at composition because no live provider exists to wrap — correct
  fail-closed behaviour, but the item does not close until **B.12** lands and both modes bind.
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
- [ ] **7. Tool input validation (D13)** — validate `call.arguments` against the registered JSON
  Schema at dispatch; schema violation → `is_error=True` result, handler never invoked.
  **Not started.** `ToolRegistry` stores schemas (`registry.py:17-32`) and `PolicyEngine` now reads
  path parameters out of them, but nothing validates arguments against them — handlers receive
  whatever the model emitted. Note this needs no new dependency: a minimal type/required check over
  the stored schema is enough for the five built-in tools.
- [x] **8. Honest cassette `stream()` (D15)** — raise `NotImplementedError` (streaming is a sprint
  non-goal) rather than fabricating a non-conformant frame sequence.
- [ ] **9. Wire or delete `ShortTermMemoryAdapter` (D12)** — if A.11 prompt assembly reads history
  through it, bind it in composition and add a `Kernel` field; otherwise delete it.
  **Decision now forced: delete.** A.11 shipped and `RunLoop` keeps history in a local
  `list[Message]` (`agency/run_loop.py:102`); the adapter is bound nowhere in `composition.py`. The
  dual path the review called out (D12) is now real rather than hypothetical. Deleting it is the
  3a-consistent choice — memory is a Block 4 concern, and an unbound adapter will attract a second
  history implementation.

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
- [ ] **12. OpenAI-compatible `ModelProvider` adapter (G8)** — one adapter covering Ollama/Qwen
  local (`base_url`) per `docs/06-guides-and-patterns/ollama-qwen-coder-setup.md`. Anthropic/Google
  adapters are out of scope.
  **Not started — this is the only thing standing between the harness and a local-LLM run.**
  `adapters/model/` contains `cassette.py` and nothing else. The `openai` extra is already declared
  in `pyproject.toml`; the adapter belongs behind it so the default install stays lean (C4). Until
  it lands, every claim about running against Qwen/Ollama is unexercised.
- [ ] **13. Five built-in tools with schema path scoping and grant verification (C1, G2, G12)** —
  exactly five tools, registered at composition from the profile's tool list: `read_file`,
  `list_dir`, `grep`, `apply_edit` (uses `EditRequest`/`EditResult`), `run_command`. Implemented
  over a dev-mode subprocess `Workspace` adapter rooted at `workspace.root` (container sandbox is
  Block 5). Two conditions are **non-negotiable**, not follow-on polish:
  - [x] **Schema-declared path parameters.** *(Landed via `x-sagiha-path: true` annotations walked
    out of the schema — but the key-guessing fallback still runs for tools with no registered
    schema, so it is superseded rather than deleted. See **R3**.)* Each tool's JSON Schema declares which argument(s) are
    paths; `PolicyEngine` reads path scope from the schema, not from key-name guessing
    (`"path"`, `"file_path"`, …), which cannot see into `EditRequest.path` today (final review
    D8/G12). Key-guessing is deleted, not patched around.
  - [ ] **`get_grant` verified at the point of effect.** `dispatch.py` calls `get_grant(grant_id)`
    before `registry.dispatch` and rejects an expired or unknown grant; today `get_grant` has zero
    callers on the dispatch path (final review §5.2). Regression test: `test_expired_grant_rejected_at_dispatch`.
    **Implemented but conditional — tracked as R2.** The call exists
    (`kernel/dispatch.py:84-86`) and the regression test passes
    (`test_sprint3a_phase2_3.py::test_dispatch_rejects_expired_grant`), but it is reached through
    `getattr(policy, "get_grant", None)`, so a policy engine that does not define the method skips
    verification silently. This item stays open until the call is unconditional.
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

- [ ] **16.** Unknown tool → `is_error=True` result and `ToolCallFailed`. **No test exists yet.**
- [x] **17.** Expired grant / forged `grant_id` is rejected at dispatch (regression test for B.13's
  `get_grant` verification, not new machinery).
  → `test_sprint3a_phase2_3.py::test_dispatch_rejects_expired_grant`. Path containment picked up
  extra coverage beyond the checklist in `tests/unit/test_path_containment.py` (traversal, sibling
  prefix, symlink escape) — keep it.

### D. CI for 3a

- [ ] **18.** CI runs the **full** `pytest` suite with `pytest-cov` and enforces `fail_under = 80`.
  **Not started.** `ci.yml:61` runs `pytest tests/contracts/` only, so **every test under
  `tests/unit/` — including the 3a e2e test — is unexercised in CI.** `fail_under = 80` is already
  configured in `pyproject.toml:98` and takes effect as soon as the job runs with `--cov`.
- [ ] **19.** CI replay job runs `sagiha replay --verify` against the committed e2e cassette
  (replaces the always-skip stub).
  **Not started.** `ci.yml:72-79` still branches on whether the command exists, and invokes flags
  the CLI does not define (**D28**). Since `sagiha replay` now exists, the stub's `else` branch is
  dead but the `if` branch fails on arguments — fix both together.

> [!IMPORTANT]
> **Items 18 and 19 are what convert 3a from "implemented" to "closed."** Per the final review's
> C3, a partial implementation on a branch does not count. Today the e2e test exists and nothing
> runs it; that is precisely the "green cassette that never exercised the deny path" failure the
> review warned about, one step earlier.

### 🔎 Findings raised by the 3a implementation (2026-07-30)

`D22`–`D25` come from the final review §11.1; `D26`/`D27` were raised and closed by the
path-containment pass. Continuing the series:

| ID | Finding | Evidence | Impact |
| :--- | :--- | :--- | :--- |
| **D28** | CI replay job invokes flags the CLI does not define | `.github/workflows/ci.yml:77` calls `sagiha replay --verify-all --fixtures …`; `cli.py:76-83` defines `replay <run_id> --verify` | The job fails the moment its `if` branch is taken. Currently masked because `sagiha replay` now exists but the stub's shape was never revisited — the `else` branch is dead and the `if` branch is broken |
| **D29** | CI never executes `tests/unit/` | `ci.yml:61` runs `pytest tests/contracts/ -v` only | **The 3a exit test and every deny-path, path-containment, and gate test are unenforced.** `fail_under = 80` in `pyproject.toml:98` is configured but never applied. This is the "green cassette that never exercised the deny path" failure one step earlier — the tests exist and nothing runs them |

Both ride along with **D.18 / D.19**. The shape debts this sprint also surfaced — duck-typed grant
verification, the surviving path key-guessing fallback, the evaluator's location, and the unwired
`ShortTermMemoryAdapter` — are **R2 / R3 / R4 / R7** in the
[Refactor Register](../../todo_list_development.md#-refactor-register--must-be-remade) rather than
new D-findings, because each passes its tests and is wrong in shape rather than behaviour.

### 🚫 Explicit non-goals for 3a

Resume/`--resume` (3b), `anyio` bus rewrite + observer timeout/quarantine (3b), deny-path beyond
grant expiry (3b), NFS SQLite journal probe (3b), stdio MCP driver, OTel exporter, container
sandbox, worktree manager, LSP, retrieval/indexing, dense embeddings (ADR-0014), best-of-N with
N>1, model routing beyond role→tier lookup, AOI, RHI, prompt caching/compaction, A2A, streaming,
Workflow DAG / `PRDSpec` / `StoryBoard` (ADR-0018 — gated on Block 2 ablation, not 3a).

---

## 🅱️ **Sprint 3b — Hardening**

**Exit condition:** 3a's exit test is green in CI (not merely implemented on a branch), and the
items below land without reopening 3a's checklist.

- [ ] **1. Resumable run state (D9)** — add a `runs` table (run_id, task, status, updated_at);
  derive step `seq` from `TrajectoryStore`, not engine memory; `sagiha run --resume <run_id>`
  continues without seq collisions.
- [ ] **2. `anyio` bus correctness (D16, D17)** — construct one `ToolCallRequested` instance for
  both emit and intercept; add observer timeout + quarantine (doc-specified behavior in
  `event-bus-and-hooks.md`); replace raw `asyncio` primitives with `anyio` per AGENTS.md.
- [ ] **3. Kernel required ports non-optional (D14)** — `model_provider`, `policy_engine`,
  `resource_governor`, `tool_registry`, `trajectory_store` become mandatory; `build_kernel` fails
  at composition when unbindable. Profile-optional ports stay `| None`.
- [ ] **4. Security deny-path tests (U1, D8)** — beyond 3a's grant-expiry check:
  - [ ] A tool in `always_gate` is refused with `requires_human=True` and emits `ToolCallDenied`.
  - [ ] Interceptor denial and interceptor timeout both block execution (fail-closed).
- [ ] **5. Provenance filtering (D7)** — fix `InMemoryMemory.recall` to honor `min_provenance`, with
  a test.
- [ ] **6. NFS / non-local filesystem SQLite journal mode probe** — WAL is currently assumed; a long
  unattended run on a non-local filesystem can SIGBUS without a probe and fallback (final review
  §11.4, G21 family — cheap, high value).

### 🚫 Explicit non-goals for 3b

Everything listed as a 3a non-goal remains out of scope for 3b as well; 3b only hardens what 3a
ships, it does not grow the surface.

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
