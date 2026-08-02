---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Remoteable Ports**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **The Rule**

> **Every port must be implementable over a wire.**
> All port payloads must be Pydantic-serializable. Live process objects (`Path`, file handles, sockets, callables, locks) are forbidden across port signatures. All port methods must be `async`.

Per [ADR-0010](../08-decisions/0010-defer-exotic-components.md), sidecars are deferred, but port contracts must permit remote implementations without breaking callers:

```
Consumer ─→ Port (Protocol) ─┬─→ InProcessAdapter        (direct call)
                             └─→ RemoteAdapter ─→ [msgpack/UDS | gRPC | HTTP] ─→ Remote process
```

This extends the design principle from [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md) (where `Workspace` omits `get_path()`) across all ports.

## **Payload Serialization Rules**

* **Permitted**: Pydantic `BaseModel` subclasses (`sagiha.domain`), primitives (`str`, `int`, `float`, `bool`, `None`, `bytes`), aware-UTC `datetime`, primitive `Enum`s, homogeneous collections, and `AsyncIterator[SerializableFrame]`.
* **Forbidden Types**:

| Forbidden Type | Reason | Alternative |
| :--- | :--- | :--- |
| `pathlib.Path` | Assumes shared filesystem | `str` path relative to workspace root |
| File handles / `IO[...]` | Non-transportable process reference | Raw bytes/str content or `ResourceBlock` URI |
| Callables / Coroutines | Cannot be marshalled over IPC | Event on `EventBus` or named hook |
| Generators / Sync Iterators | Non-resumable across boundaries | `AsyncIterator[SerializableFrame]` |
| Threading locks / Connections | Process-local | Encapsulate inside adapter |
| Unconstrained `Any` | Defeats type validation | Explicit Pydantic models (see exemptions) |

### Documented Exemptions
* `ToolRegistry.register(schema: dict[str, Any])`: Uses JSON Schema specification.
* `ToolCall.arguments: dict[str, Any]`: Validated against tool schema at dispatch.

## **Async Signatures & Enforcement**

* **Async Signatures**: Port methods use `async def`. Synchronous v1 adapters wrap work in `asyncio.to_thread`.
* **Automated CI Enforcement**: Checked via meta-conformance suite [`tests/contracts/test_port_shape.py`](../../tests/contracts/test_port_shape.py) (`test_all_port_payloads_are_serializable`, `test_every_port_method_is_async`).
* **Known Fix**: `Toolchain.detect(root: Path)` signature to be updated to relative `str`.

## **Cross-References**

* [Performance Sidecars](./performance-sidecars.md)
* [Protocols: MCP & A2A](../03-contracts-and-models/protocols-mcp-a2a.md)
