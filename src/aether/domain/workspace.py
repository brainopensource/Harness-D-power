"""Worktree reference and file-slice/patch shapes for the Workspace boundary."""

from __future__ import annotations

import os

from aether.domain.ids import Frozen, RunId


def worktree_path(worktrees_root: str, run_id: RunId | str, worktree_id: str) -> str:
    """The one on-disk location convention for a worktree:
    `<worktrees_root>/<run_id>/<worktree_id>`. Was independently redefined
    four times (measurement/evaluator.py, adapters/tools/builtin.py,
    adapters/indexer/tree_sitter.py, adapters/workspace/git_cli.py) — a pure
    string join, so it belongs here rather than behind any of those adapter
    boundaries. Module-level (not only `WorktreeRef.path`) because
    `GitCliWorktreeManager.create()` computes the path before a `WorktreeRef`
    exists to hang a method off of."""
    return os.path.join(worktrees_root, run_id, worktree_id)


class WorktreeRef(Frozen):
    worktree_id: str
    run_id: RunId
    base_commit: str
    abs_hint: str  # a *string* description for logs — never a Path (I3)

    def path(self, worktrees_root: str) -> str:
        """The on-disk location this ref names, given the root all worktrees
        share. The judge (evaluator) and the tool registry must be
        structurally unable to disagree about it (TASK-051)."""
        return worktree_path(worktrees_root, self.run_id, self.worktree_id)


class FileSlice(Frozen):
    repo_rel_path: str
    start_line: int
    end_line: int
    text: str


class PatchResult(Frozen):
    applied: bool
    rejected_hunks: int
    detail: str = ""


class SymbolHit(Frozen):
    """A syntax-tier symbol match (`ports/indexer.py`'s `Indexer.search`).

    Defined here rather than in `ports/indexer.py`, matching every other port
    payload shape in this tree (`EvalSpec`'s `WorktreeRef`, `ModelRequest`,
    `ToolResult` all live in `domain/`): `domain/` may import stdlib and
    Pydantic only (spec.md §3), so a port's own module is not the place for a
    type `domain/effects.py` also needs — `IndexArgs`/`IndexResult` (T2.4)
    would otherwise have to import `ports/`, which `domain-is-pure` forbids.
    """

    repo_rel_path: str
    line: int
    kind: str
    name: str
    snippet: str
