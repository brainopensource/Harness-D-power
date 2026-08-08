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

from aether.adapters.subprocess_env import spawn_env
from aether.domain.ids import RunId
from aether.domain.workspace import FileSlice, PatchResult, WorktreeRef
from aether.domain.workspace import worktree_path as _worktree_path

#: `git` commands here are host-side, uncontained subprocesses (TASK-062):
#: none of them is expected to run long, so one generous deadline covers
#: `worktree add/remove`, `diff` and `apply` alike rather than threading a
#: lease through a port whose signature (`Workspace`/`WorktreeManager`)
#: carries no budget concept today.
_GIT_TIMEOUT_S = 60


class PathEscapesWorktree(ValueError):
    """A caller-supplied path resolves outside the worktree it names.

    Refused, never clamped: silently rewriting `/etc/passwd` to
    `<worktree>/etc/passwd` would let a candidate think it wrote where it asked
    and leave the harness guessing which file it meant.
    """


class GitCliError(RuntimeError):
    """A `git` invocation failed. Typed so callers never mistake a git failure
    for a plausible empty result."""


class GitCliTimeout(GitCliError):
    """A `git` invocation exceeded `_GIT_TIMEOUT_S` (TASK-062). Typed rather
    than left as a bare `TimeoutError` so a caller catching `GitCliError`
    already catches this."""


async def _run_git(
    args: list[str], *, cwd: str, input_bytes: bytes | None = None
) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=spawn_env(),
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(input_bytes), timeout=_GIT_TIMEOUT_S)
    except TimeoutError as exc:
        proc.kill()
        await proc.communicate()
        raise GitCliTimeout(f"git {' '.join(args)} timed out after {_GIT_TIMEOUT_S}s") from exc
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
        abs_path = worktree.path(self._worktrees_root)
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
        return worktree.path(self._worktrees_root)

    def _resolve(self, worktree: WorktreeRef, repo_rel_path: str) -> str:
        """Join a caller-supplied path to the worktree, refusing any that
        escapes it.

        Found by tier 1 of the Sprint 3.5 ladder: a model emitted an absolute
        path in a code block, `os.path.join` discarded the worktree root (that
        is what join does with an absolute second argument), and the harness
        tried to write to `/storage.py`. A permission error is what stopped it,
        not a check — under `$HOME` it would have written outside the candidate
        worktree entirely.

        Paths crossing this boundary come from a model, which makes them
        untrusted input by definition (ADR-0015). The adapter is the boundary,
        so the check lives here rather than in whichever node happened to call
        it.
        """
        root = os.path.realpath(self._path(worktree))
        candidate = os.path.realpath(os.path.join(root, repo_rel_path))
        if candidate != root and not candidate.startswith(root + os.sep):
            raise PathEscapesWorktree(
                f"{repo_rel_path!r} resolves outside the worktree ({candidate!r} is not under "
                f"{root!r}); paths are repo-relative (I3) and a worktree is the isolation unit"
            )
        return candidate

    async def read(
        self, worktree: WorktreeRef, repo_rel_path: str, start_line: int = 1, end_line: int = -1
    ) -> FileSlice:
        file_path = self._resolve(worktree, repo_rel_path)

        def _read() -> str:
            with open(file_path, encoding="utf-8") as f:
                return f.read()

        content = await asyncio.to_thread(_read)
        lines = content.splitlines()
        actual_end = end_line if end_line != -1 else len(lines)
        sliced = "\n".join(lines[start_line - 1 : actual_end])
        return FileSlice(repo_rel_path=repo_rel_path, start_line=start_line, end_line=actual_end, text=sliced)

    async def write(self, worktree: WorktreeRef, repo_rel_path: str, text: str) -> None:
        file_path = self._resolve(worktree, repo_rel_path)

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
            for _root, _dirs, files in os.walk(path):
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
