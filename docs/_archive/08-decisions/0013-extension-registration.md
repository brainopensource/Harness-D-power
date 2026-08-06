---
status: historical
updated: 2026-07-29
---
# ADR-0013: Extension Registration via Entry Points

**Status**: Accepted  
**Date**: 2026-07-29  
**Amends**: [ADR-0004](./0004-no-di-container.md)

## Context
ADR-0004 avoided DI containers but required modifying the repository to register third-party extensions, blocking external plugin ecosystems.

## Decision
- Extensions register via Python packaging entry points in `pyproject.toml` under `sagiha.adapters`, `sagiha.tools`, `sagiha.skills`, and `sagiha.hooks`.
- Entry points resolve **once at startup**, get validated against port `Protocol`s, are recorded in the run manifest, and then freeze.
- No directory scanning; no mid-run hot-reloading.
- Extensions cannot define new ports or expand authority boundaries. See [Extension Model](../02-architecture/extension-model.md).

## Consequences
- Enables third-party PyPI extensions without repo forks.
- Preserves static navigability and IDE "go to definition".
- Requires run manifests to record extension versions for replay verification.

## Reversal Conditions
- Entry-point resolution degrades startup time or type resolution (fallback: explicit `extensions = [...]` import paths in config).
- Third-party code poses unmanageable security risks (fallback: restrict to data-only skills).
- Zero third-party extensions after 12 months.
