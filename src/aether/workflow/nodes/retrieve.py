"""RetrieveStep — reads the task instructions plus the files the node names.

Sprint 3 read exactly **one** file, defaulting to `README.md`. Against real
models that was the single largest capability defect in the harness: the model
was asked to patch code it had never seen, and it did the only thing it could —
invented a plausible file and produced a diff against fiction. Three local
models scored 0/8 on trivial tasks this way.

So a node now names the files it needs (`params.entry_files`) and gets a byte
ceiling (`params.max_bytes`) so a large file cannot silently eat the prompt.
Missing files are reported in `missing`, never silently skipped: "the model was
not shown the file" and "the model was shown the file and failed" are different
diagnoses, and the second is only believable when the first is excluded.

Still no `Indexer` here (out of M1a's four boundaries) — retrieval by symbol,
call graph or embedding is a later, ablatable mechanism. This node's job is to
put *named* files in front of the model, honestly.
"""

from __future__ import annotations

from aether.domain.budget import BudgetDims
from aether.domain.effects import ReadArgs
from aether.domain.envelope import Envelope
from aether.domain.workspace import FileSlice
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.step import StepContext, WorkflowStep


class TaskInput(Envelope):
    pass


class RetrievedContext(Envelope):
    instructions: str
    #: Every file this node actually read, in the order it was asked for.
    files: tuple[FileSlice, ...] = ()
    #: Named but unreadable. Published, not swallowed — see the module docstring.
    missing: tuple[str, ...] = ()
    plan: str = ""

    @property
    def file_slice(self) -> FileSlice | None:
        """The first retrieved file. Kept so Sprint 2's single-file callers and
        their tests keep working while the plural form becomes the real one."""
        return self.files[0] if self.files else None


class RetrieveStep(WorkflowStep[TaskInput, RetrievedContext]):
    node_kind = "retrieve"
    input_type = TaskInput
    output_type = RetrievedContext

    def __init__(
        self,
        dispatch: DispatchFacade,
        entry_files: tuple[str, ...] = ("README.md",),
        max_bytes: int = 20_000,
    ) -> None:
        self._dispatch = dispatch
        self._entry_files = entry_files
        self._max_bytes = max_bytes

    async def run(self, ctx: StepContext, payload: TaskInput) -> RetrievedContext:
        files: list[FileSlice] = []
        missing: list[str] = []
        budget_left = self._max_bytes

        for repo_rel_path in self._entry_files:
            if budget_left <= 0:
                missing.append(f"{repo_rel_path} (byte budget exhausted)")
                continue
            try:
                args = ReadArgs(worktree=payload.worktree, repo_rel_path=repo_rel_path)
                file_slice = await self._dispatch.read(args, BudgetDims(wall_clock_ms=5000))
            except Exception as exc:  # noqa: BLE001 — a missing file is a fact, not a crash
                missing.append(f"{repo_rel_path} ({type(exc).__name__})")
                continue

            text = file_slice.text[:budget_left]
            budget_left -= len(text)
            files.append(file_slice.model_copy(update={"text": text}))

        return RetrievedContext(
            task=payload.task,
            worktree=payload.worktree,
            instructions=payload.task.instructions,
            files=tuple(files),
            missing=tuple(missing),
        )
