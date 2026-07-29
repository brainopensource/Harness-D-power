---
status: normative
updated: 2026-07-29
---

# ADR-0004: Explicit Composition Root, No DI Container

**Status**: Accepted — **amended by [ADR-0013](./0013-extension-registration.md)**
**Date**: 2026-07-28

> [!NOTE]
> ADR-0013 amends the extension-loading half of this decision: third parties register adapters, tools,
> and skills through packaging entry points, resolved once at composition and then frozen. The
> static-navigability property this ADR protects is preserved in full — the entry-point target is an
> ordinary module path. The rejection of a DI container and of filesystem scanning stands unchanged.

## Context
The original design specified a kernel DI container with runtime plugin discovery. That is conventional enterprise structure, and it defeats static analysis: type checkers cannot see dynamically registered implementations, so "go to definition" fails at every wiring site.

## Decision
One composition root, `build_kernel(config) -> Kernel`. No container, no scanning. Extensions load from paths declared explicitly in `config.toml`.

## Consequences
The codebase stays statically navigable. This matters more here than in most projects: **the principal maintainer of this code is an LLM navigating it through a language server** — the system's own stated purpose — so navigability is an architectural requirement, not a style preference. Swapping implementations means editing one function rather than changing configuration, which is a real ergonomic cost and an acceptable one.

## Reversal Conditions
A genuine need to load adapters chosen at runtime by untrusted configuration — which would also raise security questions worth answering first.

The weaker version of that need — third parties shipping adapters without forking — did materialize,
and was resolved by ADR-0013 without reintroducing runtime discovery.
