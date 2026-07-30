"""Built-in coding tools registered at composition — Sprint 3a."""

from __future__ import annotations

from typing import Any, cast

from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.workspace.local import LocalWorkspace, grep_workspace, list_dir_entries
from sagiha.domain.content import EffectClass, TextBlock, ToolResult
from sagiha.domain.work import Edit, EditRequest

READ_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "x-sagiha-path": True},
        "offset": {"type": "integer"},
        "limit": {"type": "integer"},
    },
    "required": ["path"],
}

LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "x-sagiha-path": True},
    },
}

GREP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pattern": {"type": "string"},
        "path": {"type": "string", "x-sagiha-path": True},
    },
    "required": ["pattern"],
}

APPLY_EDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "x-sagiha-path": True},
        "old_string": {"type": "string"},
        "new_string": {"type": "string"},
        "expected_occurrences": {"type": "integer"},
    },
    "required": ["path", "old_string", "new_string"],
}

RUN_COMMAND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "command": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["command"],
}

BUILTIN_SCHEMAS: dict[str, dict[str, Any]] = {
    "read_file": READ_SCHEMA,
    "list_dir": LIST_SCHEMA,
    "grep": GREP_SCHEMA,
    "apply_edit": APPLY_EDIT_SCHEMA,
    "run_command": RUN_COMMAND_SCHEMA,
}


def register_builtin_tools(
    registry: DefaultToolRegistry,
    workspace: LocalWorkspace,
) -> dict[str, dict[str, Any]]:
    """Register the five Sprint 3a tools. Returns schemas for policy path binding."""

    async def read_file(args: dict[str, Any]) -> ToolResult:
        call_id = str(args.get("_call_id", ""))
        path = str(args["path"])
        offset = int(args.get("offset", 0))
        limit = args.get("limit")
        text = await workspace.read(path, offset=offset, limit=int(limit) if limit is not None else None)
        return ToolResult(call_id=call_id, content=[TextBlock(text=text)])

    async def list_dir(args: dict[str, Any]) -> ToolResult:
        call_id = str(args.get("_call_id", ""))
        path = str(args.get("path", "."))
        entries = list_dir_entries(workspace.root, path)
        return ToolResult(call_id=call_id, content=[TextBlock(text=str(entries))])

    async def grep(args: dict[str, Any]) -> ToolResult:
        call_id = str(args.get("_call_id", ""))
        pattern = str(args["pattern"])
        path = str(args.get("path", "."))
        matches = grep_workspace(workspace.root, pattern, path)
        return ToolResult(call_id=call_id, content=[TextBlock(text=str(matches))])

    async def apply_edit(args: dict[str, Any]) -> ToolResult:
        call_id = str(args.get("_call_id", ""))
        path = str(args["path"])
        req = EditRequest(
            path=path,
            edits=(
                Edit(
                    old_string=str(args["old_string"]),
                    new_string=str(args["new_string"]),
                    expected_occurrences=int(args.get("expected_occurrences", 1)),
                ),
            ),
        )
        result = await workspace.apply_edit(req)
        ok = all(h.applied for h in result.hunks)
        return ToolResult(
            call_id=call_id,
            content=[TextBlock(text=result.model_dump_json())],
            is_error=not ok,
        )

    async def run_command(args: dict[str, Any]) -> ToolResult:
        call_id = str(args.get("_call_id", ""))
        command_raw = args.get("command")
        if not isinstance(command_raw, list):
            return ToolResult(
                call_id=call_id,
                content=[TextBlock(text="command must be list[str]")],
                is_error=True,
            )
        argv: list[str] = []
        for item_obj in cast(list[object], command_raw):
            if not isinstance(item_obj, str):
                return ToolResult(
                    call_id=call_id,
                    content=[TextBlock(text="command must be list[str]")],
                    is_error=True,
                )
            argv.append(item_obj)
        result = await workspace.run(argv)
        return ToolResult(
            call_id=call_id,
            content=[TextBlock(text=result.model_dump_json())],
            is_error=result.exit_code != 0,
        )

    specs: list[tuple[str, dict[str, Any], EffectClass, Any]] = [
        ("read_file", READ_SCHEMA, EffectClass.PURE, read_file),
        ("list_dir", LIST_SCHEMA, EffectClass.PURE, list_dir),
        ("grep", GREP_SCHEMA, EffectClass.PURE, grep),
        ("apply_edit", APPLY_EDIT_SCHEMA, EffectClass.IDEMPOTENT, apply_edit),
        ("run_command", RUN_COMMAND_SCHEMA, EffectClass.DESTRUCTIVE, run_command),
    ]

    for name, schema, effect, handler in specs:
        registry.register_handler(name, schema, effect, handler)

    return dict(BUILTIN_SCHEMAS)
