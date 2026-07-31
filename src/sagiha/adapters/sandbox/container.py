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
        raise NotImplementedError("v2-S5 — see docs/STATUS.md")

    async def write(self, path: str, content: str) -> None:
        """Write file inside the container volume."""
        raise NotImplementedError("v2-S5 — see docs/STATUS.md")

    async def apply_edit(self, request: EditRequest) -> EditResult:
        """Apply edit inside the container volume."""
        raise NotImplementedError("v2-S5 — see docs/STATUS.md")

    async def run(self, command: list[str]) -> CommandResult:
        """Run command inside the container perimeter using `podman exec`."""
        raise NotImplementedError("v2-S5 — see docs/STATUS.md")

    async def checkpoint(self, label: str) -> str:
        """Create container volume commit checkpoint."""
        raise NotImplementedError("v2-S5 — see docs/STATUS.md")

    async def restore(self, commit_sha: str) -> None:
        """Restore container volume to commit_sha."""
        raise NotImplementedError("v2-S5 — see docs/STATUS.md")
