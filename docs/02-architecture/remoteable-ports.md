---
status: normative
updated: 2026-07-29
---

# **Remoteable Ports**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **The Rule**

> **Every port must be implementable over a wire.**
>
> Payloads crossing a port boundary are Pydantic-serializable. No `Path`, file handle, socket,
> callable, generator, thread, lock, or other live object crosses. Every port method is `async`,
> including where the only v1 adapter is synchronous.

That is the whole rule. What follows is why it is worth enforcing on day 1, and what it costs.

## **Why now, when everything is in-process**

[ADR-0010](../08-decisions/0010-defer-exotic-components.md) defers compiled sidecars, gRPC, and
external daemons behind measured triggers, and that deferral is correct. But *deferring a component*
and *foreclosing it* are different outcomes, and only one of them is reversible.

If ports leak in-process types, then the day a trigger fires — Tree-sitter parsing is GIL-bound, the
vector tier outgrows SQLite, an LSP pool needs to stay warm in a separate process — moving that
component out is not an adapter swap. It is a refactor of every consumer, because the consumers were
written against a contract that only a same-process object can satisfy.

Enforced from the first commit, an in-process adapter and a remote adapter differ **only by a
transport shim**:

```
Consumer ─→ Port (Protocol) ─┬─→ InProcessAdapter        (v1: direct call)
                             └─→ RemoteAdapter ─→ [msgpack/UDS | gRPC | HTTP] ─→ Rust/Go service
```

No consumer changes. No port changes. The trigger condition stays a real option instead of an
aspiration in a roadmap.

The cost of the rule today is close to zero: the domain models are already Pydantic, and async-by-
default costs one keyword. The cost of adopting it after five adapters exist is a week per port.

## **This generalizes an argument the tree already makes**

[Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md) already states that `Workspace` has
**no `get_path()`**, because exposing a real filesystem path lets consumers call `open()` directly and
permanently blocks substituting a container or remote runtime.

That reasoning is correct and is not specific to `Workspace`. Every leaked in-process handle is the
same defect with a different name. This document promotes the argument from one port to all of them.

## **What "serializable" means precisely**

Permitted across a port boundary:

* Pydantic `BaseModel` subclasses from `sagiha.domain`
* Primitives: `str`, `int`, `float`, `bool`, `None`, `bytes`
* Aware-UTC `datetime` (see contract rule 3)
* `Enum` subclasses with primitive values
* Homogeneous `list` / `tuple` / `dict` of the above
* Unions and `Annotated` discriminated unions of the above
* `AsyncIterator[T]` where `T` is itself permitted — a stream of serializable frames is remoteable;
  a stream of live objects is not

Forbidden:

| Forbidden | Why | Use instead |
| :--- | :--- | :--- |
| `pathlib.Path` | Implies a shared filesystem namespace | `str` path relative to a workspace root |
| File handles, `IO[...]` | Not transportable; ties lifetime to a process | Content, or a `ResourceBlock` URI |
| Callables, coroutine factories | Cannot be marshalled | An event on the bus, or a named hook |
| Generators, non-async iterators | Cannot be resumed across a boundary | `AsyncIterator[SerializableFrame]` |
| Locks, queues, connections | Process-local by definition | Keep inside the adapter |
| `Any` in a payload position | Defeats the check entirely | A real model; or take a documented exemption |

### Documented exemptions

Two open-shaped payloads are genuinely open-shaped, and the exemption is stated so the rule stays
credible — an unstated exception erodes a rule faster than a stated one:

* `ToolRegistry.register(schema: dict[str, Any])` — JSON Schema is externally defined.
* `ToolCall.arguments: dict[str, Any]` — validated against that schema at dispatch.

Both are still JSON-serializable, so both remain remoteable. The exemption is from contract rule 1,
not from this one.

## **Async even when synchronous**

A `Protocol` method that is `def` cannot later become `async def` without changing every call site.
Since a remote implementation is necessarily async, a synchronous port method is a decision that the
port will never be remote — made implicitly, by whoever typed it first.

Where the v1 adapter is genuinely synchronous, it wraps the work in `asyncio.to_thread` and the
signature stays honest.

## **Enforcement**

Review does not catch this reliably; a test does. `tests/contracts/test_port_shape.py` walks every
`Protocol` in `sagiha.ports`, resolves annotations, and fails on any parameter or return type outside
the permitted set:

```python
async def test_all_port_payloads_are_serializable(): ...
async def test_every_port_method_is_async(): ...
```

This is a **meta-conformance** test: it checks the shape of the contracts themselves, not the
behavior of an adapter. It runs in the same CI job as the per-port suites.

## **Known violation to fix at implementation**

`Toolchain.detect(root: Path)` in the port index takes a `Path`. It becomes a workspace-relative
`str`, consistent with `Workspace`. Recorded here rather than silently corrected, because a rule
introduced alongside an unacknowledged violation of itself teaches the wrong lesson.

## **What this rule does not do**

It does not commit the project to distribution, gRPC, protobuf, or a second language. Transport
choice remains what [Performance Sidecars](./performance-sidecars.md) and
[Protocols: MCP & A2A](../03-contracts-and-models/protocols-mcp-a2a.md) say it is: start with
length-prefixed msgpack or JSON-RPC over a Unix domain socket, and adopt gRPC only when a second
consumer exists.

This rule only guarantees that when that day comes, the answer is an adapter.
