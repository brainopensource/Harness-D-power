"""Git commit-replay harvester — walks git log, extracts task candidates.

SENIOR TODO: Task filtering heuristics, difficulty classification,
             merge-commit handling, multi-file change scoring.
"""

from __future__ import annotations

import logging

from sagiha.domain.benchmark import HarvestedTask

logger = logging.getLogger(__name__)


class GitCommitHarvester:
    """Walks git log to find commits that fix failing tests — E0 task source."""

    async def harvest(self, repo_path: str, *, limit: int = 100) -> list[HarvestedTask]:
        """Extract candidate tasks from the repository's commit history.

        SENIOR TODO: Implement the actual git log walking, diff analysis,
        test-failure detection, and task candidate scoring.
        """
        return []

    async def validate_task(self, task: HarvestedTask, repo_path: str) -> bool:
        """Verify that base_commit reverts cleanly and the test fails.

        SENIOR TODO: git checkout base_commit, run failing_test_cmd,
        verify it fails, then verify target_commit makes it pass.
        """
        return False
