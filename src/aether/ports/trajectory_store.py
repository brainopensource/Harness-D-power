"""TrajectoryStore — durable append-only event log boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from pydantic import AwareDatetime

from aether.domain.ids import Frozen, RunId


class StoredEvent(Frozen):
    seq: int
    run_id: RunId
    event_type: str
    payload_json: str
    at: AwareDatetime


@runtime_checkable
class TrajectoryStore(Protocol):
    """Durable append-only log; a bus consumer like any other. Replay for the
    prompt-cache CI floor (I10) and record/replay cassettes reads from here."""

    async def append(self, event: StoredEvent) -> None: ...

    async def replay(self, run_id: RunId, from_seq: int = 0) -> AsyncIterator[StoredEvent]: ...

    async def latest_seq(self, run_id: RunId) -> int: ...
