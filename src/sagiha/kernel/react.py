"""Deterministic Async ReAct Microkernel State Machine.

See docs/04-workflows-and-loops/dmartic-inner-loop.md.
"""

from __future__ import annotations

import logging

from sagiha.domain.content import (
    Message,
    ModelRequest,
    TextBlock,
    ToolCall,
    ToolResult,
    ToolUseBlock,
)
from sagiha.domain.control import RunContext
from sagiha.domain.identity import StepId
from sagiha.domain.trajectory import TrajectoryStep
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.model import ModelProvider
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry
from sagiha.ports.trajectory import TrajectoryStore

logger = logging.getLogger(__name__)


class ReActEngine:
    """Async ReAct loop managing prompt assembly, model reasoning, and capability dispatch."""

    def __init__(
        self,
        model_provider: ModelProvider,
        policy_engine: PolicyEngine,
        resource_governor: ResourceGovernor,
        tool_registry: ToolRegistry,
        trajectory_store: TrajectoryStore | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._model = model_provider
        self._policy = policy_engine
        self._governor = resource_governor
        self._registry = tool_registry
        self._trajectory = trajectory_store
        self._bus = bus
        self._step_sequence: dict[str, int] = {}

    async def _resolve_tool_calls(self, model_response: Message) -> list[ToolCall]:
        """Collect ToolUseBlocks and resolve effect from the registry (D1 / D11)."""
        tool_calls: list[ToolCall] = []
        for block in model_response.content:
            if isinstance(block, ToolUseBlock):
                effect = await self._registry.get_effect_class(block.tool_name)
                tool_calls.append(
                    ToolCall(
                        call_id=block.call_id,
                        tool_name=block.tool_name,
                        arguments=block.arguments,
                        effect=effect,
                    )
                )
            elif isinstance(block, ToolCall):
                effect = await self._registry.get_effect_class(block.tool_name)
                tool_calls.append(block.model_copy(update={"effect": effect}))
        return tool_calls

    async def step(self, ctx: RunContext, prompt: str) -> TrajectoryStep:
        """Executes a single ReAct step: Prompt -> Model -> Parse -> Dispatch Tool -> Record."""
        seq = self._step_sequence.get(ctx.run_id, 0) + 1
        self._step_sequence[ctx.run_id] = seq

        step_id = StepId(
            run_id=ctx.run_id,
            branch_id="main",
            seq=seq,
            parent=str(seq - 1) if seq > 1 else None,
        )

        request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text=prompt)])])

        model_response = await self._model.complete(request)
        tool_calls = await self._resolve_tool_calls(model_response)

        tool_results: list[ToolResult] = []
        for call in tool_calls:
            res = await dispatch(
                call=call,
                ctx=ctx,
                policy=self._policy,
                governor=self._governor,
                registry=self._registry,
                bus=self._bus,
            )
            tool_results.append(res)

        step_record = TrajectoryStep(
            step_id=step_id,
            tool_calls=tuple(tool_calls),
            tool_results=tuple(tool_results),
        )

        if self._trajectory is not None:
            await self._trajectory.append_step(step_record)

        return step_record
