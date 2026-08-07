"""ToolRegistry — the tool catalog and execution boundary."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.domain.tools import ToolCall, ToolResult, ToolSpec
from aether.domain.workspace import WorktreeRef


@runtime_checkable
class ToolRegistry(Protocol):
    """Catalog frozen at composition (I6); MCP arrives later as one adapter
    of this same protocol (ADR-0016) — outputs labeled untrusted like any tool."""

    async def catalog(self) -> tuple[ToolSpec, ...]: ...

    async def execute(self, worktree: WorktreeRef, call: ToolCall) -> ToolResult: ...
