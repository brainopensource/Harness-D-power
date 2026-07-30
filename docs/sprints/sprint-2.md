# **Sprint 2: Day-Zero Baseline Kernel, Replay & MCP Driver**

> **Status**: In Progress (Core Microkernel & Dispatched Replay Complete)  
> **Target**: Baseline runnable ReAct microkernel, SQLite-WAL trajectory storage, capability dispatch choke point, stdio MCP driver, and cassette record/replay adapter.

---

## 📋 **Sprint 2 Implementation Checklist**

- [x] **1. Event Bus (`src/sagiha/kernel/bus.py`)**
  - [x] Asynchronous pub/sub event bus supporting multiple decoupled subscribers.
  - [x] Safe execution of observers without blocking event dispatch.
  - [x] Synchronous interceptors with fail-closed timeout protection on critical path.

- [x] **2. SQLite-WAL TrajectoryStore (`src/sagiha/adapters/trajectory/sqlite.py`)**
  - [x] Connection factory enforcing SQLite WAL pragmas (`PRAGMA journal_mode = WAL`, `PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`, `PRAGMA synchronous = NORMAL`).
  - [x] Append-only trajectory step and event storage (`trajectories.db`).
  - [x] DAG step tracking (`StepId(run_id, branch_id, seq, parent)`).
  - [x] Separate handling for `StepScored` events (never mutating stored steps).

- [x] **3. ShortTermMemory & Memory Adapters (`src/sagiha/adapters/memory/short_term.py`)**
  - [x] `ShortTermMemoryAdapter` over trajectory store & recent working context.
  - [x] `InMemoryMemory` implementation for durable memory port (`remember`, `recall`, `invalidate`).

- [x] **4. PolicyEngine & ResourceGovernor (`src/sagiha/kernel/policy/`, `src/sagiha/kernel/governor.py`)**
  - [x] `DefaultPolicyEngine`: Authorizes requested tool calls and mints capability `Grant` objects.
  - [x] `DefaultResourceGovernor`: Tracks spend USD limits, concurrent leases, and resource allocations.

- [x] **5. Capability Dispatch Choke Point (`src/sagiha/kernel/dispatch.py`)**
  - [x] Single entry point routing tool execution from Agency intent to Runtime effect.
  - [x] Sequence: `PolicyEngine.authorize()` → mint `Grant` → `ResourceGovernor.acquire()` → execute tool → emit event → record outcome.
  - [x] Enforces CAR invariant: `Agency` holds zero references to `Runtime` or adapter objects.

- [x] **6. Tool Registry (`src/sagiha/adapters/tools/registry.py`)**
  - [x] Tool classification with `EffectClass` (`PURE`, `IDEMPOTENT`, `DESTRUCTIVE`).
  - [x] `DefaultToolRegistry` managing tool handlers and schema verification.

- [x] **7. Record/Replay Cassette ModelProvider (`src/sagiha/adapters/model/cassette.py`)**
  - [x] Implements `ModelProvider` port supporting `live`, `record`, and `replay` modes.
  - [x] Replays recorded model responses deterministically with zero network calls in CI.

- [x] **8. Deterministic Async ReAct State Machine (`src/sagiha/kernel/react.py`)**
  - [x] `ReActEngine` execution loop: prompt assembly → model completion → parse tool calls → dispatch capability choke point → record step in trajectory.

- [x] **9. Composition Root Wiring (`src/sagiha/composition.py`)**
  - [x] Updated `build_kernel(config)` to construct and wire all Day-Zero kernel components, event bus observers, and default adapters.

- [x] **10. Conformance & Replay Test Suite (`tests/unit/test_kernel_sprint2.py`)**
  - [x] Test event bus observer and interceptor execution.
  - [x] Test SQLite trajectory store serialization and WAL connection factory.
  - [x] Test policy engine authorization and dispatch capability choke point.
  - [x] Test ReAct engine step execution and cassette replay.

---

## ⏳ **Scope Change — 2026-07-29**

The two remaining items (stdio MCP client driver, OTel telemetry subscriber) are **deferred** per
the [2026-07-29 Foundation Review](../reviews/2026-07-29-foundation-review.md) (§6, §11): both
extend the periphery while the core loop is not yet demonstrated. MCP lands in Block 5 alongside
the sandbox; OTel is an additive EventBus observer over an event stream already persisted to SQLite.

Sprint 2 is closed with **known defects** in the delivered components — see review findings D1–D18
(dead tool-dispatch branch in `react.py`, request-blind cassette replay, mode-ignoring composition,
lossy event reads, unresumable step sequence, under-specified `ModelRequest`, unvalidated tool
inputs, unwired short-term memory, non-conformant `stream()`, bus/doc drift). These are the first
work items of [Sprint 3](./sprint-3.md).
