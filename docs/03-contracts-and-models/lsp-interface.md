---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Language Server Protocol (`LSPAdapter`) Interface**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**

`LSPAdapter` (`src/sagiha/ports/lsp.py`) provides real-time language server diagnostics, definitions, and references, returning typed `Symbol` and `DiagnosticItem` models. See contract rules in [Hexagonal Ports](./hexagonal-ports.md).

## **Ranking vs. Admission**

Diagnostics feed **soft scores to rank candidates**; they never admit candidates directly. Because diagnostic counts can be gamed (e.g., deleting failing code or adding type suppressions), hard gates like `no_new_suppressions` and `Toolchain` tests enforce admission.

## **Operational Design & Host-Side Pool**

Language servers are kept warm to eliminate 30s+ indexing overhead. In-memory document overlays (`didOpen`/`didChange`) supply unsaved candidate changes without disk writes.

Per [ADR-0016](../08-decisions/0016-container-runtime-podman.md), the LSP server pool runs **host-side**:

1. **Avoids Repeated Cold Starts**: Running LSP daemons inside container sandboxes would force re-indexing per candidate.
2. **Decoupled via Overlays**: Document overlays remove filesystem dependencies.
3. **Read-Only Surface**: LSP adapters read source but perform no mutations or arbitrary execution.

*Trade-off*: Host-side analysis may miss container-only native build outputs. Ground truth validation remains in-container via `Toolchain.test()` and `Toolchain.typecheck()`.

The host pool is managed by a Python supervisor, bounded by `max_lsp_servers` in `ResourceGovernor`, keyed by `(language, project_root)`, and handles crash recovery by returning typed unavailable results. No compiled sidecar daemon wrapper is required; see [Performance Sidecars](../02-architecture/performance-sidecars.md).
