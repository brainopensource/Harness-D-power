"""EvaluateStep — calls `Evaluator.evaluate` with an `EvalSpec` built from the
task + worktree, returns the `GateReport` — the DAG's honest-zero terminal
per ADR-0002."""

from __future__ import annotations

from aether.domain.budget import BudgetDims
from aether.domain.gate import GateReport
from aether.ports.evaluator import EvalSpec
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.nodes.apply import AppliedPatch
from aether.workflow.step import StepContext, WorkflowStep


class EvaluateStep(WorkflowStep[AppliedPatch, GateReport]):
    node_kind = "evaluate"
    input_type = AppliedPatch
    output_type = GateReport

    def __init__(self, dispatch: DispatchFacade, timeout_ms: int = 60000) -> None:
        self._dispatch = dispatch
        self._timeout_ms = timeout_ms

    async def run(self, ctx: StepContext, payload: AppliedPatch) -> GateReport:
        spec = EvalSpec(
            task_id=payload.task.task_id,
            worktree=payload.worktree,
            image_digest=payload.task.environment_image_digest,
            test_command_hash=payload.task.test_command_hash,
            timeout_ms=self._timeout_ms,
        )
        return await self._dispatch.evaluate(spec, BudgetDims(wall_clock_ms=self._timeout_ms))
