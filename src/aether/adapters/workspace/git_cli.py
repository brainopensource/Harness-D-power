"""Git Workspace & WorktreeManager adapter (TASK-017) — over `git` CLI via
`asyncio.subprocess`.

First real adapter for the `Workspace`/`WorktreeManager` boundary (ADR-0005
rev. 2). I3 hard rule: no `Path` crosses the port. All paths in/out are
repo-relative strings; `WorktreeRef.abs_hint` is a plain string for logs
only — this module never reads it back to locate a worktree. Both classes
independently derive the on-disk location from `(worktrees_root, run_id,
worktree_id)`, the same convention `WorktreeManager.create()` used to build it,
so a caller cannot smuggle a filesystem handle through the port by round-
tripping `abs_hint`.
"""

from __future__ import annotations

import asyncio
import os
import time
from uuid import uuid4

from aether.domain.ids import RunId
from aether.domain.workspace import FileSlice, PatchResult, WorktreeRef


class GitCliError(RuntimeError):
    """A `git` invocation failed. Typed so callers never mistake a git failure
    for a plausible empty result."""


def _worktree_path(root: str, run_id: RunId, worktree_id: str) -> str:
    return os.path.join(root, run_id, worktree_id)


async def _run_git(args: list[str], *, cwd: str, input_bytes: bytes | None = None) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input_bytes)
    assert proc.returncode is not None
    return proc.returncode, stdout, stderr


class GitCliWorktreeManager:
    """One worktree per candidate under a run-scoped root
    (`<worktrees_root>/<run_id>/<worktree_id>`)."""

    def __init__(self, repo_path: str, worktrees_root: str) -> None:
        self._repo_path = repo_path
        self._worktrees_root = worktrees_root
        self._active: dict[RunId, list[WorktreeRef]] = {}
        self.last_create_duration_ms: float | None = None  # F1 timer raw hook (TASK-021 reads this)

    async def create(self, run_id: RunId, base_commit: str) -> WorktreeRef:
        worktree_id = f"wt-{uuid4().hex[:12]}"
        abs_path = _worktree_path(self._worktrees_root, run_id, worktree_id)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        start = time.perf_counter()
        code, _stdout, stderr = await _run_git(
            ["worktree", "add", "--detach", abs_path, base_commit], cwd=self._repo_path
        )
        self.last_create_duration_ms = (time.perf_counter() - start) * 1000

        if code != 0:
            raise GitCliError(f"git worktree add failed ({code}): {stderr.decode(errors='replace')}")

        ref = WorktreeRef(worktree_id=worktree_id, run_id=run_id, base_commit=base_commit, abs_hint=abs_path)
        self._active.setdefault(run_id, []).append(ref)
        return ref

    async def destroy(self, worktree: WorktreeRef) -> None:
        abs_path = _worktree_path(self._worktrees_root, worktree.run_id, worktree.worktree_id)
        code, _stdout, stderr = await _run_git(
            ["worktree", "remove", "--force", abs_path], cwd=self._repo_path
        )
        if code != 0:
            raise GitCliError(f"git worktree remove failed ({code}): {stderr.decode(errors='replace')}")

        refs = self._active.get(worktree.run_id, [])
        self._active[worktree.run_id] = [r for r in refs if r.worktree_id != worktree.worktree_id]

    async def list_active(self, run_id: RunId) -> tuple[WorktreeRef, ...]:
        return tuple(self._active.get(run_id, ()))


class GitCliWorkspace:
    """Read/write access to one worktree's files, scoped by the same
    `(worktrees_root, run_id, worktree_id)` convention `GitCliWorktreeManager`
    uses to create them."""

    def __init__(self, worktrees_root: str) -> None:
        self._worktrees_root = worktrees_root

    def _path(self, worktree: WorktreeRef) -> str:
        return _worktree_path(self._worktrees_root, worktree.run_id, worktree.worktree_id)

    async def read(
        self, worktree: WorktreeRef, repo_rel_path: str, start_line: int = 1, end_line: int = -1
    ) -> FileSlice:
        file_path = os.path.join(self._path(worktree), repo_rel_path)

        def _read() -> str:
            with open(file_path, encoding="utf-8") as f:
                return f.read()

        content = await asyncio.to_thread(_read)
        lines = content.splitlines()
        actual_end = end_line if end_line != -1 else len(lines)
        sliced = "\n".join(lines[start_line - 1 : actual_end])
        return FileSlice(repo_rel_path=repo_rel_path, start_line=start_line, end_line=actual_end, text=sliced)

    async def write(self, worktree: WorktreeRef, repo_rel_path: str, text: str) -> None:
        file_path = os.path.join(self._path(worktree), repo_rel_path)

        def _write() -> None:
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)

        await asyncio.to_thread(_write)

    async def apply_patch(self, worktree: WorktreeRef, unified_diff: str) -> PatchResult:
        path = self._path(worktree)
        code, _stdout, stderr = await _run_git(
            ["apply", "--reject", "--whitespace=nowarn", "-"],
            cwd=path,
            input_bytes=unified_diff.encode(),
        )

        def _count_reject_files() -> int:
            count = 0
            for root, _dirs, files in os.walk(path):
                count += sum(1 for f in files if f.endswith(".rej"))
            return count

        rejected = await asyncio.to_thread(_count_reject_files)
        return PatchResult(
            applied=code == 0 and rejected == 0,
            rejected_hunks=rejected,
            detail=stderr.decode(errors="replace") if code != 0 else "",
        )

    async def diff(self, worktree: WorktreeRef) -> str:
        path = self._path(worktree)
        code, stdout, stderr = await _run_git(["diff", "--no-color"], cwd=path)
        if code != 0:
            raise GitCliError(f"git diff failed ({code}): {stderr.decode(errors='replace')}")
        return stdout.decode(errors="replace")
