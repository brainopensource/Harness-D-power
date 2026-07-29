"""Reviewer — independent design-quality judge. Optional. Never a gate.

See docs/03-contracts-and-models/hexagonal-ports.md#orchestration--improvement. Returns a
`ReviewReport` — a soft score that ranks, never a gate that admits. The judge must be a frontier
model, never the model that generated the candidate.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.work import ReviewReport, TaskSpec

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class Reviewer(Protocol):
    """Optional — unbound under profiles with no bound Reviewer (e.g. `chat`)."""

    async def review(self, task: TaskSpec, diff: str, branch_id: str) -> ReviewReport: ...
