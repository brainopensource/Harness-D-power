"""Git worktree-based WorktreeManager — allocate/materialize/release ephemeral worktrees.

See docs/04-workflows-and-loops/git-worktree-branching.md and ports/workspace.py.

SENIOR TODO: Materialize step (copy .env, .venv, node_modules from config.workspace.materialize),
             concurrent worktree safety, cleanup on crash.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from anyio.to_thread import run_sync

from sagiha.adapters.workspace.local import LocalWorkspace

logger = logging.getLogger(__name__)


class GitWorktreeManager:
    """Manages ephemeral git worktrees for parallel candidate evaluation."""

    def __init__(self, repo_root: str, worktree_dir: str = ".sagiha/worktrees") -> None:
        self._repo_root = Path(repo_root)
        self._worktree_dir = self._repo_root / worktree_dir
        self._worktrees: dict[str, LocalWorkspace] = {}

    async def allocate(self, base_commit: str, branch_id: str) -> LocalWorkspace:
        """Create a new worktree branching from base_commit.

        SENIOR TODO: Error handling for dirty working trees, branch conflicts,
                     disk space checks, concurrent allocation safety.
        """
        worktree_path = self._worktree_dir / branch_id

        def _sync_create() -> None:
            worktree_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "worktree", "add", "-b", branch_id, str(worktree_path), base_commit],
                cwd=str(self._repo_root),
                capture_output=True,
                check=True,
            )

        await run_sync(_sync_create)
        workspace = LocalWorkspace(str(worktree_path))
        self._worktrees[branch_id] = workspace
        return workspace

    async def materialize(self, branch_id: str) -> None:
        """Copy shared artifacts (venv, node_modules) into the worktree.

        SENIOR TODO: Implement materialization from config.workspace.materialize list,
                     symlink vs copy strategy, size-aware decisions.
        """
        pass

    async def release(self, branch_id: str) -> None:
        """Remove the worktree and clean up the branch.

        SENIOR TODO: Force-remove on stuck worktrees, branch cleanup policy.
        """
        worktree_path = self._worktree_dir / branch_id

        def _sync_remove() -> None:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=str(self._repo_root),
                capture_output=True,
            )
            subprocess.run(
                ["git", "branch", "-D", branch_id],
                cwd=str(self._repo_root),
                capture_output=True,
            )

        await run_sync(_sync_remove)
        self._worktrees.pop(branch_id, None)
