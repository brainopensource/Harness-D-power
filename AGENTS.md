# SAGIHA — Agent Guidelines & Invariants

This repository houses the architecture, specification, and implementation of **SAGIHA**, a SOTA autonomous coding harness built on capability security, microkernel dispatch, and pristine evaluation gates.

## Core Architectural Invariants

1. **Capability Authorization (CAR Model)**:
   - Tool execution is gated through `PolicyEngine.authorize()`.
   - Dispatch choke point in `kernel/dispatch.py` executes authorized calls.
   - The Trusted Computing Base (TCB) consists of `sagiha.kernel.policy`, `sagiha.outer_loop.evaluator`, benchmark definitions, `.importlinter`, and CI workflows. Agents must NEVER modify TCB files.

2. **Port-Adapter Architecture**:
   - `sagiha.domain` models are pure Pydantic models with zero I/O dependencies.
   - `sagiha.ports` define typed `Protocol` boundaries with zero internal dependencies.
   - All port implementations (`adapters/`) must pass their respective port conformance test suites.
   - **Contracts live in `src/sagiha/ports/` and `src/sagiha/domain/`. `src/` is the single source of truth — code wins.** A `Protocol` or `BaseModel` defined in a `.md` file is a bug. Documentation carries rules and rationale; the definition has exactly one home — see `docs/implementation/contracts-to-code.md`.
   - **Every port must be implementable over a wire**: payloads are Pydantic-serializable, every method is `async`, and no `Path`, file handle, callable, generator, or live object crosses a boundary. See `docs/02-architecture/remoteable-ports.md`.

3. **Verification & Gates**:
   - `require_tests_unmodified`: Test suite modifications by agents are rejected by default.
   - Deterministic replay via cassettes must match step sequences byte-for-byte.
   - Hard gates admit candidates; proxies may rank but never admit, and never override a gate failure.

4. **Extension**:
   - Adapters, tools, and skills register via packaging entry points, resolved once at composition and then frozen. No runtime discovery, no filesystem scanning.
   - Extensions may never define a new port, reach past a port boundary, or widen authority.

## Codebase Conventions

- Python runtime: `>=3.13`.
- Package manager: `uv`.
- Format & Lint: `ruff format`, `ruff check --fix`, `pyright`, `lint-imports`.
- Async I/O: `anyio` structured concurrency.
