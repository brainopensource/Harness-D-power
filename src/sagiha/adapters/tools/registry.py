"""Default ToolRegistry implementation — see docs/02-architecture/car-model.md."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sagiha.domain.content import EffectClass, TextBlock, ToolCall, ToolResult

ToolHandler = Callable[[dict[str, Any]], Awaitable[ToolResult]]


class DefaultToolRegistry:
    """Registry managing tool classification and execution dispatch."""

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        self._effects: dict[str, EffectClass] = {}
        self._handlers: dict[str, ToolHandler] = {}

    async def register(self, tool_name: str, schema: dict[str, Any], effect: EffectClass) -> None:
        self._schemas[tool_name] = schema
        self._effects[tool_name] = effect

    def register_handler(
        self,
        tool_name: str,
        schema: dict[str, Any],
        effect: EffectClass,
        handler: ToolHandler,
    ) -> None:
        self._schemas[tool_name] = schema
        self._effects[tool_name] = effect
        self._handlers[tool_name] = handler

    async def get_effect_class(self, tool_name: str) -> EffectClass:
        return self._effects.get(tool_name, EffectClass.DESTRUCTIVE)

    async def dispatch(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.tool_name)
        if handler is None:
            return ToolResult(
                call_id=call.call_id,
                content=[TextBlock(text=f"Unknown tool '{call.tool_name}'")],
                truncated=False,
                is_error=True,
            )

        try:
            args = {**call.arguments, "_call_id": call.call_id}
            result = await handler(args)
            if not result.call_id:
                return result.model_copy(update={"call_id": call.call_id})
            return result
        except Exception as exc:
            return ToolResult(
                call_id=call.call_id,
                content=[TextBlock(text=f"Tool handler error: {exc}")],
                truncated=False,
                is_error=True,
            )
