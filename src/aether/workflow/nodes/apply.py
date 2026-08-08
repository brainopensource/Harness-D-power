"""ApplyStep — turns a model's reply into writes in the candidate worktree.

The node no longer knows what a patch *looks like*. It asks the node's
`EditFormat` to parse the reply and then performs whatever that produced, so a
new format is a class in `workflow/edit_format.py` and a line of YAML rather
than a change here.

Every write still goes through the dispatch facade, so the choke point sees
them (I5) — a format that wrote files itself would be a second path to the
worktree, which is the thing the choke point exists to make impossible.
"""

from __future__ import annotations

from aether.domain.budget import BudgetDims
from aether.domain.effects import ApplyPatchArgs, WriteArgs
from aether.domain.ids import Frozen
from aether.domain.task import Task
from aether.domain.workspace import WorktreeRef
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.edit_format import DEFAULT_EDIT_FORMAT, get_edit_format
from aether.workflow.nodes.generate import GeneratedPatch
from aether.workflow.step import StepContext, WorkflowStep


class AppliedPatch(Frozen):
    task: Task
    worktree: WorktreeRef
    applied: bool
    detail: str = ""
    # The reply that was applied, carried forward: the repair edge (TASK-023)
    # needs to see the attempt it is repairing, not just that one happened.
    patch_text: str = ""
    #: Paths actually written. Empty for a diff that did not apply.
    files_changed: tuple[str, ...] = ()
    iteration: int = 0
    #: Set when *our instrument* failed before the candidate could be judged —
    #: today, only a `provider_error` completion. `EvaluateStep` turns this into
    #: `GateStatus.NONE` instead of running the tests, because a worktree the
    #: model never got to edit is not a failed attempt. Distinct from `detail`,
    #: which reports why a *real* model reply could not be applied.
    instrument_error: str | None = None


class ApplyStep(WorkflowStep[GeneratedPatch, AppliedPatch]):
    node_kind = "apply"
    input_type = GeneratedPatch
    output_type = AppliedPatch

    def __init__(self, dispatch: DispatchFacade, edit_format: str = DEFAULT_EDIT_FORMAT) -> None:
        self._dispatch = dispatch
        self._edit_format = get_edit_format(edit_format)

    async def run(self, ctx: StepContext, payload: GeneratedPatch) -> AppliedPatch:
        # Checked before parsing, because there is nothing to parse: a provider
        # error yields an empty completion, which is indistinguishable from a
        # model that answered with nothing. Scoring the two the same way put our
        # own transport failures into the resolve-rate denominator as task
        # failures (measurement.md §2 B4).
        if payload.stop_reason == "provider_error":
            return AppliedPatch(
                task=payload.task,
                worktree=payload.worktree,
                applied=False,
                detail="the model provider did not return a completion",
                patch_text=payload.raw_output,
                iteration=payload.iteration,
                instrument_error=(
                    "model provider failed (transport, HTTP or truncated stream); "
                    "no completion was produced, so this candidate was never measured"
                ),
            )

        # The node's own format wins over whatever produced the text: a
        # topology that generates one shape and applies another is a
        # configuration error, and honouring the apply node's declaration is
        # what makes it visible immediately rather than three nodes later.
        parsed = self._edit_format.parse(payload.raw_output)

        if parsed.errors:
            return AppliedPatch(
                task=payload.task,
                worktree=payload.worktree,
                applied=False,
                detail="; ".join(parsed.errors),
                patch_text=payload.raw_output,
                iteration=payload.iteration,
            )

        if parsed.is_empty:
            return AppliedPatch(
                task=payload.task,
                worktree=payload.worktree,
                applied=False,
                detail="the model produced no edit",
                patch_text=payload.raw_output,
                iteration=payload.iteration,
            )

        if parsed.kind == "unified_diff":
            result = await self._dispatch.apply_patch(
                ApplyPatchArgs(worktree=payload.worktree, unified_diff=parsed.unified_diff),
                BudgetDims(wall_clock_ms=10000),
            )
            return AppliedPatch(
                task=payload.task,
                worktree=payload.worktree,
                applied=result.applied,
                detail=result.detail,
                patch_text=payload.raw_output,
                iteration=payload.iteration,
            )

        for file_edit in parsed.files:
            await self._dispatch.write(
                WriteArgs(
                    worktree=payload.worktree,
                    repo_rel_path=file_edit.repo_rel_path,
                    text=file_edit.text,
                ),
                BudgetDims(wall_clock_ms=5000),
            )
        return AppliedPatch(
            task=payload.task,
            worktree=payload.worktree,
            applied=True,
            detail=f"wrote {len(parsed.files)} file(s)",
            patch_text=payload.raw_output,
            files_changed=tuple(f.repo_rel_path for f in parsed.files),
            iteration=payload.iteration,
        )
