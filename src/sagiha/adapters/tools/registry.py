"""Default ToolRegistry implementation — see docs/02-architecture/car-model.md."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sagiha.domain.content import EffectClass, TextBlock, ToolCall, ToolResult

ToolHandler = Callable[[dict[str, Any]], Awaitable[ToolResult]]

_JSON_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> list[str]:
    """Structural JSON-Schema-subset check (D13): required fields present, declared types match.

    Deliberately not the full `jsonschema` package — the built-in tool schemas use only
    `type`/`properties`/`required`/`items`, and pulling in a general validator for that subset
    would be a dependency the project's own <8,000 LOC / zero-framework-bloat stance argues
    against. Extend here if a schema starts using a keyword this does not cover; do not silently
    let it pass.
    """
    errors: list[str] = []
    for field in schema.get("required", []):
        if field not in arguments:
            errors.append(f"missing required field '{field}'")

    properties = schema.get("properties", {})
    for key, value in arguments.items():
        prop_schema = properties.get(key)
        if prop_schema is None:
            continue
        expected = prop_schema.get("type")
        py_type = _JSON_TYPES.get(expected) if expected else None
        if py_type is None:
            continue
        if expected == "boolean" and isinstance(value, bool):
            continue
        if expected == "integer" and isinstance(value, bool):
            errors.append(f"field '{key}' must be integer, got bool")
            continue
        if not isinstance(value, py_type):
            errors.append(f"field '{key}' must be {expected}, got {type(value).__name__}")
            continue
        if expected == "array":
            item_schema = prop_schema.get("items")
            item_type = _JSON_TYPES.get(item_schema.get("type")) if item_schema else None
            if item_type is not None:
                for i, item in enumerate(value):
                    if not isinstance(item, item_type):
                        errors.append(
                            f"field '{key}[{i}]' must be {item_schema['type']}, got {type(item).__name__}"
                        )
    return errors


class DefaultToolRegistry:
    """Registry managing tool classification and execution dispatch."""

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        self._effects: dict[str, EffectClass] = {}
        self._handlers: dict[str, ToolHandler] = {}
        #: T7 provenance at source. Absent ⇒ untrusted: a tool registered without an
        #: explicit claim has not earned one.
        self._trusted_output: dict[str, bool] = {}

    async def register(self, tool_name: str, schema: dict[str, Any], effect: EffectClass) -> None:
        self._schemas[tool_name] = schema
        self._effects[tool_name] = effect

    def register_handler(
        self,
        tool_name: str,
        schema: dict[str, Any],
        effect: EffectClass,
        handler: ToolHandler,
        *,
        trusted_output: bool = False,
    ) -> None:
        """Register a tool. `trusted_output` defaults to `False` — a tool must *claim*
        trust, never inherit it, because the cost of a wrong default in the trusting
        direction is an unlabelled attacker-controlled write path (T7)."""
        self._schemas[tool_name] = schema
        self._effects[tool_name] = effect
        self._handlers[tool_name] = handler
        self._trusted_output[tool_name] = trusted_output

    async def trusted_output(self, tool_name: str) -> bool:
        """Whether `tool_name`'s output is harness-derived rather than attacker-influenced."""
        return self._trusted_output.get(tool_name, False)

    async def get_effect_class(self, tool_name: str) -> EffectClass:
        return self._effects.get(tool_name, EffectClass.DESTRUCTIVE)

    async def effect_for_call(self, call: ToolCall) -> EffectClass:
        """Per-tool default. `run_command` is narrowed by callers in `agency`/TCB code via
        `kernel.policy.effects.classify_command` — adapters may not import `kernel` (layers
        contract), so this seam only returns the declared per-tool class here.
        """
        return await self.get_effect_class(call.tool_name)

    async def dispatch(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.tool_name)
        if handler is None:
            return ToolResult(
                call_id=call.call_id,
                content=[TextBlock(text=f"Unknown tool '{call.tool_name}'")],
                truncated=False,
                is_error=True,
                trusted=True,  # harness-authored; does not introduce external content
            )

        # D13: reject unvalidated arguments before the handler ever runs. A schema violation
        # is always the caller's fault (the model emitted arguments the registered contract
        # doesn't allow) — the handler must never see them.
        schema = self._schemas.get(call.tool_name, {})
        errors = validate_arguments(schema, call.arguments)
        if errors:
            return ToolResult(
                call_id=call.call_id,
                content=[TextBlock(text=f"Argument validation failed: {'; '.join(errors)}")],
                truncated=False,
                is_error=True,
                trusted=True,  # harness-authored; does not introduce external content
            )

        try:
            args = {**call.arguments, "_call_id": call.call_id}
            result = await handler(args)
            # T7: stamp provenance here, at the only place that knows the registration.
            # Doing it in the handler would make every handler responsible for a security
            # property, and one forgetful handler silently loses it.
            update: dict[str, Any] = {"trusted": self._trusted_output.get(call.tool_name, False)}
            if not result.call_id:
                update["call_id"] = call.call_id
            return result.model_copy(update=update)
        except Exception as exc:
            return ToolResult(
                call_id=call.call_id,
                content=[TextBlock(text=f"Tool handler error: {exc}")],
                truncated=False,
                is_error=True,
                trusted=True,  # harness-authored; does not introduce external content
            )
