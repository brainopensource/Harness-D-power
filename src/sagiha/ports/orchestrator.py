"""Orchestrator — the single headless signature everything reduces to.

See docs/02-architecture/entry-points-and-piloting.md ("One Core, Many Cockpits"). No
`execute_chat()` — profile selection happens inside `TaskSpec`, not via a second entry point.
"""

from __future__ import annotations

from typing import AsyncIterator, Final, Protocol

from sagiha.domain.control import RunContext
from sagiha.domain.events import Event
from sagiha.domain.work import TaskSpec

PORT_VERSION: Final = 1
STABILITY: Final = "stable"


class Orchestrator(Protocol):
    async def execute(self, task: TaskSpec, context: RunContext) -> AsyncIterator[Event]: ...
