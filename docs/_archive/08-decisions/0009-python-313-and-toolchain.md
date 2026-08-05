---
status: normative
updated: 2026-07-29
---
# ADR-0009: Python ≥3.13 and Toolchain

**Status**: Accepted  
**Date**: 2026-07-28

## Context
Standardizing core tools prevents environment fragmentation and aligns developer toolchains with LLM language server diagnostics.

## Decision
- **Runtime**: Python `>=3.13` (un-capped, pinned via `uv.lock`; leverage free-threaded GIL-free builds PEP 703).
- **Package Manager**: `uv`.
- **Lint & Format**: `ruff`.
- **Type Checkers**: `pyright` strict (blocking CI gate matching `LSPAdapter`); `mypy` strict (advisory CI gate).
- **Testing**: `pytest >=8.3`, `pytest-asyncio >=0.24`.
- **Architecture Limits**: `import-linter`.

## Consequences
- Unified developer and agent execution environment.
- Eliminates dual-checker blocking deadlocks.

## Reversal Conditions
- Incompatible C-extension requirements, or breaking license changes in pyright blocking CI usage.
