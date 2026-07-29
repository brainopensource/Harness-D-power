# **Language Server Protocol (`LSPAdapter`) Interface**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Overview**
`LSPAdapter` exposes real-time language server capabilities to agents. Type errors are a dense, cheap, immediate signal — available in milliseconds, long before a test suite finishes — which makes this one of the highest-value feedback channels in the harness.

```python
class LSPAdapter(Protocol):
    async def get_diagnostics(self, file_path: str) -> list[DiagnosticItem]: ...
    async def get_definition(self, file_path: str, line: int, column: int) -> Symbol | None: ...
    async def get_references(self, file_path: str, line: int, column: int) -> list[Symbol]: ...
```

Returns are typed `Symbol` and `DiagnosticItem` models rather than `Dict[str, Any]`, and `@runtime_checkable` is not applied — see the contract rules in [Hexagonal Ports](./hexagonal-ports.md).

## **Diagnostics Rank Candidates; They Never Admit Them**

Diagnostic counts are a **proxy**, and a trivially gamed one: delete the failing code, add `# type: ignore`, widen a parameter to `Any`, or wrap the call in a bare `except`. Every one of those reduces the error count while making the code worse.

Diagnostics therefore feed the **soft score** used to rank candidates that have already cleared the hard gates, and one gate exists specifically to close the cheapest exploit: `no_new_suppressions`. A clean diagnostic report is evidence, never proof.

## **Operational Realities**

These are the actual engineering problems, and the previous specification addressed none of them:

* **Cold start**: `pyright` and `rust-analyzer` take 30s+ to index a large repository. Servers are kept **warm** across tasks; paying startup per invocation would make diagnostics slower than the tests they were meant to pre-empt.
* **Unsaved edits**: diagnostics must reflect in-memory state. The adapter drives `didOpen`/`didChange` with document overlays rather than requiring a disk write, so speculative edits can be checked before they are committed anywhere.
* **Server explosion under parallel search**: N worktrees × M languages, each with a dedicated server, exhausts RAM — a direct consequence of the System 2 design that the previous documents never confronted. Mitigation: a **bounded pool** shared across worktrees, driven by overlays rather than one server per tree, with the pool size enforced by the `ResourceGovernor`.
* **Crash recovery**: language servers die. The supervisor restarts them, and a diagnostic request during restart returns a typed "unavailable" result rather than blocking the agent loop indefinitely.

## **No LSP Daemon Sidecar**

Language servers **are** already daemons speaking JSON-RPC over stdio. Wrapping them in a compiled service adds indirection, not speed. What is needed is a Python **supervisor** — warm pooling, overlay management, crash recovery — which is exactly what this adapter is. See [Performance Sidecars](../02-architecture/performance-sidecars.md).
