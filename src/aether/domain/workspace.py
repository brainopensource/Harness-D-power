"""Worktree reference and file-slice/patch shapes for the Workspace boundary."""

from __future__ import annotations

from aether.domain.ids import Frozen, RunId


class WorktreeRef(Frozen):
    worktree_id: str
    run_id: RunId
    base_commit: str
    abs_hint: str  # a *string* description for logs — never a Path (I3)


class FileSlice(Frozen):
    repo_rel_path: str
    start_line: int
    end_line: int
    text: str


class PatchResult(Frozen):
    applied: bool
    rejected_hunks: int
    detail: str = ""
