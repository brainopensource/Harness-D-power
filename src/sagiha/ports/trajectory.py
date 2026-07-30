"""TrajectoryStore — append-only steps and events; source of truth for replay, audit, training data.

See docs/03-contracts-and-models/hexagonal-ports.md#execution and
docs/02-architecture/microkernel-and-bus.md. TrajectoryStore and the OTel exporter both subscribe
to the EventBus independently — neither is derived from the other.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.events import Event
from sagiha.domain.trajectory import RunRecord, TrajectoryStep

PORT_VERSION: Final = 2
STABILITY: Final = "provisional"


class TrajectoryStore(Protocol):
    async def append_step(self, step: TrajectoryStep) -> None: ...

    async def append_event(self, event: Event) -> None: ...

    async def steps_for_run(self, run_id: str) -> list[TrajectoryStep]: ...

    async def events_for_run(self, run_id: str) -> list[Event]: ...

    async def upsert_run(self, record: RunRecord) -> None:
        """Insert or update the `runs` table row for `record.run_id` (D9).

        The engine's in-memory step counter is never the source of truth for where a run left
        off — `steps_for_run` is. This is only the task/status side of resumability.
        """
        ...

    async def get_run(self, run_id: str) -> RunRecord | None: ...
