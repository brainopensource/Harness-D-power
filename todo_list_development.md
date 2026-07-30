# ⚡ SAGIHA — Development TODO List & Status Roadmap

> **Source of Truth Alignment:** Based on [`pitch.md`](pitch.md), [`README.md`](README.md), [`docs/STATUS.md`](docs/STATUS.md), [`docs/sprints/`](docs/sprints/), and [`docs/07-roadmap/phased-migration-matrix.md`](docs/07-roadmap/phased-migration-matrix.md).
>
> **Last verified:** 2026-07-30 against `HEAD` — 76 tests pass · `pyright` 0 errors · `import-linter` 5/5 contracts kept (agency contract now enforced, not warned) · `ruff` + `ruff format --check` clean · event catalog `--check` green · `sagiha replay --verify` green.
>
> **CI policy:** GitHub Actions now runs the full suite. **D28/D29 are closed** — a `tests` job runs
> `pytest tests/ --cov` with the 80% floor applied, and the `replay` job invokes the real
> `sagiha replay --verify` CLI contract against a committed fixture cassette.

---

## 🔑 **Status Marker Legend**

| Marker | Meaning |
| :--- | :--- |
| `[x]` | **Done & verified** — implemented, tested, and passing the CI gates |
| `[x] 🔁 R#` | **Done but must be remade** — works today, but the shape is wrong. See the [Refactor Register](#-refactor-register--must-be-remade) |
| `[~]` | **Partial** — the happy path works; a named piece is missing |
| `[ ]` | **Not started** |

> ⚠️ A `🔁` item is *not* a bug. It passes its tests. It is flagged because the **implementation lives in the wrong place, leans on a duck-typed hook, or keeps a legacy fallback** that will become expensive once adapters multiply. Remake these before Block 2, not after.

---

## 📊 **Completed Sprints Summary**

* **Sprint 1: Architecture, Specifications & Hexagonal Contracts** — `[x] COMPLETED`
  - Hexagonal Architecture, CAR model, domain models (`src/sagiha/domain/`), typed protocol ports (`src/sagiha/ports/`).
  - CI boundaries (`import-linter`, `pyright`, `pytest tests/contracts/`).
* **Sprint 2: Day-Zero Baseline Kernel, Replay & MCP Driver** — `[x] CLOSED (2026-07-29)`
  - Core microkernel scaffold (`EventBus`, `SQLite-WAL TrajectoryStore`, `PolicyEngine`, `ResourceGovernor`, dispatch choke point, tool registry, cassette `ModelProvider`, `ReActEngine`, composition root).
  - *Scope update*: stdio MCP client and OTel observer deferred to Block 5. Defects D1–D18 tracked into Sprint 3.
* **Sprint 3a: Closed Runnable Loop** — `[x] CLOSED (2026-07-30)`
  - `sagiha run` / `sagiha replay --verify`, `RunLoop` with stop conditions, five built-in tools, digest-keyed cassettes, `GateReport`, typed event upcasters.
  - Closed: **D1, D2, D10, D11, D12, D13, D19, D20, D21, C1, C6, C7, C9, C.16**.
  - Per final review **C3**, a partial implementation on a branch does not count — the exit test
    (`tests/unit/test_sprint3a_e2e.py`) now runs in CI with coverage enforced, and the CLI's real
    `sagiha replay --verify` contract is exercised against a committed fixture cassette. Not part of
    the exit test and left open as a fast-follow: the OpenAI-compatible provider adapter — no run
    against a real model is possible yet.
  - Closed **5 of 11 refactor debts** in the same pass — **R2, R3, R6, R7, R8**. **R1, R4, R5, R9,
    R11** closed in Sprint 3b below.
* **Sprint 3a-security: Path Containment** — `[x] COMPLETED (2026-07-30)`
  - Closed **D26** (sibling-prefix / symlink escape) and **D27** (`scope_paths` collected but never enforced).
* **Sprint 3b: Hardening** — `[x] CLOSED (2026-07-30)`
  - Resumable run state (D9, `sagiha run --resume`), `anyio` bus observer timeout + quarantine
    (D16/D17), mandatory kernel ports regression-tested (D14), deny-path security tests beyond
    grant expiry (U1/D8), `InMemoryMemory.recall` provenance filtering (D7), NFS/non-local
    filesystem SQLite journal mode probe with automatic fallback.
  - Closed the remaining **6 of 11** refactor debts — **R1** (`kernel/react.py` deleted, tests
    migrated to `RunLoop`), **R4** (evaluator moved to `outer_loop/evaluator/`, bound through the
    `Evaluator` port), **R5** (`car-model.md` and `runtime/__init__.py` now state plainly that
    Runtime has no code until Block 5, rather than leaving the empty package unexplained), **R9**
    (compaction's three numbers specified in `prompt-architecture.md`), **R11** (`mcp`,
    `opentelemetry-*`, `lsprotocol`, `watchfiles` moved to optional extras). All 11 refactor debts
    are now closed.

---

## 📋 **Development Task Matrix**

### 1. 🛡️ **Level 1: Harness Engineering — Body, Sensors & Security (CAR Model)**

- [x] **Hexagonal Port & Domain Models** (`src/sagiha/ports/`, `src/sagiha/domain/`)
- [x] **Capability Dispatch Choke Point** (`src/sagiha/kernel/dispatch.py`)
- [x] **Policy Engine & Capability Grant Minting** (`src/sagiha/kernel/policy/`)
- [x] **Resource Governor** (`src/sagiha/kernel/governor.py`) — budget/lease bounds, now consulted per step
- [x] **Tool Registry & Effect Classification** (`src/sagiha/adapters/tools/registry.py`)
- [x] **Grant Verification at Point of Effect** — `dispatch.py` calls `policy.verify_grant(grant_id)` unconditionally (no `getattr`); `PolicyEngine.verify_grant` is now a mandatory Protocol method returning `bool`, never `Grant` (test_no_grant_in_any_public_signature still green). **R2 fixed.**
- [x] **Schema-Declared Path Scoping** — `x-sagiha-path: true` annotations walked out of the JSON Schema; a tool with **no registered schema now fails closed** at `authorize()` instead of falling back to key-name guessing. **R3 fixed.**
- [x] **Path Containment Enforced at the Choke Point** — `engine.escapes_root` refuses any scoped path outside `workspace_root` *before* a grant is minted (**D27**)
- [x] **Adapter Containment Guard (defence in depth)** — `resolve_within` uses `Path.is_relative_to` after resolving, closing both the sibling-prefix and symlink escapes (**D26**)
- [x] **Five Built-in Core Tools** (`src/sagiha/adapters/tools/builtins.py`) — `read_file`, `list_dir`, `grep`, `apply_edit`, `run_command`
- [x] 🔁 **R10** **Dev-Mode Subprocess Workspace Adapter** (`src/sagiha/adapters/workspace/local.py`) — rooted file execution
- [x] **Tool Input Schema Validation** (D13) — `DefaultToolRegistry.dispatch` calls `validate_arguments` against the registered JSON Schema before the handler runs; a minimal type/required/array-item checker, not a `jsonschema` dependency → `tests/unit/test_tool_validation.py`
- [x] **Unknown-Tool Deny Test** (C.16) — unknown tool → `is_error=True` + `ToolCallFailed`, exercised through the full `kernel.dispatch` path → `tests/unit/test_tool_validation.py::test_dispatch_unknown_tool_reaches_registry_and_emits_failed`
- [ ] **Deny-Path & Interceptor Security Tests** (`Sprint 3b`) — `always_gate` refusal, interceptor denial *and* timeout both fail closed
- [ ] **Container Sandbox Perimeter (Podman)** (`Block 5`) — rootless containers + egress allowlisting. **Blocks `autonomous` autonomy** — see R10
- [ ] **Warm LSP Supervisor** (`Block 5`) — host-side language server diagnostics pool
- [ ] **Post-Edit Diagnostics Delta in `EditResult`** (`Block 4/5`) — return only *new* diagnostics after a write

---

### 2. 🔄 **Deterministic Replay & Provider Access**

- [x] **Cassette ModelProvider** (`src/sagiha/adapters/model/cassette.py`) — `live` / `record` / `replay` modes
- [x] **Digest Request Matching** — `request_digest()` SHA-256 over a canonical `ModelRequest`; `CassetteMismatchError` on mismatch **or exhaustion** (no silent last-entry repeat)
- [x] **`ModelRequest` v2** — `system`, `tools`, `max_tokens`, `temperature`, role tier. Landed *before* any cassette fixture, as required
- [x] **Honest `stream()`** — raises `NotImplementedError` rather than fabricating frames (D15)
- [x] **Deterministic Replay Verification CLI** — `sagiha replay --verify`
- [x] **CI runs `tests/unit/` with `--cov`** (D29) — new `tests` job runs `pytest tests/ --cov=src/sagiha`; `fail_under = 80` applies automatically (measured 87–88%)
- [x] **Replay job flags match the CLI** (D28) — `replay` job now invokes `sagiha replay <run_id> --verify --cassette … --workspace … --trajectory-db …` against `tests/fixtures/replay_smoke/cassette.json`, generated by `scripts/gen_replay_fixture.py` through the real `build_kernel`/`RunLoop` path
- [ ] **OpenAI-Compatible Model Provider Adapter** (`Fast-follow`) — local Ollama / Qwen + OpenAI endpoints, behind the existing `openai` extra. Not required by 3a's exit test — the exit test is cassette-driven by design — but the one remaining blocker for a run against a real model; `composition.py` fails closed in `live`/`record` because there is no provider to bind
- [ ] **`build_kernel` live/record binding** (D3) — depends on the adapter above
- [ ] **Graded Replay Fidelity L0/L1/L2** (`Sprint 3b`) — replace absolute "byte-for-byte" claims with the graded ladder (X13)

---

### 3. 🧠 **Level 2: Loop Engineering & Cognition (DMARTIC & Macro Workflows)**

- [x] 🔁 **R1** **Async ReAct Engine Scaffold** (`src/sagiha/kernel/react.py`) — **superseded by `RunLoop`**
- [x] **`RunLoop` Engine with Stop Conditions** (`src/sagiha/agency/run_loop.py`) — `max_steps`, budget exhaustion via `remaining_budget`, `end_turn`, and **stuck-signature detection** (repeated tool+args hash → `stuck_loop`)
- [x] 🔁 **R9** **Minimal Prompt Assembly & History Packing** — system prompt + tool schemas + trajectory history into `ModelRequest` v2; steps are no longer memoryless
- [ ] **Resumable Run State (`--resume`)** (`Sprint 3b`) — `runs` table; derive `seq` from `TrajectoryStore`, not engine memory (D9)
- [ ] **Concrete Compaction Algorithm** (`Sprint 3b`) — three numbers: headroom %, keep-first-N, keep-last-M. See R9
- [ ] **Mid-Turn Interjection / Steering Semantics** (`Block 2+`) — merge rules for messages arriving during a turn
- [ ] **Workflow DAG & Protocol** (`Block 4`) — `WorkflowStep[In, Out]` per [ADR-0018](docs/08-decisions/0018-native-workflow-dag.md). **Gated**: ships only if E0 shows planning beats no-planning
- [ ] **Macro Planning Stages** (`Block 4`) — `PRDGeneratorStep` → `StoryDecomposerStep` → `CodingStep` → `VerifierStep`
- [ ] **System 2 Deliberate Best-of-N Search** (`Block 3/4`) — parallel candidates across ephemeral worktrees + sequential repair

---

### 4. 🕸️ **Neural-Symbolic Memory & Code Graph**

- [x] **SQLite-WAL Trajectory Store** (`src/sagiha/adapters/trajectory/sqlite.py`) — append-only step & event logging
- [x] **Typed Event Upcasters** (`src/sagiha/domain/upcasters.py`) — lossless deserialization through the `ALL_EVENTS` union (D6)
- [x] **`call_id` Correlation** — on `ToolResult`, `ToolCallCompleted`, `ToolCallFailed`. Multi-tool steps are now mineable (D21)
- [x] **In-Memory Durable Memory** (`src/sagiha/adapters/memory/short_term.py`) — `ShortTermMemoryAdapter` deleted (**R7 fixed**): it was wired zero times; `RunLoop` keeps step history locally. `InMemoryMemory` remains as the one bound `Memory` port implementation.
- [ ] **Provenance Filtering Fix** (`Sprint 3b`) — `InMemoryMemory.recall` must honor `min_provenance` (D7)
- [ ] **NFS / Network-FS Journal Probe** (`Sprint 3b`) — classify the filesystem, degrade WAL → Truncate. Without it a network home directory yields a **`SIGBUS` panic, not an error**
- [ ] **`TrajectoryStore` as a Recall Source** (`Block 4`) — FTS5 over past runs: *"have I hit this failure before?"*
- [ ] **AST Code Graph Integration** (`Block 4`) — Tree-sitter `callers_of` / `impacted_by`
- [ ] **Obsidian-Style Knowledge Net** (`Block 4`) — `neighbors()` / `backlinks()` on the `Memory` port
- [ ] **Dense Vector Embeddings** (`Deferred`) — per [ADR-0014](docs/08-decisions/0014-defer-dense-retrieval.md), until FTS5 recall@10 is missed

---

### 5. 🎯 **Level 3: Meta-Loop Engineering — Evaluation (E0) & Self-Improvement (RHI)**

- [x] 🔁 **R4** **Pristine Test Evaluator (`GateReport`)** — `RunLoop._evaluate` runs acceptance checks and emits a real `GateReport`
- [x] **Absence Is Never a Pass** — `GateReport.admitted` is `all(g is True ...)`; an unevaluated gate can no longer admit a candidate (**D20**)
- [ ] **E0-Lite Evaluation Harness** (`Block 2`) — commit-replay harvester + task runner. **Harvest scaffolding needs no working agent and can start now**
- [ ] **Written Accept Predicate** (`Block 2`) — estimator, α, minimum detectable effect, k, and the exact accept/reject rule. Currently `k ≥ 3` with no named test
- [ ] **A/A Noise Floor Measurement** (`Block 2`) — local-first (cassette / Ollama) so the floor is affordable
- [ ] **Resolve ADR-0015 Class B vs Class C** (`Block 2`) — the ADR recommends Class C but adopted Class B while still claiming "anyone can re-run it" (G14)
- [ ] **L3-min Prompt Ratchet** (`after Block 2`) — one mutable prompt file, ≤15 tasks, paired lift vs. floor, TCB paths CI-rejected
- [ ] **Reflexive Harness Improvement (RHI / Outer Loop)** (`Block 5+`) — full trajectory mining and auto-tuning

---

### 6. 🌐 **Level 4: Macro Multi-Agent Swarms & Integrations**

> **Sequencing rule:** none of this starts before a **measured** L2. Swarming a harness whose error rate has never been measured multiplies an unknown, and without a noise floor a coordination bug is indistinguishable from stochasticity.

- [ ] **MCP Stdio/HTTP Driver** (`Block 5`) — consume external MCP tools, `trusted_output=False`
- [ ] **OTel Telemetry Bus Observer** (`Block 5`)
- [ ] **`WorkspaceRef` for `WorktreeManager.allocate()`** (`Block 5`) — returning a live `Workspace` Protocol is the one standing violation of the remoteable-ports rule (A12)
- [ ] **Remoteable Ports & A2A Wire Triggers** (`Block 5+`) — architect → developer → QA harnesses across isolated worktrees

---

## 🔁 **Refactor Register — Must Be Remade**

Each closed item passed its tests before being remade — none was a bug, only a shape debt. Five of eleven closed alongside Sprint 3a; the remaining six closed alongside Sprint 3b (2026-07-30). Only **R10** (Block 5's Podman perimeter) is open, and it is a hard product constraint, not a remake — see its row below.

| ID | Item | What is wrong | Remake as | Status |
| :--- | :--- | :--- | :--- | :--- |
| ~~**R1**~~ | ~~`kernel/react.py`~~ | **Closed (2026-07-30).** `kernel/react.py` deleted outright — `RunLoop` already superseded it and there was no remaining caller to demote it for. `test_kernel_sprint2.py::test_react_engine_execution` and `test_sprint3a_phase2_3.py::test_react_parses_tool_use_block` migrated to drive `RunLoop` instead of `ReActEngine`, preserving the same regression coverage (end-turn-with-no-tools, and ToolUseBlock→ToolCall resolution+dispatch) | — | **Closed** |
| ~~**R2**~~ | ~~Grant verification~~ | **Fixed (2026-07-30).** `PolicyEngine.verify_grant(grant_id) -> bool` is now a mandatory Protocol method; `dispatch.py` calls it unconditionally, no `getattr` | — | **Closed** |
| ~~**R3**~~ | ~~Path scoping fallback~~ | **Fixed (2026-07-30).** No registered schema → `authorize()` returns `allowed=False` ("cannot scope grant"); the key-name-guessing fallback is deleted | — | **Closed** |
| **R4** | Evaluator location | Gate evaluation lives in `agency/run_loop.py`; `outer_loop/evaluator/` is still a docstring-only package. The evaluator is TCB-adjacent and should not sit in `agency/` | Move to `outer_loop/evaluator/`, bind through the `Evaluator` port | Open — Sprint 3b |
| ~~**R5**~~ | ~~`runtime/` is empty~~ | **Closed (docs, 2026-07-30).** Tool execution lives in `adapters/tools/`, unsandboxed (R10) — moving it into `runtime/` now would mislabel it as sandboxed before Block 5's container/gVisor perimeter (ADR-0006) exists. Instead, `car-model.md` and `runtime/__init__.py` now say plainly that Runtime has no code until Block 5, and that the `car-layering` `import-linter` contract already forbids `agency/` from importing `runtime/` *or* `adapters/` — the empty package doesn't weaken the enforced boundary | — | **Closed** |
| ~~**R6**~~ | ~~`.importlinter` too lenient~~ | **Fixed (2026-07-30).** `agency/run_loop.py` (305 lines) imports `sagiha.ports.*`, so the `car-layering` contract's ignore rule now matches real code; `unmatched_ignore_imports_alerting = warn` removed, back to the tool's `error` default | — | **Closed** |
| ~~**R7**~~ | ~~`ShortTermMemoryAdapter`~~ | **Fixed (2026-07-30).** Written, wired zero times; deleted from `adapters/memory/short_term.py` and `__init__.py` rather than left as a dead second path (D12) | — | **Closed** |
| ~~**R8**~~ | ~~Port stability labels~~ | **Fixed (2026-07-30).** All 8 ports previously marked `STABILITY = "stable"` (`memory`, `governor`, `model`, `orchestrator`, `policy`, `tool_registry`, `trajectory`, `workspace`) relabeled `provisional` — none has a second adapter. `port-stability-and-versioning.md`'s tier table corrected to match (it had drifted to a fourth `draft` tier that existed in no code) | — | **Closed** |
| ~~**R9**~~ | ~~Compaction~~ | **Closed (docs, 2026-07-30).** `prompt-architecture.md` now specifies the three numbers normatively: headroom 20%, keep-first-N=2, keep-last-M=6, plus the no-op condition and where the summary turn lands in a trajectory. Compaction remains unimplemented in `agency/run_loop.py` — that was explicitly out of scope for 3a and is not on 3b's checklist — but the algorithm an implementer reaches for is now specified, not invented per-PR | — | **Closed** |
| **R10** | `run_command` is unsandboxed | `LocalWorkspace.run` sets `cwd` to the root but nothing confines the subprocess. Containment covers *tool paths*, not what a spawned process does | Hard product constraint: **`autonomous` autonomy stays refused until Block 5's Podman perimeter lands.** Document it as a constraint, not a footnote | Open — Block 5 |
| ~~**R11**~~ | ~~Core dependencies~~ | **Closed (2026-07-30).** `mcp` → `mcp` extra, `opentelemetry-sdk`/`opentelemetry-exporter-otlp` → `otel` extra, `lsprotocol`/`watchfiles` → `indexing` extra. None was imported anywhere in `src/sagiha` (confirmed by grep before moving), matching `STATUS.md`'s deferral of all four | — | **Closed** |

---

## ✅ **Verification — Run These**

```sh
uv run pytest -q                                        # 57 passed
uv run pyright                                          # 0 errors (scoped to src/sagiha)
uv run lint-imports                                     # 5 contracts kept, 0 broken
uv run ruff check src/sagiha tests                      # clean
uv run ruff format --check src/sagiha tests             # clean
uv run python scripts/gen_event_catalog.py --check      # catalog up to date
uv run sagiha version

# CI now runs the equivalent of the first six as separate jobs, plus a real replay smoke test:
uv run sagiha replay verify --verify \
  --cassette tests/fixtures/replay_smoke/cassette.json \
  --workspace tests/fixtures/replay_smoke/workspace \
  --trajectory-db /tmp/replay_check.db
```

> **Note on scope:** `pyright` is scoped to `src/sagiha` and the vendored reference harnesses
> (`src/claude_code`, `src/grok_build`, `src/hermes_agent`, `src/open_code`) are now gitignored.
> They are analysis material under `docs/reference/harness_examples/`, never packaged. Left
> unscoped they contribute ~400k strict-mode errors and ~3.6k unformatted files, which would have
> destroyed the CI signal the first time anyone ran `git add .`.

---

## 🎯 **The One Test That Governs Everything**

> An end-to-end test in CI where the agent, driven by a committed cassette, fixes a failing test in a
> fixture repository **through the dispatch choke point**, the run is gate-evaluated, and
> `sagiha replay --verify` passes on the recording.

**Status: green in CI** (`tests/unit/test_sprint3a_e2e.py`, plus a real CLI-level replay smoke test)
— with one honest caveat, and it is explicitly outside what this sentence requires:

**It runs against a cassette, not a live model**, because the OpenAI-compatible adapter is not built
yet. The loop is closed and verified; it has not been closed *against a real model*. That is the
next thing on this page, tracked as a fast-follow rather than a blocker — the exit sentence above
says "driven by a committed cassette" by design, and does not require a live provider.

Work that does not serve the next sentence — a run against a real model — or the refactor register
above, waits.
