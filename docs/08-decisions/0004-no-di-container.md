# ADR-0004: Explicit Composition Root, No DI Container

**Status**: Accepted
**Date**: 2026-07-28

## Context
The original design specified a kernel DI container with runtime plugin discovery. That is conventional enterprise structure, and it defeats static analysis: type checkers cannot see dynamically registered implementations, so "go to definition" fails at every wiring site.

## Decision
One composition root, `build_kernel(config) -> Kernel`. No container, no scanning. Extensions load from paths declared explicitly in `config.toml`.

## Consequences
The codebase stays statically navigable. This matters more here than in most projects: **the principal maintainer of this code is an LLM navigating it through a language server** — the system's own stated purpose — so navigability is an architectural requirement, not a style preference. Swapping implementations means editing one function rather than changing configuration, which is a real ergonomic cost and an acceptable one.

## Reversal Conditions
A genuine need to load adapters chosen at runtime by untrusted configuration — which would also raise security questions worth answering first.
