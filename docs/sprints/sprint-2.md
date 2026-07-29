# **Sprint 2: Day-Zero Baseline Kernel, Replay & MCP Driver**

> **Status**: In Progress  
> **Target**: Baseline runnable ReAct microkernel, SQLite-WAL trajectory storage, capability dispatch choke point, stdio MCP driver, and cassette record/replay adapter.

---

## 📋 **Sprint 2 Implementation Checklist**

- [ ] **1. Event Bus (`sagiha/kernel/bus.py`)**
  - [ ] Asynchronous pub/sub event bus supporting multiple decoupled subscribers.
  - [ ] Safe execution of observers without blocking event dispatch.
  - [ ] Full support for domain events defined in `sagiha.domain.events`.

- [ ] **2. SQLite-WAL TrajectoryStore (`sagiha/adapters/trajectory/sqlite.py`)**
  - [ ] Connection factory enforcing SQLite WAL pragmas (`PRAGMA journal_mode = WAL`, `PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`, `PRAGMA synchronous = NORMAL`).
  - [ ] Append-only trajectory event storage (`trajectories.db`).
  - [ ] DAG step tracking (`StepId(run_id, branch_id, seq, parent)`).
  - [ ] Separate handling for `StepScored` events (never mutating stored steps).

- [ ] **3. ShortTermMemory Adapter (`sagiha/adapters/memory/short_term.py`)**
  - [ ] Implements `Memory` port over trajectory store & recent working context.
  - [ ] Exposes `recall` and `remember` for windowed working context.

- [ ] **4. PolicyEngine & ResourceGovernor (`sagiha/kernel/policy/`, `sagiha/kernel/governor.py`)**
  - [ ] `PolicyEngine`: Authorizes requested tool calls and mints capability `Grant` objects.
  - [ ] `ResourceGovernor`: Tracks max concurrent runs, step limits, wall clock time, and spend USD limits.

- [ ] **5. Capability Dispatch Choke Point (`sagiha/kernel/dispatch.py`)**
  - [ ] Single entry point for all tool execution and effects.
  - [ ] Sequence: `PolicyEngine.authorize()` → mint `Grant` → `ResourceGovernor.acquire()` → execute tool → emit event → record outcome.
  - [ ] Enforces CAR invariant: `Agency` holds zero references to `Runtime` or adapter objects.

- [ ] **6. Tool Registry & Stdio MCP Driver (`sagiha/adapters/tools/`, `sagiha/adapters/mcp/`)**
  - [ ] Tool classification with `EffectClass` (`PURE`, `READ_ONLY`, `MUTATING`, `SYSTEM`).
  - [ ] Stdio MCP client driver for spawning and communicating with MCP servers.
  - [ ] Builtin tools: filesystem (`read_file`, `write_file`, `list_dir`) and shell command execution.

- [ ] **7. Record/Replay Cassette ModelProvider (`sagiha/adapters/model/cassette.py`)**
  - [ ] Implements `ModelProvider` port supporting `live`, `record`, and `replay` modes.
  - [ ] Replays recorded model responses and re-executes `PURE` tool calls deterministically without network calls.

- [ ] **8. Deterministic Async ReAct State Machine (`sagiha/kernel/react.py`)**
  - [ ] Core execution loop: context assembly → model prompt → response parsing → dispatch tool call → receive observation → update memory → completion check.

- [ ] **9. Composition Root Wiring (`sagiha/composition.py`)**
  - [ ] Update `build_kernel(config)` to construct and wire all Day-Zero kernel components and adapters.

- [ ] **10. Conformance & Replay Test Suite (`tests/unit/`, `tests/contracts/`)**
  - [ ] Test event bus sub/pub.
  - [ ] Test SQLite trajectory store serialization and WAL connection factory.
  - [ ] Test policy engine and dispatch authorization.
  - [ ] Test cassette record/replay determinism.
