"""Workspace + WorktreeManager — two protocols, one boundary (ratified)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.domain.ids import RunId
from aether.domain.workspace import FileSlice, PatchResult, WorktreeRef


@runtime_checkable
class Workspace(Protocol):
    """Read/write access to one worktree's files. All paths repo-relative strings."""

    async def read(
        self, worktree: WorktreeRef, repo_rel_path: str, start_line: int = 1, end_line: int = -1
    ) -> FileSlice: ...

    async def write(self, worktree: WorktreeRef, repo_rel_path: str, text: str) -> None: ...

    async def apply_patch(self, worktree: WorktreeRef, unified_diff: str) -> PatchResult: ...

    async def diff(self, worktree: WorktreeRef) -> str: ...


@runtime_checkable
class WorktreeManager(Protocol):
    """Worktree lifecycle. create() is timer-instrumented from day one (ADR-0001)."""

    async def create(self, run_id: RunId, base_commit: str) -> WorktreeRef: ...

    async def destroy(self, worktree: WorktreeRef) -> None: ...

    async def list_active(self, run_id: RunId) -> tuple[WorktreeRef, ...]: ...
