"""Memory implementation.

See docs/03-contracts-and-models/hexagonal-ports.md#memory--retrieval.

`ShortTermMemoryAdapter` was deleted here (D12/R7, 2026-07-30): `RunLoop` keeps step history in a
local `list[Message]` (`agency/run_loop.py`) and this adapter was bound nowhere in
`composition.py` — a live class behind a contract nothing called, which is precisely the dead
second path D12 warned about. Short-term history has exactly one implementation now. If prompt
assembly later needs a `ShortTermMemory` port adapter, write it against that real need rather than
reviving this one; a buffer that pre-dates the caller it was guessing at tends to guess wrong.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sagiha.domain.identity import utc_now
from sagiha.domain.memory import MemoryRecord, Provenance, Recall, RecallQuery

# Trust ordering, most to least trusted (docstring order in domain/memory.py). Higher rank wins.
_PROVENANCE_TRUST_RANK: dict[Provenance, int] = {
    Provenance.OPERATOR: 3,
    Provenance.HARNESS: 2,
    Provenance.MODEL: 1,
    Provenance.EXTERNAL: 0,
}


class InMemoryMemory:
    """In-memory implementation of the durable Memory port for testing/baseline kernel."""

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    async def remember(self, record: MemoryRecord) -> str:
        memory_id = str(uuid.uuid4())
        self._records[memory_id] = record
        return memory_id

    async def recall(self, query: RecallQuery) -> list[Recall]:
        results: list[Recall] = []
        as_of = query.as_of or utc_now()
        min_rank = (
            _PROVENANCE_TRUST_RANK[query.min_provenance] if query.min_provenance is not None else None
        )
        for mem_id, rec in self._records.items():
            if rec.valid_to is not None and rec.valid_to <= as_of:
                continue
            if query.kinds and rec.kind not in query.kinds:
                continue
            if min_rank is not None and _PROVENANCE_TRUST_RANK[rec.provenance] < min_rank:
                continue
            score = 1.0 if query.text.lower() in rec.content.lower() else 0.5
            results.append(Recall(memory_id=mem_id, record=rec, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[: query.limit]

    async def invalidate(self, memory_id: str, at: datetime) -> None:
        if memory_id in self._records:
            rec = self._records[memory_id]
            self._records[memory_id] = rec.model_copy(update={"valid_to": at})
