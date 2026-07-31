---
status: normative
updated: 2026-07-29
---
# ADR-0013: Extension Registration via Entry Points

**Status**: Accepted
**Date**: 2026-07-29
**Amends**: [ADR-0004](./0004-no-di-container.md) — does not reverse it

## Context

ADR-0004 rejected a DI container and runtime plugin discovery. The reasoning is sound and stands: a
container with dynamic discovery defeats static analysis, and this codebase's principal maintainer is
an LLM navigating through a language server, so static navigability is a first-class architectural
requirement rather than a style preference.

But ADR-0004 answered only "how is the core wired," and the answer that followed from it in the
conceptual design — "plugins are static adapters registered via explicit composition root" — has a
consequence nobody wrote down: **a third party cannot add an adapter, tool, or skill without editing
this repository.** Every extension becomes a pull request, and every extender becomes a maintainer.

SAGIHA is intended to be open source and community-extensible, and to eventually be extended by agents
operating on it. That goal and the literal reading of ADR-0004 are incompatible. One of them had to
give, and neither should — the two constraints were treated as a binary when a third option exists.

## Decision

Extensions register through **Python packaging entry points**, declared in the extender's
`pyproject.toml` under `sagiha.adapters`, `sagiha.tools`, and `sagiha.skills`.

The composition root resolves each declared entry point **exactly once at startup**, validates it
against the target port's `Protocol`, records it in the run manifest, and then **freezes the
registry**. Nothing is discovered by scanning. Nothing is registered after composition.

Config may pin, disable, or restrict the resolved set; the operator retains final say.

Four extension surfaces are recognized — adapter, tool, skill, hook — each with its own constraints
and trust level. None may define a new port, reach past a port boundary, or widen authority. See
[Extension Model](../02-architecture/extension-model.md).

## Consequences

**Makes easy**: a third party ships `sagiha-qdrant` on PyPI; a user installs it and enables it in
config. No fork, no patch, no upstream coordination. The project can accumulate an ecosystem without
the maintainer becoming a bottleneck — which is the difference between a framework and an application
with good documentation.

**Preserves**: every property ADR-0004 was protecting. The entry point target is an ordinary module
path, so pyright resolves it and "go to definition" works. The declaration is written by a human in a
file, not inferred from a filesystem scan. `sagiha extensions list` prints the resolved set, so wiring
stays auditable from one place.

**Makes hard**: extensions are now part of the reproducibility surface. A replayed trajectory must run
against the same extension set, so the run manifest records every name, version, and resolved entry
point. Extensions also become part of the security surface — an installed extension is code running in
the harness process, which is why tools are policy-gated at dispatch and skills carry `EXTERNAL`
provenance regardless of who wrote them.

**Forecloses**: hot-reloading extensions mid-run, and any extension that needs to define a new port.
Both are deliberate.

## Reversal Conditions

* Entry-point resolution measurably degrades startup time or type resolution in practice — in which
  case fall back to an explicit `extensions = [...]` list of import paths in config, keeping the same
  resolve-once-then-freeze lifecycle and losing only the install-and-go ergonomics.
* Evidence that third-party extensions are a net security loss at this project's scale — in which case
  restrict the entry-point groups to `sagiha.skills` (data, not code) and require adapters to be
  vendored.
* No third-party extension exists twelve months after the first public release, indicating the
  mechanism solved a problem the project does not have.
