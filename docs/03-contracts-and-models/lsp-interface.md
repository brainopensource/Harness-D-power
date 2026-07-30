---
status: normative
updated: 2026-07-29
---

# **Language Server Protocol (`LSPAdapter`) Interface**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**
`LSPAdapter` exposes real-time language server capabilities to agents. Type errors are a dense, cheap, immediate signal — available in milliseconds, long before a test suite finishes — which makes this one of the highest-value feedback channels in the harness.

The contract lives in **`src/sagiha/ports/lsp.py`** (`get_diagnostics`, `get_definition`,
`get_references`). Returns are typed `Symbol` and `DiagnosticItem` models rather than
`Dict[str, Any]`, and `@runtime_checkable` is not applied — see the contract rules in
[Hexagonal Ports](./hexagonal-ports.md).

## **Diagnostics Rank Candidates; They Never Admit Them**

Diagnostic counts are a **proxy**, and a trivially gamed one: delete the failing code, add `# type: ignore`, widen a parameter to `Any`, or wrap the call in a bare `except`. Every one of those reduces the error count while making the code worse.

Diagnostics therefore feed the **soft score** used to rank candidates that have already cleared the hard gates, and one gate exists specifically to close the cheapest exploit: `no_new_suppressions`. A clean diagnostic report is evidence, never proof.

## **Operational Realities**

A language server integration is easy to specify and hard to operate. These are the problems that decide whether it is usable in an inner loop:

* **Cold start**: `pyright` and `rust-analyzer` take 30s+ to index a large repository. Servers are kept **warm** across tasks; paying startup per invocation would make diagnostics slower than the tests they were meant to pre-empt.
* **Unsaved edits**: diagnostics must reflect in-memory state. The adapter drives `didOpen`/`didChange` with document overlays rather than requiring a disk write, so speculative edits can be checked before they are committed anywhere.
* **Server explosion under parallel search**: N worktrees × M languages, each with a dedicated server, exhausts RAM. This is a direct consequence of the System 2 design and the main hidden cost of parallel candidates. Mitigation: a **bounded pool** shared across worktrees, driven by overlays rather than one server per tree, with the pool size enforced by the `ResourceGovernor`.
* **Crash recovery**: language servers die. The supervisor restarts them, and a diagnostic request during restart returns a typed "unavailable" result rather than blocking the agent loop indefinitely.

## **Where the Pool Runs**

[ADR-0016](../08-decisions/0016-container-runtime-podman.md) puts command execution inside a
per-candidate container, which raises a question the warm-pool design does not answer on its own:
**does the language server run on the host, or inside each container?**

**The pool is host-side.** Three reasons, in order of weight:

1. **In-container pooling defeats the pool.** A server inside the sandbox dies with its container, so
   the 30s cold start is paid per candidate and again after every restart — N candidates × M languages
   × every retry. That is precisely the cost warm pooling exists to eliminate.
2. **Overlays already remove the filesystem dependency.** The adapter drives `didOpen`/`didChange` with
   in-memory document overlays rather than requiring a disk write, so the server never needs to see the
   container's filesystem to analyze candidate source.
3. **The LSP adapter is a reader, not an effectful runtime.** It executes no model-authored commands
   and writes nothing. Keeping it outside the sandbox does not weaken the perimeter, because the
   perimeter exists to contain *effects* — and `run_command`, `apply_edit`, and the toolchain all remain
   inside it.

**The trade-off, stated plainly**: a host-side server analyses source that may reference dependencies
installed only inside the image. Diagnostics can therefore be wrong about native extensions, generated
code, or anything resolved at image build time. That is accepted, because:

* Diagnostics are a **fast, dense, gameable proxy** feeding the soft score — never a hard gate. A
  false diagnostic misranks a candidate; it cannot admit or reject one.
* Ground truth is `Toolchain.test()` and `Toolchain.typecheck()`, which **do** run inside the
  container, against the real environment. Anything requiring true in-container execution — running a
  debugger, resolving image-built native extensions — belongs there and not here.

The host-side pool is bounded by `max_lsp_servers` in the `ResourceGovernor`, shared across all
worktrees, and keyed by (language, project root) rather than by candidate.

## **No LSP Daemon Sidecar**

Language servers **are** already daemons speaking JSON-RPC over stdio. Wrapping them in a compiled service adds indirection, not speed. What is needed is a Python **supervisor** — warm pooling, overlay management, crash recovery — which is exactly what this adapter is. See [Performance Sidecars](../02-architecture/performance-sidecars.md).
