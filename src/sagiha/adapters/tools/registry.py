"""Default ToolRegistry implementation — see docs/02-architecture/car-model.md."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from sagiha.domain.content import EffectClass, TextBlock, ToolCall, ToolResult

ToolHandler = Callable[[dict[str, Any]], Awaitable[ToolResult]]


class DefaultToolRegistry:
    """Registry managing tool classification and execution dispatch."""

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        self._effects: dict[str, EffectClass] = {}
        self._handlers: dict[str, ToolHandler] = {}

    async def register(
        self, tool_name: str, schema: dict[str, Any], effect: EffectClass
    ) -> None:
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

    def get_effect_class(self, tool_name: str) -> EffectClass:
        return self._effects.get(tool_name, EffectClass.DESTRUCTIVE)

    async def dispatch(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.tool_name)
        if handler is None:
            return ToolResult(
                content=[TextBlock(text=f"Unknown tool '{call.tool_name}'")],
                truncated=False,
            )

        try:
            return await handler(call.arguments)
        except Exception as exc:
            return ToolResult(
                content=[TextBlock(text=f"Tool handler error: {exc}")],
                truncated=False,
            )
