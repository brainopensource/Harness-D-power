"""EvaluateStep — calls `Evaluator.evaluate` with an `EvalSpec` built from the
task + worktree, returns an `EvaluatedCandidate` carrying the `GateReport` —
the DAG's honest-zero terminal per ADR-0002.

The output socket became `EvaluatedCandidate` rather than a bare `GateReport`
in Sprint 3 (TASK-023). The repair edge is `evaluate →(fail, k)→ repair`, and
the repair node needs the task, the worktree and the attempt it is repairing,
not only the verdict. Keeping the verdict alone as the socket type would have
forced the executor to smuggle that context past the type system — which is
the same class of hole the socket types exist to close.
"""

from __future__ import annotations

from aether.domain.budget import BudgetDims
from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import Frozen
from aether.domain.task import Task
from aether.domain.workspace import WorktreeRef
from aether.ports.evaluator import EvalSpec
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.nodes.apply import AppliedPatch
from aether.workflow.step import StepContext, WorkflowStep


class EvaluatedCandidate(Frozen):
    task: Task
    worktree: WorktreeRef
    report: GateReport
    patch_text: str = ""
    iteration: int = 0


class EvaluateStep(WorkflowStep[AppliedPatch, EvaluatedCandidate]):
    node_kind = "evaluate"
    input_type = AppliedPatch
    output_type = EvaluatedCandidate

    def __init__(self, dispatch: DispatchFacade, timeout_ms: int = 60000) -> None:
        self._dispatch = dispatch
        self._timeout_ms = timeout_ms

    async def run(self, ctx: StepContext, payload: AppliedPatch) -> EvaluatedCandidate:
        # An instrument failure upstream is reported as one, and the tests are
        # not run: executing them would score an unmodified worktree and return
        # a confident FAILED for a candidate that was never produced. The
        # executor's "NONE never routes into repair" rule then covers this for
        # free — repairing against our own transport failure would teach the
        # loop to fix the harness instead of the task.
        if payload.instrument_error is not None:
            return EvaluatedCandidate(
                task=payload.task,
                worktree=payload.worktree,
                report=GateReport(
                    gate="tests",
                    status=GateStatus.NONE,
                    detail=payload.detail,
                    instrument_error=payload.instrument_error,
                ),
                patch_text=payload.patch_text,
                iteration=payload.iteration,
            )

        spec = EvalSpec(
            task_id=payload.task.task_id,
            worktree=payload.worktree,
            image_digest=payload.task.environment_image_digest,
            test_command_hash=payload.task.test_command_hash,
            timeout_ms=self._timeout_ms,
            base_commit=payload.task.base_commit,
            test_paths=payload.task.test_paths,
        )
        report = await self._dispatch.evaluate(spec, BudgetDims(wall_clock_ms=self._timeout_ms))
        return EvaluatedCandidate(
            task=payload.task,
            worktree=payload.worktree,
            report=report,
            patch_text=payload.patch_text,
            iteration=payload.iteration,
        )
