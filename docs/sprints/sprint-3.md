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

### A. Kernel defect fixes that block a dispatchable loop

- [ ] **1. Tool-call parsing (D1/D11)** — `kernel/react.py` must collect `ToolUseBlock` from
  `Message.content` and resolve it to a `ToolCall`, with `effect` taken from
  `ToolRegistry.get_effect_class(tool_name)`, never from model output.
  - [ ] Regression test: a cassette response containing a `tool_use` block results in a dispatched
    tool and a `ToolResult` recorded in the step.
- [ ] **2. `ModelRequest` v2 (D10)** — add `system: str`, `tools: list[ToolSchema]` (name,
  description, JSON schema), `max_tokens`, `temperature`, and a `role: str` tier reference.
  **Must land before any cassette fixture is committed** — cassettes embed this shape.
- [ ] **3. Digest cassette matching (D2)** — key replay on a canonical request digest; raise
  `CassetteMismatchError` on mismatch or exhaustion (no silent repeat of the last entry).
- [ ] **4. `build_kernel` mode binding (D3)** — `live` binds the OpenAI-compatible adapter (A.5
  below), `record` wraps it in the cassette recorder, `replay` requires a cassette path;
  misconfiguration fails at composition, not at first call.
- [ ] **5. Typed event read path + `upcasters.py` stub (D6, C7)** — deserialize stored events
  through the `ALL_EVENTS` discriminated union so `events_for_run` returns concrete event types
  with payloads intact; create `sagiha/domain/upcasters.py` (identity-only upcasters are
  acceptable) in the **same PR**, since the versioning contract in
  [Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md) has
  nowhere to land otherwise the day an event shape changes.
- [ ] **6. `call_id` on tool completion (D5, D21)** — add `is_error: bool` **and** `call_id: str` to
  `ToolResult`; add `call_id` to `ToolCallCompleted`/`ToolCallFailed`. Dispatch emits
  `ToolCallFailed` on error, `ToolCallCompleted` on success regardless of truncation; handler
  exceptions surface as `is_error=True`, not prose. Without `call_id`, multi-tool steps cannot be
  audited or mined — fixing D5 without D21 entrenches an unmineable event shape (final review
  §5.6).
- [ ] **7. Tool input validation (D13)** — validate `call.arguments` against the registered JSON
  Schema at dispatch; schema violation → `is_error=True` result, handler never invoked.
- [ ] **8. Honest cassette `stream()` (D15)** — raise `NotImplementedError` (streaming is a sprint
  non-goal) rather than fabricating a non-conformant frame sequence.
- [ ] **9. Wire or delete `ShortTermMemoryAdapter` (D12)** — if A.11 prompt assembly reads history
  through it, bind it in composition and add a `Kernel` field; otherwise delete it.

### B. Minimum closed loop

- [ ] **10. `RunLoop` with stop conditions (C6)** — `RunLoop.run(task: TaskSpec, ctx: RunContext)`
  iterating `step()` with explicit stop conditions: model `end_turn`, `max_steps_per_run`, budget
  exhausted (governor consulted per step — wires `record_spend`/`remaining_budget`, currently dead
  code), cancellation, **and a minimal stuck signature**: the same tool name + argument hash
  repeating N times in a row surfaces the run rather than looping to exhaustion. Without this, D2's
  fix to stop silently repeating the last cassette entry still produces infinite green CI against a
  broken cassette or empty tool loop (final review D2/G21/C6). Emits `RunStarted`/`StepStarted`/
  `StepCompleted`/`ModelCallStarted`/`ModelCallCompleted`/`RunCompleted|RunFailed`.
- [ ] **11. Minimal prompt assembly (G7, D18)** — system prompt template + tool schemas + trajectory
  history (prior steps and tool results — today each step is memoryless) packed into
  `ModelRequest` v2. Stable prefix ordering per `docs/02-architecture/prompt-architecture.md`;
  compaction and cache breakpoints are **out of scope**.
- [ ] **12. OpenAI-compatible `ModelProvider` adapter (G8)** — one adapter covering Ollama/Qwen
  local (`base_url`) per `docs/06-guides-and-patterns/ollama-qwen-coder-setup.md`. Anthropic/Google
  adapters are out of scope.
- [ ] **13. Five built-in tools with schema path scoping and grant verification (C1, G2, G12)** —
  exactly five tools, registered at composition from the profile's tool list: `read_file`,
  `list_dir`, `grep`, `apply_edit` (uses `EditRequest`/`EditResult`), `run_command`. Implemented
  over a dev-mode subprocess `Workspace` adapter rooted at `workspace.root` (container sandbox is
  Block 5). Two conditions are **non-negotiable**, not follow-on polish:
  - [ ] **Schema-declared path parameters.** Each tool's JSON Schema declares which argument(s) are
    paths; `PolicyEngine` reads path scope from the schema, not from key-name guessing
    (`"path"`, `"file_path"`, …), which cannot see into `EditRequest.path` today (final review
    D8/G12). Key-guessing is deleted, not patched around.
  - [ ] **`get_grant` verified at the point of effect.** `dispatch.py` calls `get_grant(grant_id)`
    before `registry.dispatch` and rejects an expired or unknown grant; today `get_grant` has zero
    callers on the dispatch path (final review §5.2). Regression test: `test_expired_grant_rejected_at_dispatch`.
- [ ] **14. Minimal `Evaluator` with non-`None` coding gates (D20, G3)** — runs each
  `AcceptanceCriterion.check` via the workspace, produces a real `GateReport`. Under the `coding`
  profile every code gate (`tests_pass`, `tests_unmodified`, `no_new_suppressions`,
  `coverage_not_decreased`) is set to `True` or `False` — **never left `None`** — because
  `GateReport.admitted` treats `g is not False` as passing, so a forgotten gate silently admits
  (final review D20/D25). Add a conformance assert: under `gates="full"`, `admitted` requires all
  four code gates non-`None`.
- [ ] **15. CLI (G4)** — `sagiha run <goal> [--acceptance <check>...]` and
  `sagiha replay <run_id> --verify` (L0/L1 fidelity per the foundation review §10; L2 deferred).
  `--resume` is **3b** (depends on A.7 below).

### C. Security behavioral tests scoped to 3a (grant verification only)

- [ ] **16.** Unknown tool → `is_error=True` result and `ToolCallFailed`.
- [ ] **17.** Expired grant / forged `grant_id` is rejected at dispatch (regression test for B.13's
  `get_grant` verification, not new machinery).

### D. CI for 3a

- [ ] **18.** CI runs the **full** `pytest` suite with `pytest-cov` and enforces `fail_under = 80`.
- [ ] **19.** CI replay job runs `sagiha replay --verify` against the committed e2e cassette
  (replaces the always-skip stub).

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
