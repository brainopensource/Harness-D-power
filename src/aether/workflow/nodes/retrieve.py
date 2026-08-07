"""RetrieveStep — reads task instructions + a bounded initial file slice via
`Workspace.read`. No `Indexer` dependency (out of M1a's four boundaries)."""

from __future__ import annotations

from aether.composition import ReadArgs
from aether.domain.budget import BudgetDims
from aether.domain.ids import Frozen
from aether.domain.task import Task
from aether.domain.workspace import FileSlice, WorktreeRef
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.step import StepContext, WorkflowStep


class TaskInput(Frozen):
    task: Task
    worktree: WorktreeRef


class RetrievedContext(Frozen):
    task: Task
    worktree: WorktreeRef
    instructions: str
    file_slice: FileSlice | None = None


class RetrieveStep(WorkflowStep[TaskInput, RetrievedContext]):
    node_kind = "retrieve"
    input_type = TaskInput
    output_type = RetrievedContext

    def __init__(self, dispatch: DispatchFacade, entry_file: str = "README.md") -> None:
        self._dispatch = dispatch
        self._entry_file = entry_file

    async def run(self, ctx: StepContext, payload: TaskInput) -> RetrievedContext:
        file_slice: FileSlice | None = None
        try:
            args = ReadArgs(worktree=payload.worktree, repo_rel_path=self._entry_file)
            file_slice = await self._dispatch.read(args, BudgetDims(wall_clock_ms=5000))
        except Exception:
            file_slice = None  # best-effort: entry file may not exist in this repo

        return RetrievedContext(
            task=payload.task,
            worktree=payload.worktree,
            instructions=payload.task.instructions,
            file_slice=file_slice,
        )
