"""Workspace & WorktreeManager — sandboxed execution surface. Optional under some profiles.

See docs/03-contracts-and-models/hexagonal-ports.md#execution.

`Workspace` has no `get_path()` — exposing a real filesystem path would let consumers `open()`
directly and permanently blocks substituting a container or remote runtime. `WorktreeManager`
returns a `Workspace`, never a path.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.content import CommandResult
from sagiha.domain.work import EditRequest, EditResult

PORT_VERSION: Final = 1
STABILITY: Final = "stable"


class Workspace(Protocol):
    """Optional — unbound under profiles with `workspace = "none"` or `"readonly"` for writes."""

    async def read(self, path: str, offset: int = 0, limit: int | None = None) -> str: ...

    async def write(self, path: str, content: str) -> None: ...

    async def apply_edit(self, request: EditRequest) -> EditResult: ...

    async def run(self, command: list[str]) -> CommandResult: ...

    async def checkpoint(self, label: str) -> str: ...  # returns commit_sha

    async def restore(self, commit_sha: str) -> None: ...


class WorktreeManager(Protocol):
    """Optional — unbound under profiles with `workspace = "none"` or `"readonly"`."""

    async def allocate(self, base_commit: str, branch_id: str) -> Workspace: ...

    async def materialize(self, branch_id: str) -> None: ...

    async def release(self, branch_id: str) -> None: ...
