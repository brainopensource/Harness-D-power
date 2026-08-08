"""Evaluator — TCB. Implementation resides in measurement/, never adapters/ (spec.md §4)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.domain.gate import GateReport
from aether.domain.ids import Frozen, TaskId
from aether.domain.workspace import WorktreeRef


class EvalSpec(Frozen):
    task_id: TaskId
    worktree: WorktreeRef
    image_digest: str  # pinned in the task manifest (TCB data)
    test_command_hash: str  # verified against manifest before run
    timeout_ms: int
    base_commit: str = ""  # pinned commit the I7 diff check runs against
    test_paths: tuple[str, ...] = ()  # repo-relative globs; a candidate must not touch these (I7)


@runtime_checkable
class Evaluator(Protocol):
    """TCB. Runs the task's real tests in the evaluation container
    (network none, digest-pinned). Exit-127 / uncollectable => GateStatus.NONE
    with instrument_error set — never FAILED (B4)."""

    async def evaluate(self, spec: EvalSpec) -> GateReport: ...
