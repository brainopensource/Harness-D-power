"""Unit tests for `adapters/workspace/worktree.py::GitWorktreeManager` (v2-S4 Epic S4.2a).

Uses a real throwaway git repository under `tmp_path` rather than mocking `subprocess` —
worktree lifecycle correctness (collision handling, idempotent release, event emission) is
exactly the kind of thing that looks right against a mock and breaks against real git.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from sagiha.adapters.workspace.worktree import GitWorktreeManager, WorktreeError


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "a.txt").write_text("hello\n")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


class FakeBus:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def emit(self, event: object) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_allocate_creates_worktree_at_base_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    manager = GitWorktreeManager(str(repo))
    workspace = await manager.allocate("HEAD", "branch-a")
    assert (Path(manager.path_for("branch-a")) / "a.txt").exists()
    assert workspace is not None


@pytest.mark.asyncio
async def test_allocate_collision_raises_worktree_error(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    manager = GitWorktreeManager(str(repo))
    await manager.allocate("HEAD", "branch-dup")
    with pytest.raises(WorktreeError):
        await manager.allocate("HEAD", "branch-dup")


@pytest.mark.asyncio
async def test_path_for_unallocated_branch_raises(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    manager = GitWorktreeManager(str(repo))
    with pytest.raises(WorktreeError):
        manager.path_for("never-allocated")


@pytest.mark.asyncio
async def test_release_is_idempotent(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    manager = GitWorktreeManager(str(repo))
    await manager.allocate("HEAD", "branch-b")
    await manager.release("branch-b")
    await manager.release("branch-b")  # must not raise on a second release


@pytest.mark.asyncio
async def test_release_removes_worktree_directory(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    manager = GitWorktreeManager(str(repo))
    await manager.allocate("HEAD", "branch-c")
    path = manager.path_for("branch-c")
    assert os.path.exists(path)
    await manager.release("branch-c")
    assert not os.path.exists(path)


@pytest.mark.asyncio
async def test_allocate_and_release_emit_events(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    bus = FakeBus()
    manager = GitWorktreeManager(str(repo), bus=bus)
    await manager.allocate("HEAD", "branch-d", run_id="run-1")
    await manager.release("branch-d", run_id="run-1")
    event_names = [type(e).__name__ for e in bus.events]
    assert "WorktreeAllocated" in event_names
    assert "WorktreeReleased" in event_names


@pytest.mark.asyncio
async def test_materialize_symlinks_directories(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    venv_dir = repo / ".venv"
    venv_dir.mkdir()
    (venv_dir / "marker").write_text("x")

    manager = GitWorktreeManager(str(repo), materialize_paths=[".venv"])
    await manager.allocate("HEAD", "branch-e")
    await manager.materialize("branch-e")

    linked = Path(manager.path_for("branch-e")) / ".venv"
    assert linked.is_symlink()
    assert (linked / "marker").read_text() == "x"


@pytest.mark.asyncio
async def test_materialize_skips_missing_source(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    manager = GitWorktreeManager(str(repo), materialize_paths=["nonexistent_dir"])
    await manager.allocate("HEAD", "branch-f")
    await manager.materialize("branch-f")  # must not raise


@pytest.mark.asyncio
async def test_release_all_releases_every_tracked_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    manager = GitWorktreeManager(str(repo))
    await manager.allocate("HEAD", "branch-g")
    await manager.allocate("HEAD", "branch-h")
    await manager.release_all()
    with pytest.raises(WorktreeError):
        manager.path_for("branch-g")
    with pytest.raises(WorktreeError):
        manager.path_for("branch-h")
