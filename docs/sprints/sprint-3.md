# **Sprint 3: Close the Loop — First Runnable, Replayable, Measured Agent Step Chain**

> **Status**: Planned
> **Source**: [2026-07-29 Foundation Review](../reviews/2026-07-29-foundation-review.md) — Block 1.
> **Target**: `sagiha run` completes a small coding task end-to-end on a cassette in CI and against
> local Ollama manually; `sagiha replay` verifies the recording. No new ports, no new subsystems.
>
> **Exit test (the only definition of done)**: an e2e test in CI where the agent, driven by a
> committed cassette, fixes a failing test in a fixture repo through the dispatch choke point,
> the run is gate-evaluated, and `sagiha replay --verify` passes on the recording.

---

## 📋 **Sprint 3 Implementation Checklist**

### A. Kernel defect fixes (review findings D1–D6, D9–D18 — do these first)

- [ ] **1. Tool-call parsing (D1)** — `kernel/react.py` must collect `ToolUseBlock` from
  `Message.content` and resolve it to a `ToolCall`, with `effect` taken from
  `ToolRegistry.get_effect_class(tool_name)`, never from model output (D11).
  - [ ] Regression test: a cassette response containing a `tool_use` block results in a dispatched
    tool and a `ToolResult` recorded in the step.
- [ ] **2. `ModelRequest` v2 (D10)** — add `system: str`, `tools: list[ToolSchema]` (name,
  description, JSON schema), `max_tokens`, `temperature`, and a `role: str` tier reference.
  **Must land before any cassette fixture is committed** — cassettes embed this shape.
- [ ] **3. Cassette request matching (D2)** — key replay on a canonical request digest; raise
  `CassetteMismatchError` on mismatch or exhaustion (no silent repeat of the last entry).
- [ ] **4. `build_kernel` honors `model.mode` (D3)** — `live` binds the OpenAI-compatible adapter
  (task B3), `record` wraps it in the cassette recorder, `replay` requires a cassette path;
  misconfiguration fails at composition, not at first call.
- [ ] **5. Typed event read path (D6)** — deserialize stored events through the `ALL_EVENTS`
  discriminated union so `events_for_run` returns concrete event types with payloads intact.
- [ ] **6. Failure signaling (D5)** — add `is_error: bool` to `ToolResult`; dispatch emits
  `ToolCallFailed` on error, `ToolCallCompleted` on success regardless of truncation; handler
  exceptions surface as `is_error=True`, not prose.
- [ ] **7. Resumable run state (D9)** — add a `runs` table (run_id, task, status, updated_at);
  derive step `seq` from `TrajectoryStore`, not engine memory; `sagiha run --resume <run_id>`
  continues without seq collisions.
- [ ] **8. Tool input validation (D13)** — validate `call.arguments` against the registered JSON
  Schema at dispatch; schema violation → `is_error=True` result, handler never invoked.
- [ ] **9. Bus correctness (D16, D17)** — construct one `ToolCallRequested` instance for both emit
  and intercept; add observer timeout + quarantine (doc-specified behavior in
  `event-bus-and-hooks.md`); replace raw `asyncio` primitives with `anyio` per AGENTS.md.
- [ ] **10. Kernel required ports non-optional (D14)** — `model_provider`, `policy_engine`,
  `resource_governor`, `tool_registry`, `trajectory_store` become mandatory; `build_kernel` fails
  at composition when unbindable. Profile-optional ports stay `| None`.
- [ ] **11. Honest cassette `stream()` (D15)** — raise `NotImplementedError` (streaming is a sprint
  non-goal) rather than fabricating a non-conformant frame sequence.
- [ ] **12. Wire or delete `ShortTermMemoryAdapter` (D12)** — if B2 prompt assembly reads history
  through it, bind it in composition and add a `Kernel` field; otherwise delete it.

### B. Minimum closed loop (review gaps G1, G2, G7, G8, G9)

- [ ] **1. Run loop** — `RunLoop.run(task: TaskSpec, ctx: RunContext)` iterating
  `step()` with explicit stop conditions: model `end_turn`, `max_steps_per_run`, budget exhausted
  (governor consulted per step — wires `record_spend`/`remaining_budget`, currently dead code),
  cancellation. Emits `RunStarted`/`StepStarted`/`StepCompleted`/`ModelCallStarted`/
  `ModelCallCompleted`/`RunCompleted|RunFailed` (G9).
- [ ] **2. Minimal prompt assembly (G7, D18)** — system prompt template + tool schemas + trajectory
  history (prior steps and tool results — today each step is memoryless) packed into
  `ModelRequest` v2. Stable prefix ordering per `docs/02-architecture/prompt-architecture.md`;
  compaction and cache breakpoints are **out of scope**.
- [ ] **3. OpenAI-compatible `ModelProvider` adapter (G8)** — one adapter covering Ollama/Qwen
  local (`base_url`) per `docs/06-guides-and-patterns/ollama-qwen-coder-setup.md`. Anthropic/Google
  adapters are out of scope.
- [ ] **4. Built-in tools (G2)** — exactly five, registered at composition from the profile's tool
  list: `read_file`, `list_dir`, `grep`, `apply_edit` (uses `EditRequest`/`EditResult`),
  `run_command`. Implemented over a dev-mode subprocess `Workspace` adapter rooted at
  `workspace.root` (container sandbox is Sprint 5 / Block 5).
- [ ] **5. Minimal `Evaluator` (G3)** — runs each `AcceptanceCriterion.check` via the workspace,
  produces a real `GateReport`, emits `GateEvaluated`; code-specific gates stay `None` this sprint.
- [ ] **6. CLI (G4)** — `sagiha run <goal> [--acceptance <check>...] [--resume <run_id>]` and
  `sagiha replay <run_id> --verify` (L0/L1 fidelity per review §10; L2 deferred).

### C. Security behavioral tests (review U1, D8 — tests, not new machinery)

- [ ] **1.** Deny path: a tool in `always_gate` is refused with `requires_human=True` and emits
  `ToolCallDenied`.
- [ ] **2.** Unknown tool → `is_error=True` result and `ToolCallFailed`.
- [ ] **3.** Interceptor denial and interceptor timeout both block execution (fail-closed).
- [ ] **4.** Expired grant / forged `grant_id` is rejected at `record_outcome` correlation.
  Full path-scope enforcement is Block 3 — out of scope here.

### D. CI & hygiene (review G5, X-findings)

- [ ] **1.** CI runs the **full** `pytest` suite with `pytest-cov` and enforces `fail_under = 80`.
- [ ] **2.** CI replay job runs `sagiha replay --verify` against the committed e2e cassette
  (replaces the always-skip stub).
- [ ] **3.** Delete duplicated contract definitions from
  `docs/03-contracts-and-models/task-and-acceptance.md` and
  `docs/02-architecture/neural-symbolic-memory.md`; replace with `src/` references. If
  `neighbors`/`backlinks` are still wanted on the `Memory` port, record that as a port change
  proposal, not a doc code fence.
- [ ] **4.** Fix `InMemoryMemory.recall` to honor `min_provenance` (D7) with a test.

---

## 🚫 **Explicit Non-Goals (deferred per review §6)**

Stdio MCP driver and OTel exporter (moved out of Sprint 2 scope), container sandbox, worktree
manager, LSP, retrieval/indexing, dense embeddings (ADR-0014), best-of-N with N>1, model routing
beyond role→tier lookup, AOI, RHI, prompt caching/compaction, A2A, **streaming** (D15 —
`stream()` raises honestly this sprint; conformant streaming lands with the first UI consumer).

## 📏 **Sprint Metrics (recorded from the event log, per review §10)**

- E2E cassette task: success, steps, wall-clock.
- Live Ollama smoke run: success, steps, wall-clock, token usage (documented in the PR, not gated).
- Replay fidelity level achieved (target: L1).
- Coverage % (gate: ≥80).

## ⛓️ **Dependency**

Sprint 2 kernel as-is. Sprint 4 (E0-lite benchmark harness, review Block 2) builds directly on
this sprint's CLI and event log.
