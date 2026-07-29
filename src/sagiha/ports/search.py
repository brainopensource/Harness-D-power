"""CandidateSearch — propose / evaluate / select.

See docs/03-contracts-and-models/hexagonal-ports.md#orchestration--improvement and
docs/08-decisions/0005-best-of-n-not-mcts.md. Best-of-N with sequential repair — deliberately not
MCTS: no persistent tree, visit counts, or backpropagation. v0.1 runs this port at N=1 (sequential
repair only); N>1 best-of-N is deferred past v0.1 per the 2026-07-28 architecture review.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.control import RunContext
from sagiha.domain.work import GateReport, TaskSpec

PORT_VERSION: Final = 1
STABILITY: Final = "provisional"


class CandidateSearch(Protocol):
    async def propose(self, task: TaskSpec, context: RunContext, n: int) -> list[str]: ...  # branch_ids

    async def evaluate(self, branch_id: str) -> GateReport | None: ...

    async def select(self, branch_ids: list[str]) -> str: ...  # winning branch_id
