# ⚡ SAGIHA — Development TODO List & Status Roadmap

> **Source of Truth Alignment:** Based on [`pitch.md`](pitch.md), [`README.md`](README.md), [`docs/STATUS.md`](docs/STATUS.md), [`docs/sprints/`](docs/sprints/), and [`docs/07-roadmap/phased-migration-matrix.md`](docs/07-roadmap/phased-migration-matrix.md).
>
> **Last verified:** 2026-07-30 against `HEAD` — 47 tests pass · `pyright` 0 errors · `import-linter` 5/5 contracts kept · `ruff` clean · event catalog `--check` green.
>
> **CI policy:** local checks only for now (`pytest`, `pyright`, `lint-imports`, `ruff`) — GitHub
> Actions is intentionally not the gate yet. D28/D29 (CI doesn't run `tests/unit/`; the replay job's
> flags don't match the CLI) are real but deferred to whenever CI is turned back on — they are not
> blocking local development.

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
* **Sprint 3a: Closed Runnable Loop** — `[~] IMPLEMENTED, NOT CLOSED (2026-07-30)`
  - `sagiha run` / `sagiha replay --verify`, `RunLoop` with stop conditions, five built-in tools, digest-keyed cassettes, `GateReport`, typed event upcasters.
  - Closed: **D1, D2, D10, D11, D19, D20, D21, C1, C6, C7, C9**.
  - **Open**: CI runs no unit tests (**D29**) and the replay job's flags don't match the CLI (**D28**); tool input schema validation (D13); unknown-tool deny test. Per final review **C3**, a partial implementation on a branch does not count — 3a closes when CI enforces the exit test.
  - Carries **11 refactor debts (R1–R11)** — see register below.
* **Sprint 3a-security: Path Containment** — `[x] COMPLETED (2026-07-30)`
  - Closed **D26** (sibling-prefix / symlink escape) and **D27** (`scope_paths` collected but never enforced).
* **Sprint 3b: Hardening** — `[ ] NEXT`
  - Target: resumable state (D9), `anyio` bus quarantine + observer timeout (D17), deny-path security tests, provenance filtering (D7), NFS journal probe.

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
- [ ] **Tool Input Schema Validation** (`Sprint 3a`, D13) — validate `call.arguments` against the registered JSON Schema at dispatch; violation → `is_error=True`, handler never invoked. Schemas are stored and read for path scoping, but nothing validates against them, so handlers receive whatever the model emitted
- [ ] **Unknown-Tool Deny Test** (`Sprint 3a`, C.16) — unknown tool → `is_error=True` + `ToolCallFailed`. The one 3a checklist test never written
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
- [ ] **CI runs `tests/unit/` with `--cov`** (`Deferred — CI is off by policy`, **D29**) — `ci.yml:61` runs `tests/contracts/` only; `fail_under = 80` is configured but never applied. Local `uv run pytest -q` covers this today
- [ ] **Replay job flags match the CLI** (`Deferred — CI is off by policy`, **D28**) — `ci.yml:77` calls `--verify-all --fixtures …`; the command defines `replay <run_id> --verify`
- [ ] **OpenAI-Compatible Model Provider Adapter** (`Sprint 3a`) — local Ollama / Qwen + OpenAI endpoints, behind the existing `openai` extra. **The only Sprint 3a *feature* not landed**; `composition.py` fails closed in `live`/`record` because there is no provider to bind
- [ ] **`build_kernel` live/record binding** (`Sprint 3a`, D3) — depends on the adapter above
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
- [x] 🔁 **R7** **Short-Term Memory & In-Memory Store** (`src/sagiha/adapters/memory/short_term.py`)
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

Each of these **passes its tests today**. Each is flagged because the shape will cost more later than it does now.

| ID | Item | What is wrong | Remake as | When |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | `kernel/react.py` | Superseded by `agency/run_loop.py`. Two loop implementations coexist; the kernel one is no longer the path taken | Delete, or demote to a private helper `RunLoop` calls | Sprint 3b |
| ~~**R2**~~ | ~~Grant verification~~ | **Fixed (2026-07-30).** `PolicyEngine.verify_grant(grant_id) -> bool` is now a mandatory Protocol method; `dispatch.py` calls it unconditionally, no `getattr` | — | Closed |
| ~~**R3**~~ | ~~Path scoping fallback~~ | **Fixed (2026-07-30).** No registered schema → `authorize()` returns `allowed=False` ("cannot scope grant"); the key-name-guessing fallback is deleted | — | Closed |
| **R4** | Evaluator location | Gate evaluation lives in `agency/run_loop.py`; `outer_loop/evaluator/` is still a docstring-only package. The evaluator is TCB-adjacent and should not sit in `agency/` | Move to `outer_loop/evaluator/`, bind through the `Evaluator` port | Sprint 3b |
| **R5** | `runtime/` is empty | Tool execution lives in `adapters/tools/`. CAR's **R** has no code, so that half of the layer contract proves nothing | Move tool execution into `runtime/`, or drop **R** from the CAR story until it has code | Sprint 3b |
| **R6** | `.importlinter` still lenient | `unmatched_ignore_imports_alerting = warn` with a comment saying "revisit once `agency/` has code". `agency/` now has 305 lines | Flip to `error` — the concession is self-closing and should close | Sprint 3b |
| **R7** | `ShortTermMemoryAdapter` | Written, wired **zero** times; `composition.py` binds only `InMemoryMemory`. Dead code behind a live contract (D12) | Wire it into prompt assembly **or** delete it. Do not leave both | Sprint 3b |
| **R8** | Port stability labels | `ModelProvider` is marked `STABILITY = "stable"` while its `ModelRequest` shape just changed. The labels currently promise what the code cannot keep | Revoke `stable` on every port without a second adapter; generate the tier table from `STABILITY` and `--check` it in CI (X16) | Sprint 3b |
| **R9** | Compaction | Prompt assembly ships with no compaction algorithm — only policy prose. The first assembler will invent ad-hoc truncation and break prefix stability | Specify three numbers (headroom %, keep-first-N, keep-last-M) in `prompt-architecture.md` before assembly grows | Sprint 3b |
| **R10** | `run_command` is unsandboxed | `LocalWorkspace.run` sets `cwd` to the root but nothing confines the subprocess. Containment covers *tool paths*, not what a spawned process does | Hard product constraint: **`autonomous` autonomy stays refused until Block 5's Podman perimeter lands.** Document it as a constraint, not a footnote | Block 5 |
| **R11** | Core dependencies | `pyproject.toml` pins `mcp`, `opentelemetry-*`, `lsprotocol`, `watchfiles` while `STATUS.md` defers all of them. Dependency gravity pulls work toward the periphery | Move to optional extras (C4) | Sprint 3b |

---

## ✅ **Verification — Run These**

```sh
uv run pytest -q                                        # 47 passed
uv run pyright                                          # 0 errors (scoped to src/sagiha)
uv run lint-imports                                     # 5 contracts kept, 0 broken
uv run ruff check src/sagiha tests                      # clean
uv run ruff format --check src/sagiha tests             # clean
uv run python scripts/gen_event_catalog.py --check      # catalog up to date
uv run sagiha version
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

**Status: passes locally** (`tests/unit/test_sprint3a_e2e.py`) — with two honest caveats:

1. **It is not "in CI."** `.github/workflows/ci.yml:61` runs `pytest tests/contracts/` only, so the
   e2e test and every deny-path, path-containment, and gate test are unenforced (**D29**). The
   replay job still invokes `sagiha replay --verify-all --fixtures …`, flags the CLI does not define
   (**D28**). `fail_under = 80` is configured in `pyproject.toml` and never applied. All 47 tests
   currently guard nothing that a merge can trip over.
2. **It runs against a cassette, not a live model**, because the OpenAI-compatible adapter is not
   built yet. The loop is closed; it has not been closed *against a real model*.

Fixing (1) is the cheapest item on this page and the one that makes every other `[x]` above mean
something. Until then the sentence is demonstrated, not verified.

Work that does not serve this sentence, or the refactor register above, waits.
