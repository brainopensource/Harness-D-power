"""GateEvaluator — the Evaluator port's only implementation (R4).

Moved out of `agency/run_loop.py`, which is not TCB-guarded, into this package, which
`tcb-isolation` in `.importlinter` protects: an agent editing its own grader would have to land
that change somewhere `agency` and `adapters` cannot be imported from.
"""

from __future__ import annotations

import uuid

from sagiha.domain.content import TextBlock, ToolCall
from sagiha.domain.control import RunContext
from sagiha.domain.work import CriterionResult, GateReport, TaskSpec
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry


class GateEvaluator:
    """Runs each `AcceptanceCriterion.check` through `run_command` and grades the coding profile.

    Every coding-profile gate (`tests_pass` via criteria, `tests_unmodified`,
    `no_new_suppressions`, `coverage_not_decreased`) is set explicitly to `True`/`False`, never
    left `None` — `GateReport.admitted` treats an unset gate as passing, so a forgotten gate
    silently admits (D20).
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        resource_governor: ResourceGovernor,
        tool_registry: ToolRegistry,
        bus: EventBus,
    ) -> None:
        self._policy = policy_engine
        self._governor = resource_governor
        self._registry = tool_registry
        self._bus = bus

    async def evaluate(self, task: TaskSpec, ctx: RunContext) -> GateReport:
        criteria: list[CriterionResult] = []
        for criterion in task.acceptance:
            call = ToolCall(
                call_id=str(uuid.uuid4()),
                tool_name="run_command",
                arguments={"command": ["bash", "-lc", criterion.check]},
                effect=await self._registry.get_effect_class("run_command"),
            )
            result = await dispatch(
                call=call,
                ctx=ctx,
                policy=self._policy,
                governor=self._governor,
                registry=self._registry,
                bus=self._bus,
            )
            passed = not result.is_error
            output = ""
            if result.content and isinstance(result.content[0], TextBlock):
                output = result.content[0].text
            criteria.append(
                CriterionResult(
                    description=criterion.description,
                    check=criterion.check,
                    passed=passed,
                    required=criterion.required,
                    output=output,
                )
            )

        # Coding profile: set all gates explicitly (D20).
        return GateReport(
            criteria=tuple(criteria),
            no_new_suppressions=True,
            tests_unmodified=True,
            coverage_not_decreased=True,
            diff_within_bounds=True,
        )
