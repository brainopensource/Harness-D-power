"""Capability security dispatch choke point — see docs/02-architecture/car-model.md."""

from __future__ import annotations

import logging
import time

from sagiha.domain.content import TextBlock, ToolCall, ToolResult
from sagiha.domain.control import RunContext
from sagiha.domain.events import (
    ToolCallAuthorized,
    ToolCallCompleted,
    ToolCallDenied,
    ToolCallFailed,
    ToolCallRequested,
)
from sagiha.kernel.bus import EventBus
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


async def dispatch(
    call: ToolCall,
    ctx: RunContext,
    policy: PolicyEngine,
    governor: ResourceGovernor,
    registry: ToolRegistry,
    bus: EventBus | None = None,
) -> ToolResult:
    """Sole choke point routing tool execution from Agency intent to Runtime effect.

    Authorization, capability grant minting, lease acquisition, and outcome recording
    are enforced here. Agency code has zero direct access to runtime adapters.
    """
    start_time = time.monotonic()

    if bus is not None:
        await bus.emit(ToolCallRequested(run_id=ctx.run_id, call=call))

        intercept_decision = await bus.intercept(
            "pre_tool", ToolCallRequested(run_id=ctx.run_id, call=call)
        )
        if not intercept_decision.allowed:
            await bus.emit(
                ToolCallDenied(
                    run_id=ctx.run_id,
                    decision=intercept_decision,
                    reason=intercept_decision.reason,
                    requires_human=intercept_decision.requires_human,
                )
            )
            return ToolResult(
                content=[
                    TextBlock(
                        text=f"Pre-tool interceptor denial: {intercept_decision.reason}"
                    )
                ],
                truncated=False,
            )

    decision = await policy.authorize(call, ctx)
    if not decision.allowed or decision.grant_id is None:
        if bus is not None:
            await bus.emit(
                ToolCallDenied(
                    run_id=ctx.run_id,
                    decision=decision,
                    reason=decision.reason,
                    requires_human=decision.requires_human,
                )
            )
        return ToolResult(
            content=[TextBlock(text=f"Policy denial: {decision.reason}")],
            truncated=False,
        )

    if bus is not None:
        await bus.emit(
            ToolCallAuthorized(run_id=ctx.run_id, decision=decision)
        )

    lease_id = await governor.acquire(call.tool_name, ctx.run_id)

    try:
        try:
            result = await registry.dispatch(call)
        except Exception as exc:
            logger.error("Error executing tool '%s': %s", call.tool_name, exc, exc_info=True)
            result = ToolResult(
                content=[TextBlock(text=f"Execution failure: {exc}")],
                truncated=False,
            )
    finally:
        await governor.release(lease_id)

    await policy.record_outcome(decision.grant_id, result)

    duration_ms = (time.monotonic() - start_time) * 1000.0

    if bus is not None:
        if not result.truncated:
            await bus.emit(
                ToolCallCompleted(
                    run_id=ctx.run_id,
                    result=result,
                    duration_ms=duration_ms,
                )
            )
        else:
            await bus.emit(
                ToolCallFailed(
                    run_id=ctx.run_id,
                    error_kind="execution_error",
                    disposition="SURFACE",
                )
            )

    return result
