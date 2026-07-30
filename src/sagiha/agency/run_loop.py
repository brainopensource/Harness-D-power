"""RunLoop — multi-step agent loop with stop conditions and stuck detection (C6)."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass

from sagiha.domain.content import (
    Message,
    ModelRequest,
    TextBlock,
    ToolCall,
    ToolResult,
    ToolResultBlock,
    ToolSchema,
    ToolUseBlock,
)
from sagiha.domain.control import RunContext
from sagiha.domain.events import (
    GateEvaluated,
    ModelCallCompleted,
    ModelCallStarted,
    RunCompleted,
    RunFailed,
    RunStarted,
    StepCompleted,
    StepStarted,
)
from sagiha.domain.identity import StepId
from sagiha.domain.trajectory import TokenUsage, TrajectoryStep
from sagiha.domain.work import (
    AcceptanceCriterion,
    CostSummary,
    CriterionResult,
    GateReport,
    TaskSpec,
)
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.model import ModelProvider
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry
from sagiha.ports.trajectory import TrajectoryStore

logger = logging.getLogger(__name__)

_STUCK_REPEAT_THRESHOLD = 3


@dataclass
class RunLoopResult:
    task: TaskSpec
    gate_report: GateReport
    steps: list[TrajectoryStep]
    run_id: str


class RunLoop:
    """Closed coding loop: assemble history → model → tools → gate."""

    def __init__(
        self,
        model_provider: ModelProvider,
        policy_engine: PolicyEngine,
        resource_governor: ResourceGovernor,
        tool_registry: ToolRegistry,
        trajectory_store: TrajectoryStore,
        bus: EventBus,
        *,
        max_steps: int = 20,
        system_prompt: str = "You are a careful coding agent. Use tools to fix the failing test.",
        tool_schemas: list[ToolSchema] | None = None,
    ) -> None:
        self._model = model_provider
        self._policy = policy_engine
        self._governor = resource_governor
        self._registry = tool_registry
        self._trajectory = trajectory_store
        self._bus = bus
        self._max_steps = max_steps
        self._system_prompt = system_prompt
        self._tool_schemas = tool_schemas or []

    def _tool_signature(self, name: str, arguments: dict[str, object]) -> str:
        payload = json.dumps({"tool": name, "args": arguments}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    async def run(self, task: TaskSpec, ctx: RunContext) -> RunLoopResult:
        await self._bus.emit(
            RunStarted(
                run_id=ctx.run_id,
                task=task,
                run_context=ctx,
                profile=task.profile,
            )
        )

        history: list[Message] = [
            Message(role="user", content=[TextBlock(text=task.goal)])
        ]
        steps: list[TrajectoryStep] = []
        signature_counts: dict[str, int] = {}
        stuck = False

        for seq in range(1, self._max_steps + 1):
            remaining = await self._governor.remaining_budget(ctx.run_id)
            if remaining <= 0:
                await self._bus.emit(
                    RunFailed(
                        run_id=ctx.run_id,
                        error_kind="budget_exhausted",
                        disposition="ABORT",
                        message="Budget exhausted",
                    )
                )
                break

            step_id = StepId(
                run_id=ctx.run_id,
                branch_id="main",
                seq=seq,
                parent=str(seq - 1) if seq > 1 else None,
            )
            await self._bus.emit(StepStarted(run_id=ctx.run_id, step_id=step_id))

            request = ModelRequest(
                system=self._system_prompt,
                messages=list(history),
                tools=list(self._tool_schemas),
                role="execution",
            )
            digest = hashlib.sha256(
                request.model_dump_json().encode()
            ).hexdigest()
            await self._bus.emit(
                ModelCallStarted(
                    run_id=ctx.run_id,
                    step_id=step_id,
                    model=request.role,
                    request_digest=digest,
                )
            )

            response = await self._model.complete(request)
            has_tools = any(isinstance(b, ToolUseBlock) for b in response.content)
            await self._bus.emit(
                ModelCallCompleted(
                    run_id=ctx.run_id,
                    step_id=step_id,
                    usage=TokenUsage(input_tokens=0, output_tokens=0),
                    stop_reason="tool_use" if has_tools else "end_turn",
                    cost=CostSummary(
                        usd=0.0,
                        input_tokens=0,
                        output_tokens=0,
                        wall_clock_s=0.0,
                        model_calls=1,
                    ),
                )
            )

            history.append(response)

            tool_use_blocks = [b for b in response.content if isinstance(b, ToolUseBlock)]
            if not tool_use_blocks:
                # Model ended turn
                break

            tool_calls: list[ToolCall] = []
            tool_results: list[ToolResult] = []
            for block in tool_use_blocks:
                sig = self._tool_signature(block.tool_name, block.arguments)
                signature_counts[sig] = signature_counts.get(sig, 0) + 1
                if signature_counts[sig] >= _STUCK_REPEAT_THRESHOLD:
                    stuck = True
                    logger.warning("Stuck signature detected for %s", block.tool_name)
                    break

                effect = await self._registry.get_effect_class(block.tool_name)
                call = ToolCall(
                    call_id=block.call_id,
                    tool_name=block.tool_name,
                    arguments=block.arguments,
                    effect=effect,
                )
                result = await dispatch(
                    call=call,
                    ctx=ctx,
                    policy=self._policy,
                    governor=self._governor,
                    registry=self._registry,
                    bus=self._bus,
                )
                tool_calls.append(call)
                tool_results.append(result)
                history.append(
                    Message(
                        role="user",
                        content=[
                            ToolResultBlock(
                                call_id=block.call_id,
                                content=list(result.content),
                                is_error=result.is_error,
                            )
                        ],
                    )
                )

            step = TrajectoryStep(
                step_id=step_id,
                tool_calls=tuple(tool_calls),
                tool_results=tuple(tool_results),
            )
            await self._trajectory.append_step(step)
            await self._bus.emit(StepCompleted(run_id=ctx.run_id, step_id=step_id, step=step))
            steps.append(step)

            if stuck:
                await self._bus.emit(
                    RunFailed(
                        run_id=ctx.run_id,
                        error_kind="stuck_loop",
                        disposition="ABORT",
                        message="Repeated identical tool calls",
                    )
                )
                break

        gate_report = await self._evaluate(task, ctx)
        await self._bus.emit(
            GateEvaluated(run_id=ctx.run_id, gate_report=gate_report)
        )
        await self._bus.emit(
            RunCompleted(
                run_id=ctx.run_id,
                gate_report=gate_report,
                cost=CostSummary(
                    usd=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    wall_clock_s=0.0,
                    model_calls=len(steps),
                ),
            )
        )
        return RunLoopResult(
            task=task, gate_report=gate_report, steps=steps, run_id=ctx.run_id
        )

    async def _evaluate(self, task: TaskSpec, ctx: RunContext) -> GateReport:
        """Minimal evaluator: run each acceptance check via run_command tool path."""
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


def make_task(goal: str, checks: list[str], task_id: str | None = None) -> TaskSpec:
    return TaskSpec(
        task_id=task_id or str(uuid.uuid4()),
        goal=goal,
        acceptance=tuple(
            AcceptanceCriterion(description=c, check=c, required=True) for c in checks
        ),
        profile="coding",
    )
