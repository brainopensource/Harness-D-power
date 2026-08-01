"""Built-in coding tools registered at composition — Sprint 3a."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, cast

from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.workspace.local import grep_workspace, list_dir_entries
from sagiha.domain.content import EffectClass, TextBlock, ToolResult
from sagiha.domain.work import Edit, EditRequest
from sagiha.ports.code_graph import CodeGraph
from sagiha.ports.indexer import Indexer
from sagiha.ports.workspace import Workspace


class _WorkspaceWithRoot(Protocol):
    """Concrete adapters expose `.root` for list_dir/grep helpers (not on the Workspace port)."""

    @property
    def root(self) -> Path: ...

    async def read(self, path: str, offset: int = 0, limit: int | None = None) -> str: ...

    async def write(self, path: str, content: str) -> None: ...

    async def apply_edit(self, request: EditRequest) -> object: ...

    async def run(self, command: list[str]) -> object: ...


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

WRITE_FILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "x-sagiha-path": True},
        "content": {"type": "string"},
    },
    "required": ["path", "content"],
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

FIND_SYMBOLS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "limit": {"type": "integer"},
    },
    "required": ["query"],
}

GET_SKELETON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "x-sagiha-path": True},
    },
    "required": ["path"],
}

IMPACTED_BY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "x-sagiha-path": True},
        "hops": {"type": "integer"},
    },
    "required": ["path"],
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "read_file": "Read a text file from the workspace",
    "list_dir": "List directory entries",
    "grep": "Search file contents by regex",
    "apply_edit": "Apply a search/replace edit to a file",
    "write_file": "Write content to a file, creating it (and parent directories) if necessary",
    "run_command": "Run a command in the workspace",
    "find_symbols": "Search indexed symbols by name",
    "get_skeleton": "Return signatures and structure for a file",
    "impacted_by": "List files impacted by changes to a path via the code graph",
}

BUILTIN_SCHEMAS: dict[str, dict[str, Any]] = {
    "read_file": READ_SCHEMA,
    "list_dir": LIST_SCHEMA,
    "grep": GREP_SCHEMA,
    "apply_edit": APPLY_EDIT_SCHEMA,
    "write_file": WRITE_FILE_SCHEMA,
    "run_command": RUN_COMMAND_SCHEMA,
}


def register_builtin_tools(
    registry: DefaultToolRegistry,
    workspace: Workspace,
    *,
    indexer: Indexer | None = None,
    code_graph: CodeGraph | None = None,
) -> dict[str, dict[str, Any]]:
    """Register built-in tools. Code-intel tools register only when indexer/graph are provided."""
    # list_dir / grep need a host path; both LocalWorkspace and ContainerSandbox expose `.root`.
    rooted: _WorkspaceWithRoot = workspace  # type: ignore[assignment]

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
        entries = list_dir_entries(rooted.root, path)
        payload = json.dumps([e.model_dump() for e in entries])
        return ToolResult(call_id=call_id, content=[TextBlock(text=payload)])

    async def grep(args: dict[str, Any]) -> ToolResult:
        call_id = str(args.get("_call_id", ""))
        pattern = str(args["pattern"])
        path = str(args.get("path", "."))
        matches = grep_workspace(rooted.root, pattern, path)
        payload = json.dumps([m.model_dump() for m in matches])
        return ToolResult(call_id=call_id, content=[TextBlock(text=payload)])

    async def write_file(args: dict[str, Any]) -> ToolResult:
        call_id = str(args.get("_call_id", ""))
        path = str(args["path"])
        content = str(args["content"])
        await workspace.write(path, content)
        return ToolResult(call_id=call_id, content=[TextBlock(text=f"wrote {path}")])

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

    # T7 trust column. `False` means "this output surfaces content the harness did not
    # author, so it may be attacker-controlled" — a repo file, a grep hit, a subprocess's
    # stdout. `True` means the payload is harness-derived: `apply_edit` and `write_file`
    # return an `EditResult` the workspace adapter itself constructed, describing an effect
    # the harness performed. Note the asymmetry is about the *result*, not the tool's power:
    # the mutating tools are the trusted-output ones precisely because they report on
    # themselves rather than relaying foreign bytes.
    specs: list[tuple[str, dict[str, Any], EffectClass, Any, bool]] = [
        ("read_file", READ_SCHEMA, EffectClass.PURE, read_file, False),
        ("list_dir", LIST_SCHEMA, EffectClass.PURE, list_dir, False),
        ("grep", GREP_SCHEMA, EffectClass.PURE, grep, False),
        ("apply_edit", APPLY_EDIT_SCHEMA, EffectClass.DESTRUCTIVE, apply_edit, True),
        ("write_file", WRITE_FILE_SCHEMA, EffectClass.DESTRUCTIVE, write_file, True),
        ("run_command", RUN_COMMAND_SCHEMA, EffectClass.DESTRUCTIVE, run_command, False),
    ]

    for name, schema, effect, handler, trusted in specs:
        registry.register_handler(name, schema, effect, handler, trusted_output=trusted)

    schemas: dict[str, dict[str, Any]] = dict(BUILTIN_SCHEMAS)

    if indexer is not None and code_graph is not None:

        async def find_symbols(args: dict[str, Any]) -> ToolResult:
            call_id = str(args.get("_call_id", ""))
            query = str(args["query"])
            limit = int(args.get("limit", 20))
            symbols = await indexer.find_symbols(query, limit=limit)
            payload = json.dumps([s.model_dump() for s in symbols])
            return ToolResult(call_id=call_id, content=[TextBlock(text=payload)])

        async def get_skeleton(args: dict[str, Any]) -> ToolResult:
            call_id = str(args.get("_call_id", ""))
            path = str(args["path"])
            skeleton = await indexer.get_skeleton(path)
            return ToolResult(call_id=call_id, content=[TextBlock(text=skeleton)])

        async def impacted_by(args: dict[str, Any]) -> ToolResult:
            call_id = str(args.get("_call_id", ""))
            path = str(args["path"])
            hops = int(args.get("hops", 2))
            impacted = await code_graph.impacted_by(path, hops=hops)
            payload = json.dumps(impacted)
            return ToolResult(call_id=call_id, content=[TextBlock(text=payload)])

        code_intel_specs: list[tuple[str, dict[str, Any], EffectClass, Any, bool]] = [
            ("find_symbols", FIND_SYMBOLS_SCHEMA, EffectClass.PURE, find_symbols, True),
            ("get_skeleton", GET_SKELETON_SCHEMA, EffectClass.PURE, get_skeleton, True),
            ("impacted_by", IMPACTED_BY_SCHEMA, EffectClass.PURE, impacted_by, True),
        ]
        for name, schema, effect, handler, trusted in code_intel_specs:
            registry.register_handler(name, schema, effect, handler, trusted_output=trusted)
            schemas[name] = schema

    return schemas
