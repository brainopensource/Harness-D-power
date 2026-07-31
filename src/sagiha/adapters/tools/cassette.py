"""Cassette record/replay ToolRegistry — see docs/08-decisions/0020-per-invocation-effect-classification.md.

Mirrors `adapters/model/cassette.py`'s digest-keyed record/replay shape, but for tool
dispatch: `PURE`-classified calls (per `ToolCall.effect`, already narrowed by
`kernel.policy.effects.classify_command` upstream in `agency`/TCB code) always re-execute
against the wrapped live registry, live or replay. `DESTRUCTIVE`/`IDEMPOTENT` calls execute
and get recorded in `record` mode, and are served from the recording — never re-executed —
in `replay` mode. This is what makes `replay --verify` a real workspace check for the
majority-`PURE` command steps in a trajectory, instead of a request-digest check only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from sagiha.adapters.tools.registry import DefaultToolRegistry, ToolHandler
from sagiha.domain.content import EffectClass, ToolCall, ToolResult


class ToolCassetteMismatchError(RuntimeError):
    """Raised when a replayed DESTRUCTIVE/IDEMPOTENT call has no matching recording."""


def call_digest(tool_name: str, arguments: dict[str, Any]) -> str:
    payload = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ToolCassetteEntry(BaseModel):
    digest: str
    result: ToolResult


class CassetteToolRegistry:
    """Wraps a live `DefaultToolRegistry`; re-executes `PURE` calls, records/replays the rest."""

    def __init__(
        self,
        inner: DefaultToolRegistry,
        cassette_path: str,
        mode: Literal["record", "replay", "live"] = "live",
    ) -> None:
        self._inner = inner
        self._cassette_path = Path(cassette_path)
        self._mode = mode
        self._entries: dict[str, list[ToolCassetteEntry]] = {}
        self._cursors: dict[str, int] = {}
        self.re_executed = 0
        self.served_from_cassette = 0

        if self._cassette_path.exists():
            for item in json.loads(self._cassette_path.read_text()):
                entry = ToolCassetteEntry.model_validate(item)
                self._entries.setdefault(entry.digest, []).append(entry)

    def register_handler(
        self, tool_name: str, schema: dict[str, Any], effect: EffectClass, handler: ToolHandler
    ) -> None:
        self._inner.register_handler(tool_name, schema, effect, handler)

    async def register(self, tool_name: str, schema: dict[str, Any], effect: EffectClass) -> None:
        await self._inner.register(tool_name, schema, effect)

    async def get_effect_class(self, tool_name: str) -> EffectClass:
        return await self._inner.get_effect_class(tool_name)

    async def effect_for_call(self, call: ToolCall) -> EffectClass:
        return await self._inner.effect_for_call(call)

    def _record(self, digest: str, result: ToolResult) -> None:
        if self._mode != "record":
            return
        self._entries.setdefault(digest, []).append(ToolCassetteEntry(digest=digest, result=result))
        all_entries = [e for group in self._entries.values() for e in group]
        self._cassette_path.parent.mkdir(parents=True, exist_ok=True)
        self._cassette_path.write_text(json.dumps([e.model_dump(mode="json") for e in all_entries], indent=2))

    async def dispatch(self, call: ToolCall) -> ToolResult:
        digest = call_digest(call.tool_name, call.arguments)

        if call.effect is EffectClass.PURE:
            result = await self._inner.dispatch(call)
            self.re_executed += 1
            self._record(digest, result)
            return result

        if self._mode == "replay":
            group = self._entries.get(digest, [])
            cursor = self._cursors.get(digest, 0)
            if cursor >= len(group):
                raise ToolCassetteMismatchError(
                    f"no recorded result for {call.tool_name}({call.arguments!r}) [digest={digest}]"
                )
            self._cursors[digest] = cursor + 1
            self.served_from_cassette += 1
            return group[cursor].result.model_copy(update={"call_id": call.call_id})

        result = await self._inner.dispatch(call)
        self.re_executed += 1
        self._record(digest, result)
        return result
