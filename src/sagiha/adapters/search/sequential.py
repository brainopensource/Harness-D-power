"""Sequential candidate search — N=1 baseline (sequential repair only).

See docs/08-decisions/0005-best-of-n-not-mcts.md and ports/search.py.
v0.1 runs at N=1; N>1 best-of-N is the senior's job.

SENIOR TODO: Parallel candidate generation (N>1), repair loop with diagnostic feedback,
             escalation ladder, graph-partitioned decomposition for multi-file tasks.
"""

from __future__ import annotations

import logging
import uuid

from sagiha.domain.control import RunContext
from sagiha.domain.work import GateReport, TaskSpec

logger = logging.getLogger(__name__)


class SequentialCandidateSearch:
    """N=1 sequential candidate search — run once, evaluate, return."""

    async def propose(self, task: TaskSpec, context: RunContext, n: int) -> list[str]:
        """Propose n candidate branch IDs.

        SENIOR TODO: Worktree allocation per candidate, parallel RunLoop invocations.
        """
        return [f"candidate-{uuid.uuid4().hex[:8]}" for _ in range(n)]

    async def evaluate(self, branch_id: str) -> GateReport | None:
        """Evaluate a candidate branch against the gate.

        SENIOR TODO: Run GateEvaluator against the candidate's worktree.
        """
        return None

    async def select(self, branch_ids: list[str]) -> str:
        """Select the winning candidate.

        SENIOR TODO: Gate-based selection (hard gates admit, soft scores rank).
        """
        return branch_ids[0] if branch_ids else ""
