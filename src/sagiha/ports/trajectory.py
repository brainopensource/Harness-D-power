"""TrajectoryStore — append-only steps and events; source of truth for replay, audit, training data.

See docs/03-contracts-and-models/hexagonal-ports.md#execution and
docs/02-architecture/microkernel-and-bus.md. TrajectoryStore and the OTel exporter both subscribe
to the EventBus independently — neither is derived from the other.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.events import Event
from sagiha.domain.trajectory import TrajectoryStep

PORT_VERSION: Final = 1
STABILITY: Final = "stable"


class TrajectoryStore(Protocol):
    async def append_step(self, step: TrajectoryStep) -> None: ...

    async def append_event(self, event: Event) -> None: ...

    async def steps_for_run(self, run_id: str) -> list[TrajectoryStep]: ...

    async def events_for_run(self, run_id: str) -> list[Event]: ...
