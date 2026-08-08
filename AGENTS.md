# AETHER — Agent Guidelines & Invariants

This repository houses the architecture, specification, and implementation of **AETHER**, a SOTA autonomous coding harness built on capability security, microkernel dispatch, and pristine evaluation gates. Full spec: [`docs/spec.md`](docs/spec.md).

## Core Architectural Invariants

1. **Capability Authorization (CAR Model)**:
   - Tool execution is gated through `PolicyEngine.authorize()`.
   - Dispatch choke point in `kernel/dispatch.py` executes authorized calls: `authorize → verify grant → acquire lease → dispatch → release`. Verification happens immediately before the effect, not at authorization time (I5).
   - The Trusted Computing Base (TCB) consists of `aether.kernel` (dispatch, bus, governor, policy), `aether.measurement` (evaluator, gates, statistics, runner), `aether.workflow` (schema, validator, executor), benchmark and task-manifest definitions, `.importlinter`, and CI workflows. Agents must NEVER modify TCB files.

2. **Port-Adapter Architecture**:
   - `aether.domain` models are pure Pydantic models with zero I/O dependencies (I1).
   - `aether.ports` define typed `Protocol` boundaries with zero internal dependencies (I2).
   - All port implementations (`adapters/`) must pass their respective port conformance test suites (I4).
   - **Contracts live in `src/aether/ports/` and `src/aether/domain/`. `src/` is the single source of truth — code wins.** A `Protocol` or `BaseModel` defined in a `.md` file is a bug. Documentation carries rules and rationale; the definition has exactly one home — see [`docs/spec.md`](docs/spec.md) §4.
   - **Every port must be implementable over a wire**: payloads are Pydantic-serializable, every method is `async`, and no `Path`, file handle, callable, generator, or live object crosses a boundary (I3).
   - **TCB port residency**: implementations of TCB ports live inside TCB paths — `PolicyEngine` in `kernel/`, `Evaluator` in `measurement/`. Never in `adapters/`.

3. **Verification & Gates**:
   - `tests_unmodified`: the agent that writes code cannot modify the tests grading it (I7). Test suite modifications by agents are rejected by default.
   - Deterministic replay via cassettes must match step sequences byte-for-byte.
   - Hard gates admit candidates; proxies may rank but never admit, and never override a gate failure (I9).

4. **Extension**:
   - Adapters, tools, and skills register via packaging entry points, resolved once at composition and then frozen. No runtime discovery, no filesystem scanning (I6).
   - Extensions may never define a new port, reach past a port boundary, or widen authority.

## Codebase Conventions

- Python runtime: `>=3.13,<3.14`.
- Package manager: `uv` — `uv.lock` committed, `uv sync --frozen` in CI.
- Format & Lint: `ruff format`, `ruff check --fix`, `pyright --strict`, `lint-imports` (import-linter).
- Async I/O: stdlib `asyncio` with `TaskGroup`, `asyncio.timeout`, `ExceptionGroup` handling. **No `anyio`, no `trio`** — rejected explicitly, see [`docs/development/tech_stack_and_infra.md`](docs/development/tech_stack_and_infra.md).

## Migration note

`src/aether/` is the only target for new code; it is currently empty (see [`docs/STATUS.md`](docs/STATUS.md)). `src/sagiha/` is predecessor reference material being retired — do not add to it. Front-end code lives under `src_front/` and imports as `@aether/core`; see [`docs_front/spec.md`](docs_front/spec.md). CI's `.importlinter` and `TCB_PATHS` are still keyed to `sagiha` paths pending the first `src/aether/` file landing in the same change (owner: `TASK-000`, [`docs/agile/backlog.md`](docs/agile/backlog.md), M0 Exit Gate 0) — do not treat that as license to write new `sagiha.*` code.
