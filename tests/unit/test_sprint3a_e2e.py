"""Sprint 3a e2e: cassette-driven apply_edit + gate on a fixture workspace."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sagiha.adapters.model.cassette import CassetteEntry, request_digest
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.content import (
    Message,
    ModelRequest,
    TextBlock,
    ToolSchema,
    ToolUseBlock,
)
from sagiha.domain.control import RunContext


def _tool_schemas() -> list[ToolSchema]:
    return [
        ToolSchema(
            name="apply_edit",
            description="edit",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        )
    ]


@pytest.mark.asyncio
async def test_e2e_cassette_fixes_failing_check(tmp_path: Path) -> None:
    # Fixture repo: broken module + failing check until apply_edit runs.
    ws = tmp_path / "fixture"
    ws.mkdir()
    (ws / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")

    system = "You are a careful coding agent. Use tools to fix the failing test."
    goal = "Change VALUE to 2 in mod.py"
    schemas = _tool_schemas()

    resp1 = Message(
        role="assistant",
        content=[
            ToolUseBlock(
                call_id="c-edit",
                tool_name="apply_edit",
                arguments={
                    "path": "mod.py",
                    "old_string": "VALUE = 1",
                    "new_string": "VALUE = 2",
                },
            )
        ],
    )
    resp2 = Message(role="assistant", content=[TextBlock(text="Done.")])

    # For cassette we record the requests the RunLoop will actually send.

    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    traj = tmp_path / "traj.db"

    from collections.abc import AsyncIterator

    from sagiha.domain.trajectory import StreamEvent

    class ScriptedProvider:
        def __init__(self) -> None:
            self.i = 0
            self.recorded: list[tuple[ModelRequest, Message]] = []

        async def complete(self, request: ModelRequest) -> Message:
            responses = [resp1, resp2]
            if self.i >= len(responses):
                return Message(role="assistant", content=[TextBlock(text="stop")])
            msg = responses[self.i]
            self.recorded.append((request, msg))
            self.i += 1
            return msg

        async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError
            yield  # pragma: no cover

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(ws)),
        telemetry=TelemetryConfig(trajectory_db=str(traj)),
    )
    # Build kernel pieces manually with scripted provider, then write cassette from recording.
    kernel = build_kernel(config, cassette_path=str(cassette_path))
    # Override model with scripted for recording pass
    scripted = ScriptedProvider()
    loop = RunLoop(
        model_provider=scripted,  # type: ignore[arg-type]
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        max_steps=5,
        system_prompt=system,
        tool_schemas=schemas,
    )
    ctx = RunContext(
        run_id="e2e-1",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    task = make_task(
        goal,
        checks=["python -c \"from mod import VALUE; assert VALUE == 2\""],
        task_id="e2e-1",
    )
    result = await loop.run(task, ctx)
    assert (ws / "mod.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    assert result.gate_report.admitted is True

    # Persist cassette from recorded requests for digest replay.
    entries = [
        CassetteEntry(
            request=req, response=resp, digest=request_digest(req)
        ).model_dump(mode="json")
        for req, resp in scripted.recorded
    ]
    cassette_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    # Reset fixture and replay via digest cassette.
    (ws / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    kernel2 = build_kernel(config, cassette_path=str(cassette_path))
    loop2 = RunLoop(
        model_provider=kernel2.model_provider,
        policy_engine=kernel2.policy_engine,
        resource_governor=kernel2.resource_governor,
        tool_registry=kernel2.tool_registry,
        trajectory_store=kernel2.trajectory_store,
        bus=kernel2.bus,
        max_steps=5,
        system_prompt=system,
        tool_schemas=schemas,
    )
    ctx2 = RunContext(
        run_id="e2e-2",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    result2 = await loop2.run(task.model_copy(update={"task_id": "e2e-2"}), ctx2)
    assert (ws / "mod.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    assert result2.gate_report.admitted is True
