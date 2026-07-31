"""Git worktree-based WorktreeManager — allocate/materialize/release ephemeral worktrees.

See docs/04-workflows-and-loops/git-worktree-branching.md and ports/workspace.py.

`allocate()` is typed to return the `Workspace` port, per that module's invariant that a
`WorktreeManager` never leaks a path through the object it hands back. But composition-root code
(and `e0/runner.py`, which already builds a fresh `Kernel` per task) legitimately needs the
worktree's filesystem path to construct a new `Config`/`Kernel` bound to it — so `path_for()` is a
**concrete-class-only** extension, not on the `WorktreeManager` Protocol, exactly like
`DefaultPolicyEngine.is_tainted` is a concrete-only helper absent from `PolicyEngine`. A caller that
only holds the `WorktreeManager` Protocol type can never reach a path; a caller that holds this
concrete class (because it is the one instantiating it) can.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from anyio.to_thread import run_sync

from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.events import Event, WorktreeAllocated, WorktreeReleased
from sagiha.ports.workspace import Workspace

logger = logging.getLogger(__name__)


class WorktreeError(RuntimeError):
    """Base exception for worktree lifecycle failures."""


class _EventEmitter(Protocol):
    """Structural stand-in for `kernel.bus.EventBus` — `sagiha.adapters` may not import
    `sagiha.kernel` (the `layers` import contract), so this module cannot name the concrete
    type. Composition-root code passes the real `EventBus` in; it satisfies this shape."""

    async def emit(self, event: Event) -> None: ...


class GitWorktreeManager:
    """Manages ephemeral git worktrees for parallel candidate evaluation."""

    def __init__(
        self,
        repo_root: str,
        worktree_dir: str = ".sagiha/worktrees",
        *,
        materialize_paths: list[str] | None = None,
        bus: _EventEmitter | None = None,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._worktree_dir = self._repo_root / worktree_dir
        self._worktrees: dict[str, LocalWorkspace] = {}
        #: Relative paths copied/symlinked into a worktree on `materialize()` — mirrors
        #: `WorkspaceConfig.materialize` (`.env`, `.venv`, `node_modules` by default).
        self._materialize_paths = materialize_paths or []
        self._bus = bus

    def path_for(self, branch_id: str) -> str:
        """The worktree's filesystem path. Concrete-class-only — see module docstring."""
        if branch_id not in self._worktrees:
            raise WorktreeError(f"no allocated worktree for branch_id={branch_id!r}")
        return str(self._worktrees[branch_id].root)

    async def allocate(self, base_commit: str, branch_id: str, *, run_id: str | None = None) -> Workspace:
        """Create a new worktree branching from `base_commit`.

        Fails loudly (`WorktreeError`) on a branch-name collision rather than letting `git`'s
        cryptic stderr surface — callers are expected to mint collision-free `branch_id`s (e.g.
        `f"{task_id}-{uuid4().hex[:8]}"`), so a collision here is a caller bug worth naming.
        """
        if branch_id in self._worktrees:
            raise WorktreeError(f"branch_id={branch_id!r} already allocated")

        worktree_path = self._worktree_dir / branch_id

        def _sync_create() -> tuple[int, str]:
            worktree_path.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch_id, str(worktree_path), base_commit],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
            )
            return result.returncode, result.stderr

        returncode, stderr = await run_sync(_sync_create)
        if returncode != 0:
            raise WorktreeError(
                f"git worktree add failed for branch_id={branch_id!r} at base_commit={base_commit!r}: "
                f"{stderr.strip()}"
            )

        workspace = LocalWorkspace(str(worktree_path))
        self._worktrees[branch_id] = workspace

        if self._bus is not None:
            await self._bus.emit(
                WorktreeAllocated(run_id=run_id or branch_id, branch_id=branch_id, base_commit=base_commit)
            )
        return workspace

    async def materialize(self, branch_id: str) -> None:
        """Symlink/copy shared artifacts (venv, node_modules, .env) into the worktree.

        Directories are symlinked (large, rebuildable, and a copy would multiply disk usage
        per candidate); `.env`-shaped single files are copied (a symlinked `.env` would let one
        candidate's edits — there are none, but a future `write_file` on it would — leak into
        every sibling and the primary checkout). Missing sources are skipped, not errors: not
        every repository has a `.venv` or `node_modules` to share.
        """
        if branch_id not in self._worktrees:
            raise WorktreeError(f"no allocated worktree for branch_id={branch_id!r}")
        worktree_path = self._worktrees[branch_id].root

        def _sync_materialize() -> None:
            for rel_path in self._materialize_paths:
                source = self._repo_root / rel_path
                if not source.exists():
                    continue
                target = worktree_path / rel_path
                if target.exists() or target.is_symlink():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    target.symlink_to(source, target_is_directory=True)
                else:
                    shutil.copy2(source, target)

        await run_sync(_sync_materialize)

    async def release(self, branch_id: str, *, run_id: str | None = None, disposition: str = "ok") -> None:
        """Remove the worktree and clean up the branch.

        Checks both subprocess return codes rather than swallowing failures silently — a
        worktree that fails to remove must be visible (it leaks disk and, worse, a stale branch
        that a later `allocate()` collision-check would otherwise miss).
        """
        if branch_id not in self._worktrees:
            return  # already released, or never allocated — release() is idempotent by design
        worktree_path = self._worktrees[branch_id].root

        def _sync_remove() -> tuple[int, str, int, str]:
            remove_result = subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
            )
            branch_result = subprocess.run(
                ["git", "branch", "-D", branch_id],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
            )
            return (
                remove_result.returncode,
                remove_result.stderr,
                branch_result.returncode,
                branch_result.stderr,
            )

        remove_code, remove_err, branch_code, branch_err = await run_sync(_sync_remove)
        actual_disposition = disposition
        if remove_code != 0:
            logger.warning("worktree remove failed for branch_id=%s: %s", branch_id, remove_err.strip())
            actual_disposition = "remove_failed"
        if branch_code != 0:
            logger.warning("branch delete failed for branch_id=%s: %s", branch_id, branch_err.strip())

        self._worktrees.pop(branch_id, None)

        if self._bus is not None:
            await self._bus.emit(
                WorktreeReleased(
                    run_id=run_id or branch_id, branch_id=branch_id, disposition=actual_disposition
                )
            )

    async def release_all(self) -> None:
        """Release every currently-tracked worktree — the crash/teardown sweep.

        Iterates over a snapshot of keys because `release()` mutates `self._worktrees`.
        """
        for branch_id in list(self._worktrees):
            await self.release(branch_id, disposition="teardown")
