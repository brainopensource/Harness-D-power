---
status: historical
updated: 2026-07-29
---
# ADR-0004: Explicit Composition Root, No DI Container

**Status**: Accepted — **amended by [ADR-0013](./0013-extension-registration.md)**  
**Date**: 2026-07-28

> [!NOTE]
> Amended by ADR-0013 for extension loading via packaging entry points. Rejection of DI containers and filesystem scanning stands.

## Context
DI containers and dynamic filesystem scanning break static analysis and language-server navigation ("go to definition"), which is essential for LLM-driven development.

## Decision
- Single composition root: `build_kernel(config) -> Kernel`.
- No DI containers or dynamic directory scanning.
- Extensions declared explicitly in `config.toml` (or packaging entry points per ADR-0013).

## Consequences
- Static code navigability preserved for IDEs and LLM agents.
- Swapping components requires explicit root configuration.

## Reversal Conditions
- Mandatory runtime loading of untrusted, non-declarative configurations.
