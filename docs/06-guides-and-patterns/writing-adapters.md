# **Writing Custom Adapters**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **The Pattern**

1. **Read the Protocol** in `sagiha/ports/`. Structural typing means you do **not** inherit from it — implementing the methods is sufficient, and inheriting couples you needlessly.
2. **Implement the methods**, accepting and returning the declared Pydantic models. No `Dict[str, Any]` crosses the boundary.
3. **Add your adapter to the conformance suite** — the required step, detailed below.
4. **Wire it in the composition root** (`composition.py`). There is no container to register with and no discovery to trigger.

```python
# sagiha/adapters/memory/my_store.py
from sagiha.ports.memory import Memory
from sagiha.domain.memory import MemoryRecord, RecallQuery, Recall

class MyStore:                       # no base class needed
    async def remember(self, record: MemoryRecord) -> str: ...
    async def recall(self, query: RecallQuery) -> list[Recall]: ...
    async def invalidate(self, memory_id: str, at: datetime) -> None: ...
```

## **Step 3 Is Not Optional**

```python
# tests/contracts/test_memory_conformance.py
@pytest.fixture(params=[SqliteMemory, LanceMemory, MyStore])
def memory(request): ...
```

An adapter that is not in the conformance suite is not a supported adapter. This is the mechanism that makes the migration matrix executable rather than aspirational — see [Port Conformance Testing](./port-conformance-testing.md).

Note that `isinstance(obj, Memory)` is **not** a validity check. `@runtime_checkable` verifies method *presence* only, never signatures, so an implementation taking entirely wrong argument types passes it. Static checking plus the conformance suite are the real gates.

## **Rules That Keep the Hexagon Intact**

**Speak domain language, not storage language.** If your adapter's method names leak its backend (`store_vector`, `execute_cypher`, `get_path`), the port is wrong and every consumer is now coupled to your implementation. The previous `LongTermMemory.store_vector(key, vector)` port is the cautionary example: it forced the core to own the embedding model and could not have accepted a text-episode graph engine at all.

**Own your infrastructure concerns.** Embedding, connection pooling, retries, and schema migration live inside the adapter. If callers must do something before calling you, that requirement belongs in your constructor.

**Return typed models.** A `Dict[str, Any]` return means consumers hardcode key names no type checker can see — worse coupling than a concrete class, because it fails silently and cannot be refactored.

**Aware-UTC timestamps only.** Use `utc_now()`. Naive datetimes break bi-temporal comparison across adapters.

**Degrade, never stall.** If your backend is unavailable, raise a typed error promptly. A hung adapter blocks the agent loop; a failed one is recoverable.

## **Adapters With Side Effects**

Anything touching the filesystem, network, or processes takes a `Grant` parameter and declares an `EffectClass`. Without the grant your adapter is unreachable from Agency — which is the enforcement working as designed, not a bug to route around.
