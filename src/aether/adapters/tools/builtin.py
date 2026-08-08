"""Built-in ToolRegistry adapter (TASK-018) — the tool catalog and execution
boundary.

First real adapter for `ToolRegistry` (ADR-0005 rev. 2); MCP (ADR-0016) is a
second adapter of this same port, later. Catalog is a fixed tuple built once
in `__init__` (I6 — frozen at composition); there is no mutator method, so
runtime registration is structurally impossible, not merely disallowed.

Every `ToolResult.spans` entry is labeled `Provenance.UNTRUSTED_EXTERNAL` at
the point `execute()` constructs the result — a caller never has to remember
to taint a tool output afterward (ADR-0015).

Runs uncontained this sprint via `asyncio.subprocess` scoped to the worktree
directory (mirrors `GitCliWorkspace`'s own path convention) — the same
precedent the Evaluator ships under. `containers/tools/Containerfile` is a
Sprint-3/B3 scaffold, unused by this module.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from aether.adapters.subprocess_env import spawn_env
from aether.domain.ids import SpanId
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.tools import ToolCall, ToolResult, ToolSpec
from aether.domain.workspace import WorktreeRef
from aether.ports.workspace import Workspace

#: Matches the cost estimate `workflow/nodes/generate.py` reserves against
#: (`BudgetDims(wall_clock_ms=30000)`) — the fallback when a caller does not
#: thread a real lease-derived deadline through `execute()`. TASK-062: this
#: used to be no deadline at all; a hung tool call ran forever.
_DEFAULT_DEADLINE_MS = 30_000

_READ_FILE_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer", "default": 1},
            "end_line": {"type": "integer", "default": -1},
        },
        "required": ["path"],
    }
)

_BASH_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }
)


class BuiltinToolRegistry:
    def __init__(self, workspace: Workspace, worktrees_root: str) -> None:
        self._workspace = workspace
        self._worktrees_root = worktrees_root
        self._catalog: tuple[ToolSpec, ...] = (
            ToolSpec(
                name="read_file",
                description="Read a line-range slice of a file in the worktree.",
                params_json_schema=_READ_FILE_SCHEMA,
                effect_class="read",
            ),
            ToolSpec(
                name="bash",
                description="Run a shell command scoped to the worktree directory.",
                params_json_schema=_BASH_SCHEMA,
                effect_class="shell",
            ),
        )

    async def catalog(self) -> tuple[ToolSpec, ...]:
        return self._catalog

    async def execute(
        self, worktree: WorktreeRef, call: ToolCall, deadline_ms: int | None = None
    ) -> ToolResult:
        args: dict[str, object] = json.loads(call.args_json) if call.args_json else {}

        if call.name == "read_file":
            text, exit_code = await self._read_file(worktree, args)
        elif call.name == "bash":
            text, exit_code = await self._bash(worktree, args, deadline_ms)
        else:
            text, exit_code = f"unknown tool: {call.name}", 127

        span = TaintSpan(
            span_id=SpanId(f"tool-{call.call_id}"),
            label=Provenance.UNTRUSTED_EXTERNAL,
            text=text,
            source=f"tool:{call.name}",
            created_at=datetime.now(UTC),
        )
        return ToolResult(call_id=call.call_id, spans=(span,), exit_code=exit_code)

    async def _read_file(self, worktree: WorktreeRef, args: dict[str, object]) -> tuple[str, int]:
        try:
            file_slice = await self._workspace.read(
                worktree,
                str(args["path"]),
                int(args.get("start_line", 1)),  # type: ignore[arg-type]
                int(args.get("end_line", -1)),  # type: ignore[arg-type]
            )
            return file_slice.text, 0
        except OSError as exc:
            return str(exc), 1

    async def _bash(
        self, worktree: WorktreeRef, args: dict[str, object], deadline_ms: int | None = None
    ) -> tuple[str, int]:
        path = worktree.path(self._worktrees_root)
        deadline = (deadline_ms if deadline_ms and deadline_ms > 0 else _DEFAULT_DEADLINE_MS) / 1000
        proc = await asyncio.create_subprocess_shell(
            str(args["command"]),
            cwd=path,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=spawn_env(),
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=deadline)
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"command timed out after {deadline_ms or _DEFAULT_DEADLINE_MS}ms", 124
        assert proc.returncode is not None
        return stdout.decode(errors="replace"), proc.returncode
