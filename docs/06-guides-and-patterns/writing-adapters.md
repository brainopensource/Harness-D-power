---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Writing Custom Adapters**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Implementation Workflow**

1. **Inspect Port Protocol**: Protocols reside in `sagiha/ports/`. Python structural subtyping (`Protocol`) requires implementing methods without subclass inheritance.
2. **Implement Methods with Typed Models**: Accept and return Pydantic domain models. Never pass raw `Dict[str, Any]` across port boundaries.
3. **Register in Conformance Suite**: Add the new adapter fixture to the port's conformance suite (mandatory).
4. **Wire in Composition Root**: Instantiate and inject the adapter in `composition.py` (no dynamic service locator or container needed).

```python
# sagiha/adapters/memory/my_store.py
from sagiha.ports.memory import Memory
from sagiha.domain.memory import MemoryRecord, RecallQuery, Recall

class MyStore:  # Structural typing; no base class required
    async def remember(self, record: MemoryRecord) -> str: ...
    async def recall(self, query: RecallQuery) -> list[Recall]: ...
    async def invalidate(self, memory_id: str, at: datetime) -> None: ...
```

## **Mandatory Conformance Testing**

```python
# tests/contracts/test_memory_conformance.py
@pytest.fixture(params=[SqliteMemory, LanceMemory, MyStore])
def memory(request): ...
```

Every adapter must pass the port's conformance suite to be supported (see [Port Conformance Testing](./port-conformance-testing.md)). 

> [!WARNING]
> `@runtime_checkable` checks method presence only, not signature types. Static type checks and conformance suites are mandatory for verification.

## **Hexagonal Isolation Rules**

* **Domain Language Abstraction**: Method names must reflect domain operations, not backend storage specifics (e.g., avoid backend-coupled names like `store_vector` or `execute_cypher`).
* **Self-Contained Infrastructure**: Manage connection pools, retries, embeddings, and migrations internally or via constructor injection.
* **Strict Typed Returns**: Avoid returning unvalidated `Dict[str, Any]` dictionaries.
* **Timezone-Aware Timestamps**: Use aware UTC timestamps (`utc_now()`) exclusively.
* **Prompt Failure vs. Blocking**: Raise typed errors immediately when backends are unreachable; never hang execution.

## **Adapters with Side Effects**

Adapters executing filesystem, network, or process operations must accept a `Grant` object and declare an `EffectClass` for policy enforcement.
