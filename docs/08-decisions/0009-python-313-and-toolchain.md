---
status: normative
updated: 2026-07-29
---
# ADR-0009: Python ≥3.13 and Toolchain

**Status**: Accepted
**Date**: 2026-07-28

## Context
Sprint 1 cannot start with the runtime, package manager, type checker, and test stack unfixed. Leaving them open guarantees they get decided ad hoc and inconsistently.

## Decision
Python `>=3.13`, no upper cap (SAGIHA is an application pinned by a committed `uv.lock`; caps on applications only create resolver friction). Package manager **uv**. Lint and format **ruff**. Type checking **pyright strict as the blocking CI gate**, with **mypy strict as a non-blocking second opinion**. Testing **pytest ≥8.3** with **pytest-asyncio ≥0.24**. Layer enforcement **import-linter**.

pyright is canonical because it is the same engine the agent consumes through `LSPAdapter` — so the harness's self-check and the diagnostics the agent sees while editing can never disagree. Running both checkers as blocking gates is a known failure mode: they differ at the edges and the resolution is invariably a cast written to satisfy a tool rather than to express intent.

Python 3.13 additionally ships the free-threaded build (PEP 703), which is directly relevant: GIL contention during Tree-sitter parsing was the strongest argument for compiled sidecars, and this attacks it without leaving Python. It should be benchmarked before any Rust rewrite is funded.

## Consequences
Zero open toolchain questions at Sprint 1. A recurring mypy-only finding can be promoted to blocking case by case.

## Reversal Conditions
A required C-extension dependency lacking 3.13 support; or pyright licensing terms changing in a way that blocks CI use.
