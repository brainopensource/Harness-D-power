"""EventBus (TASK-022) — one append-only stream, many consumers.

Purely observational: **events never schedule nodes** (spec.md §8) — the
executor drives its own order from the validated topology, never from what
lands on this bus. Two drop policies: `"never"` (TrajectoryStore, the
measurement harvester — must never lose an event, unbounded queue) and
`"drop_oldest"` (display/TUI consumers — bounded, lossy under backpressure by
design; losing a rendering frame is acceptable, losing a step is not).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from aether.domain.events import Event

DropPolicy = Literal["never", "drop_oldest"]


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Event]] = {}
        self._policies: dict[str, DropPolicy] = {}

    def subscribe(
        self, consumer_id: str, *, drop_policy: DropPolicy, maxsize: int = 1000
    ) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=0 if drop_policy == "never" else maxsize)
        self._queues[consumer_id] = queue
        self._policies[consumer_id] = drop_policy
        return self._iterate(consumer_id, queue)

    async def _iterate(self, consumer_id: str, queue: asyncio.Queue[Event]) -> AsyncIterator[Event]:
        try:
            while True:
                yield await queue.get()
        finally:
            self.unsubscribe(consumer_id)

    def unsubscribe(self, consumer_id: str) -> None:
        self._queues.pop(consumer_id, None)
        self._policies.pop(consumer_id, None)

    def drain(self, consumer_id: str) -> list[Event]:
        """Synchronously empty whatever has accumulated for `consumer_id` without
        blocking. For a finite, already-completed run (the M1a smoke path) this
        is simpler than a concurrent background harvester task; a long-lived
        engine still uses `subscribe()`'s async iterator directly."""
        queue = self._queues.get(consumer_id)
        if queue is None:
            return []
        items: list[Event] = []
        while not queue.empty():
            items.append(queue.get_nowait())
        return items

    async def emit(self, event: Event) -> None:
        for consumer_id in list(self._queues):
            queue = self._queues[consumer_id]
            policy = self._policies[consumer_id]
            if policy == "never":
                await queue.put(event)
                continue
            if queue.full():
                try:
                    queue.get_nowait()  # drop the oldest, make room
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # lost a race with another producer — acceptable for a lossy consumer
