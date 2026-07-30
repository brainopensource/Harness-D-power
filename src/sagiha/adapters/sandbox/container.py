"""Podman container sandbox adapter — rootless container perimeter for Block 5.

See docs/08-decisions/0006-container-sandbox-architecture.md.

SENIOR TODO: Podman container lifecycle management, egress allowlist enforcement,
             mount binding for worktrees, credential isolation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sagiha.domain.content import CommandResult
from sagiha.domain.work import EditRequest, EditResult

logger = logging.getLogger(__name__)


class ContainerSandbox:
    """Rootless Podman container perimeter implementation of Workspace."""

    def __init__(self, image: str = "sagiha/runtime:latest", worktree_root: str = ".") -> None:
        self._image = image
        self._worktree_root = Path(worktree_root)

    async def read(self, path: str, offset: int = 0, limit: int | None = None) -> str:
        """Read file inside the container volume."""
        return ""

    async def write(self, path: str, content: str) -> None:
        """Write file inside the container volume."""
        pass

    async def apply_edit(self, request: EditRequest) -> EditResult:
        """Apply edit inside the container volume."""
        from sagiha.domain.work import HunkResult

        return EditResult(hunks=(HunkResult(applied=True, index=0, reason="ok"),), syntax_valid=True)

    async def run(self, command: list[str]) -> CommandResult:
        """Run command inside the container container perimeter using `podman exec`."""
        return CommandResult(exit_code=0, stdout="", stderr="", duration_ms=0.0)

    async def checkpoint(self, label: str) -> str:
        """Create container volume commit checkpoint."""
        return "container-checkpoint-sha"

    async def restore(self, commit_sha: str) -> None:
        """Restore container volume to commit_sha."""
        pass
