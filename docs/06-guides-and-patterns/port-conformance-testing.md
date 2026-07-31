---
status: rationale
retrieval: excluded
updated: 2026-07-29
---
# **Port Conformance Testing**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

"Swappable adapters" is the most common unenforced claim in hexagonal architectures. Asserting that replacing an adapter never requires changes to consumers is free; making it true requires a mechanism. Without one the guarantee fails silently on the day it is first exercised — the SQLite adapter is swapped for LanceDB, retrieval quietly degrades, and a month is spent blaming prompts.

**Conformance suites are that mechanism.** They are the reason the phased migration matrix is safe to execute, and they are a Day-0 deliverable, not a later refinement.

## **The Pattern**

One behavioral suite per port, parametrized over **every** adapter implementing it:

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
    """Bi-temporal read: a query as-of an earlier time still sees the old fact."""
    ...


async def test_timestamps_are_timezone_aware(memory):
    hits = await memory.recall(RecallQuery(text="anything"))
    assert all(h.valid_from.tzinfo is not None for h in hits)
```

## **What to Test**

Test the **contract**, never the implementation:

| Test this | Not this |
| :---- | :---- |
| Round-trip semantics | Table or file layout |
| Ordering and ranking guarantees | Specific scores |
| Error types on invalid input | Error message strings |
| Aware-UTC timestamps | Storage precision |
| Idempotency where promised | Internal call counts |
| Empty, missing, and boundary cases | Backend-specific quirks |

A suite that passes only for one adapter is testing an implementation, and it will block the very migration it was written to protect.

## **Rules**

1. **Every adapter is in the suite.** An adapter absent from it is unsupported.
2. **The suite is the migration acceptance test.** A new backend ships when the existing suite passes unchanged — that, and nothing else, is what "swappable" means operationally.
3. **Bugs become conformance tests.** When one adapter has a behavior the others do not, the divergence is a contract ambiguity: resolve it in the port's documentation, then encode it for everyone.
4. **`isinstance` is not conformance.** `@runtime_checkable` checks method presence only, never signatures. An adapter with wrong argument types passes it, which is worse than no check because it *looks* like verification.

## **Parity Beyond the Suite**

For high-risk migrations — the memory and index tiers especially — conformance is necessary but not sufficient, since both adapters can satisfy the contract while returning materially different results:

* **Shadow reads**: run both adapters, serve one, log divergence. Cheap, and it catches ranking drift a contract test cannot express.
* **Golden trajectory replay**: replay recorded runs against the new adapter and diff the retrieved context.
* **Retrieval metrics**: recall@k on the labelled query set must not regress. Task success alone hides retrieval regressions inside end-to-end noise.

## **In CI**

```bash
pytest tests/contracts/     # all ports × all adapters
lint-imports                # agency/ cannot import runtime/ or adapters/
mypy --strict src/
```

These three commands are the architecture's load-bearing guarantees, checked mechanically. Everything else in this documentation suite is a description of intent; this is the part that holds.
