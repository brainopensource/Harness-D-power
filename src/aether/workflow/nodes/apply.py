"""ApplyStep — takes the generated patch text and calls `Workspace.apply_patch`."""

from __future__ import annotations

from aether.composition import ApplyPatchArgs
from aether.domain.budget import BudgetDims
from aether.domain.ids import Frozen
from aether.domain.task import Task
from aether.domain.workspace import WorktreeRef
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.nodes.generate import GeneratedPatch
from aether.workflow.step import StepContext, WorkflowStep


class AppliedPatch(Frozen):
    task: Task
    worktree: WorktreeRef
    applied: bool
    detail: str = ""


class ApplyStep(WorkflowStep[GeneratedPatch, AppliedPatch]):
    node_kind = "apply"
    input_type = GeneratedPatch
    output_type = AppliedPatch

    def __init__(self, dispatch: DispatchFacade) -> None:
        self._dispatch = dispatch

    async def run(self, ctx: StepContext, payload: GeneratedPatch) -> AppliedPatch:
        args = ApplyPatchArgs(worktree=payload.worktree, unified_diff=payload.patch_text)
        result = await self._dispatch.apply_patch(args, BudgetDims(wall_clock_ms=10000))
        return AppliedPatch(
            task=payload.task, worktree=payload.worktree, applied=result.applied, detail=result.detail
        )
