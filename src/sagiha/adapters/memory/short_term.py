"""ShortTermMemory and Memory implementation.

See docs/03-contracts-and-models/hexagonal-ports.md#memory--retrieval.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sagiha.domain.identity import utc_now
from sagiha.domain.memory import MemoryRecord, Recall, RecallQuery
from sagiha.domain.trajectory import TrajectoryStep

if TYPE_CHECKING:
    from sagiha.ports.trajectory import TrajectoryStore


class ShortTermMemoryAdapter:
    """ShortTermMemory implementation over TrajectoryStore & in-memory buffer."""

    def __init__(self, trajectory_store: TrajectoryStore | None = None) -> None:
        self._trajectory_store = trajectory_store
        self._buffer: dict[str, list[TrajectoryStep]] = {}

    async def append(self, run_id: str, step: TrajectoryStep) -> None:
        if run_id not in self._buffer:
            self._buffer[run_id] = []
        self._buffer[run_id].append(step)
        if self._trajectory_store is not None:
            await self._trajectory_store.append_step(step)

    async def recent(self, run_id: str, limit: int = 20) -> list[TrajectoryStep]:
        if run_id in self._buffer and self._buffer[run_id]:
            return self._buffer[run_id][-limit:]
        if self._trajectory_store is not None:
            steps = await self._trajectory_store.steps_for_run(run_id)
            return steps[-limit:]
        return []


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
        for mem_id, rec in self._records.items():
            if rec.valid_to is not None and rec.valid_to <= as_of:
                continue
            if query.kinds and rec.kind not in query.kinds:
                continue
            score = 1.0 if query.text.lower() in rec.content.lower() else 0.5
            results.append(Recall(memory_id=mem_id, record=rec, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[: query.limit]

    async def invalidate(self, memory_id: str, at: datetime) -> None:
        if memory_id in self._records:
            rec = self._records[memory_id]
            self._records[memory_id] = rec.model_copy(update={"valid_to": at})
