"""RunLoop — multi-step agent loop with stop conditions and stuck detection (C6)."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field

from sagiha.domain.config import PricingConfig
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
from sagiha.domain.trajectory import RunRecord, TrajectoryStep
from sagiha.domain.work import (
    AcceptanceCriterion,
    CostSummary,
    GateReport,
    TaskSpec,
)
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.policy.effects import classify_command
from sagiha.outer_loop.evaluator import GateEvaluator
from sagiha.ports.evaluator import Evaluator
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.model import ModelProvider
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry
from sagiha.ports.trajectory import TrajectoryStore
from sagiha.ports.workspace import Workspace

logger = logging.getLogger(__name__)

_STUCK_REPEAT_THRESHOLD = 3


@dataclass
class RunLoopResult:
    task: TaskSpec
    gate_report: GateReport
    steps: list[TrajectoryStep]
    run_id: str
    #: What the run actually cost. Was not exposed at all before PR-1b, because there
    #: was no true figure to expose.
    cost: CostSummary = field(
        default_factory=lambda: CostSummary(
            usd=0.0, input_tokens=0, output_tokens=0, wall_clock_s=0.0, model_calls=0
        )
    )


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
        system_prompt: str = (
            "You are an autonomous software developer agent. "
            "To solve the task, you MUST use the provided tools (apply_edit, run_command). "
            "When creating or editing a file, call apply_edit directly instead of conversational text."
        ),
        tool_schemas: list[ToolSchema] | None = None,
        evaluator: Evaluator | None = None,
        workspace: Workspace | None = None,
        pricing: PricingConfig | None = None,
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
        self._workspace = workspace
        self._pricing = pricing or PricingConfig()
        self._evaluator: Evaluator = evaluator or GateEvaluator(
            policy_engine, resource_governor, tool_registry, bus
        )

    def _tool_signature(self, name: str, arguments: dict[str, object]) -> str:
        payload = json.dumps({"tool": name, "args": arguments}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _reconstruct_history(self, task: TaskSpec, existing_steps: list[TrajectoryStep]) -> list[Message]:
        """Rebuild the prompt history a resumed run would have accumulated in-process.

        Read straight from `TrajectoryStore`, not engine memory (D9) — the store is the source
        of truth for what actually happened, an in-memory list is not durable across a restart.
        """
        history: list[Message] = [Message(role="user", content=[TextBlock(text=task.goal)])]
        for step in existing_steps:
            if not step.tool_calls:
                continue
            if step.message is not None:
                # Full fidelity: replays the exact assistant turn, including any
                # text/reasoning blocks that accompanied the tool calls.
                history.append(step.message)
            else:
                # Legacy step recorded before `TrajectoryStep.message` existed (S2.5) —
                # reconstruct what we can from the derived `ToolCall`s. Any text or
                # reasoning content that accompanied them is lost; it was never stored.
                history.append(
                    Message(
                        role="assistant",
                        content=[
                            ToolUseBlock(call_id=c.call_id, tool_name=c.tool_name, arguments=c.arguments)
                            for c in step.tool_calls
                        ],
                    )
                )
            for call, result in zip(step.tool_calls, step.tool_results, strict=False):
                history.append(
                    Message(
                        role="user",
                        content=[
                            ToolResultBlock(
                                call_id=call.call_id,
                                content=list(result.content),
                                is_error=result.is_error,
                            )
                        ],
                    )
                )
        return history

    async def run(self, task: TaskSpec, ctx: RunContext, *, resume: bool = False) -> RunLoopResult:
        """Run `task` to completion (or a stop condition).

        `resume=True` continues an interrupted `ctx.run_id`: `seq` picks up from
        `TrajectoryStore.steps_for_run`'s high-water mark (D9) — never from engine memory, which
        does not survive a restart — and prior steps are folded back into `history` and the
        returned `steps` list.
        """
        existing_steps = await self._trajectory.steps_for_run(ctx.run_id) if resume else []
        start_seq = existing_steps[-1].step_id.seq + 1 if existing_steps else 1

        # Capture the base ref before step 1 — every coding gate diffs against it.
        # A resumed run keeps the sha it started from; re-checkpointing here would
        # measure the diff against the agent's own prior work and gate nothing.
        if ctx.base_commit is None and self._workspace is not None:
            try:
                ctx = ctx.model_copy(update={"base_commit": await self._workspace.checkpoint("run-start")})
            except RuntimeError:
                # Not a git workspace. Leave base_commit unset; the gates report None
                # and the run fails closed rather than claiming a pass it cannot check.
                pass

        await self._trajectory.upsert_run(RunRecord(run_id=ctx.run_id, task=task, status="working"))
        await self._bus.emit(
            RunStarted(
                run_id=ctx.run_id,
                task=task,
                run_context=ctx,
                profile=task.profile,
            )
        )

        history: list[Message] = self._reconstruct_history(task, existing_steps)
        steps: list[TrajectoryStep] = list(existing_steps)
        signature_counts: dict[str, int] = {}
        stuck = False
        failed = False
        run_usd = 0.0
        run_input_tokens = 0
        run_output_tokens = 0
        run_model_calls = 0
        run_started = time.monotonic()

        for seq in range(start_seq, start_seq + self._max_steps):
            remaining = await self._governor.remaining_budget(ctx.run_id)
            if remaining <= 0:
                failed = True
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
            digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
            await self._bus.emit(
                ModelCallStarted(
                    run_id=ctx.run_id,
                    step_id=step_id,
                    model=request.role,
                    request_digest=digest,
                )
            )

            call_started = time.monotonic()
            completion = await self._model.complete(request)
            call_seconds = time.monotonic() - call_started

            response = completion.message
            usage = completion.usage
            cost_usd = self._pricing.cost_usd(usage)

            # The call that makes `remaining_budget()` mean anything. `record_spend`
            # was implemented, correct, and invoked from nowhere in `src/` — which is
            # what made the budget break below unreachable (H2).
            await self._governor.record_spend(ctx.run_id, cost_usd)

            step_cost = CostSummary(
                usd=cost_usd,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                wall_clock_s=call_seconds,
                model_calls=1,
            )
            run_usd += cost_usd
            run_input_tokens += usage.input_tokens
            run_output_tokens += usage.output_tokens
            run_model_calls += 1

            has_tools = any(isinstance(b, ToolUseBlock) for b in response.content)
            await self._bus.emit(
                ModelCallCompleted(
                    run_id=ctx.run_id,
                    step_id=step_id,
                    usage=usage,
                    stop_reason="tool_use" if has_tools else "end_turn",
                    cost=step_cost,
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
                if block.tool_name == "run_command":
                    effect = classify_command(block.arguments.get("command", []), effect)
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
                message=response,
                usage=usage,
                cost=step_cost,
            )
            await self._trajectory.append_step(step)
            await self._bus.emit(StepCompleted(run_id=ctx.run_id, step_id=step_id, step=step))
            steps.append(step)

            if stuck:
                failed = True
                await self._bus.emit(
                    RunFailed(
                        run_id=ctx.run_id,
                        error_kind="stuck_loop",
                        disposition="ABORT",
                        message="Repeated identical tool calls",
                    )
                )
                break

        gate_report = await self._evaluator.evaluate(task, ctx)
        await self._trajectory.upsert_run(
            RunRecord(run_id=ctx.run_id, task=task, status="failed" if failed else "completed")
        )
        run_cost = CostSummary(
            usd=run_usd,
            input_tokens=run_input_tokens,
            output_tokens=run_output_tokens,
            wall_clock_s=time.monotonic() - run_started,
            model_calls=run_model_calls,
        )
        await self._bus.emit(GateEvaluated(run_id=ctx.run_id, gate_report=gate_report))
        await self._bus.emit(RunCompleted(run_id=ctx.run_id, gate_report=gate_report, cost=run_cost))
        return RunLoopResult(
            task=task, gate_report=gate_report, steps=steps, run_id=ctx.run_id, cost=run_cost
        )


def make_task(goal: str, checks: list[str], task_id: str | None = None) -> TaskSpec:
    return TaskSpec(
        task_id=task_id or str(uuid.uuid4()),
        goal=goal,
        acceptance=tuple(AcceptanceCriterion(description=c, check=c, required=True) for c in checks),
        profile="coding",
    )
