"""D7: InMemoryMemory.recall must honor min_provenance."""

from __future__ import annotations

import pytest

from sagiha.adapters.memory.short_term import InMemoryMemory
from sagiha.domain.memory import MemoryRecord, Provenance, RecallQuery


@pytest.mark.asyncio
async def test_recall_filters_below_min_provenance() -> None:
    memory = InMemoryMemory()
    await memory.remember(
        MemoryRecord(content="operator said fix the bug", kind="note", provenance=Provenance.OPERATOR)
    )
    await memory.remember(
        MemoryRecord(content="harness deterministic bug scan", kind="note", provenance=Provenance.HARNESS)
    )
    await memory.remember(
        MemoryRecord(content="model reasoning about the bug", kind="note", provenance=Provenance.MODEL)
    )
    await memory.remember(
        MemoryRecord(content="external web page about the bug", kind="note", provenance=Provenance.EXTERNAL)
    )

    results = await memory.recall(RecallQuery(text="bug", limit=10, min_provenance=Provenance.HARNESS))

    provenances = {r.record.provenance for r in results}
    assert provenances == {Provenance.OPERATOR, Provenance.HARNESS}
    assert Provenance.MODEL not in provenances
    assert Provenance.EXTERNAL not in provenances


@pytest.mark.asyncio
async def test_recall_without_min_provenance_returns_everything() -> None:
    memory = InMemoryMemory()
    await memory.remember(
        MemoryRecord(content="external web page about the bug", kind="note", provenance=Provenance.EXTERNAL)
    )

    results = await memory.recall(RecallQuery(text="bug", limit=10))

    assert len(results) == 1
    assert results[0].record.provenance == Provenance.EXTERNAL
