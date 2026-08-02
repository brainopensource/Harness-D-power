---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Port Conformance Testing**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

Conformance testing validates that swapping an adapter never requires consumer code modifications. Conformance suites provide the mechanical guarantee making phased backend migrations safe to execute.

## **The Pattern**

One behavioral test suite per port, parametrized across **all** implementing adapters:

```python
# tests/contracts/test_memory_conformance.py

@pytest.fixture(params=[SqliteMemory, LanceMemory, EpisodicGraphMemory])
def memory(request) -> Memory:
    return request.param(**test_config_for(request.param))

async def test_recall_returns_what_was_remembered(memory):
    mid = await memory.remember(MemoryRecord(content="auth uses JWT", kind="decision"))
    hits = await memory.recall(RecallQuery(text="how does auth work", k=5))
    assert mid in {h.memory_id for h in hits}

async def test_invalidated_facts_are_excluded(memory):
    mid = await memory.remember(MemoryRecord(content="auth uses sessions", kind="decision"))
    await memory.invalidate(mid, at=utc_now())
    hits = await memory.recall(RecallQuery(text="how does auth work", k=5))
    assert mid not in {h.memory_id for h in hits}

async def test_as_of_read_sees_prior_state(memory):
    """Bi-temporal read: a query as-of an earlier time sees prior state."""
    ...

async def test_timestamps_are_timezone_aware(memory):
    hits = await memory.recall(RecallQuery(text="anything"))
    assert all(h.valid_from.tzinfo is not None for h in hits)
```

## **What to Test**

Test port contracts rather than specific adapter implementations:

| Test Contract Requirements | Avoid Testing Implementation Details |
| :--- | :--- |
| Round-trip semantics | Table or file layout |
| Ordering and ranking guarantees | Specific score numbers |
| Error types on invalid input | Error message strings |
| Timezone-aware UTC timestamps | Storage precision |
| Promised idempotency | Internal call counts |
| Empty, missing, and boundary cases | Backend-specific quirks |

## **Rules**

1. **Mandatory Inclusion**: Every adapter must be included in its port's conformance suite.
2. **Migration Acceptance Gate**: A backend ships only when the existing conformance suite passes without modification.
3. **Bugs to Tests**: Adapter behavioral divergences must be resolved in the port spec and added to the suite.
4. **No `isinstance` Equivalence**: `@runtime_checkable` verifies method presence only, not signatures. Conformance tests provide the true operational check.

## **Parity Beyond Conformance**

For high-risk components (memory and indexing):

* **Shadow Reads**: Execute old and new adapters concurrently; log output divergence.
* **Golden Trajectory Replay**: Replay recorded runs against new adapters and diff context responses.
* **Retrieval Metrics**: Benchmark `recall@k` on labelled sets to prevent retrieval degradation.

## **CI Enforcement**

```bash
pytest tests/contracts/     # All ports × all adapters
lint-imports                # CAR layer contract enforcement
mypy --strict src/          # Type verification
```
