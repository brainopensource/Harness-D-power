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


def _git_init(repo: Path) -> None:
    """Make `repo` a git repository with one commit, so the gates have a base ref."""
    import subprocess

    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)

    run("init", "-q")
    run("config", "user.email", "test@example.com")
    run("config", "user.name", "Test")
    run("add", "-A")
    run("commit", "-q", "-m", "base")


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
    # The coding gates diff against a base commit (H1 fix, PR-1a). Before that fix they
    # were hardcoded True and this fixture never needed to be a real repo; now an
    # ungitted workspace correctly yields None gates and refuses to admit.
    _git_init(ws)

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

    from sagiha.domain.trajectory import Completion, StreamEvent, TokenUsage

    class ScriptedProvider:
        def __init__(self) -> None:
            self.i = 0
            self.recorded: list[tuple[ModelRequest, Message]] = []

        async def complete(self, request: ModelRequest) -> Completion:
            responses = [resp1, resp2]
            if self.i >= len(responses):
                return Completion(
                    message=Message(role="assistant", content=[TextBlock(text="stop")]),
                    usage=TokenUsage(input_tokens=0, output_tokens=0),
                    model="test",
                )
            msg = responses[self.i]
            self.recorded.append((request, msg))
            self.i += 1
            return Completion(message=msg, usage=TokenUsage(input_tokens=0, output_tokens=0), model="test")

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
        evaluator=kernel.evaluator,
        max_steps=5,
        system_prompt=system,
        tool_schemas=schemas,
        workspace=kernel.workspace,
    )
    ctx = RunContext(
        run_id="e2e-1",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    task = make_task(
        goal,
        checks=['python -c "from mod import VALUE; assert VALUE == 2"'],
        task_id="e2e-1",
    )
    result = await loop.run(task, ctx)
    assert (ws / "mod.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    assert result.gate_report.admitted is True

    # Persist cassette from recorded requests for digest replay.
    entries = [
        CassetteEntry(request=req, response=resp, digest=request_digest(req)).model_dump(mode="json")
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
        evaluator=kernel2.evaluator,
        max_steps=5,
        system_prompt=system,
        tool_schemas=schemas,
        workspace=kernel.workspace,
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


@pytest.mark.asyncio
async def test_e2e_editing_tests_fails_unmodified_gate(tmp_path: Path) -> None:
    ws = tmp_path / "fixture"
    ws.mkdir()
    tests_dir = ws / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_mod.py").write_text("def test_one(): assert 1 == 1\n", encoding="utf-8")
    _git_init(ws)

    # Edit a test file
    (tests_dir / "test_mod.py").write_text("def test_one(): assert 1 == 2\n", encoding="utf-8")

    system = "You are a careful coding agent."
    goal = "Modify test"
    schemas = _tool_schemas()

    resp = Message(role="assistant", content=[TextBlock(text="Done.")])
    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    traj = tmp_path / "traj.db"

    from sagiha.domain.trajectory import Completion, TokenUsage

    class ScriptedProvider:
        async def complete(self, request: ModelRequest) -> Completion:
            return Completion(message=resp, usage=TokenUsage(input_tokens=0, output_tokens=0), model="test")

        async def stream(self, request: ModelRequest):
            raise NotImplementedError
            yield

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(ws)),
        telemetry=TelemetryConfig(trajectory_db=str(traj)),
    )
    kernel = build_kernel(config, cassette_path=str(cassette_path))
    loop = RunLoop(
        model_provider=ScriptedProvider(),
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        evaluator=kernel.evaluator,
        max_steps=5,
        system_prompt=system,
        tool_schemas=schemas,
        workspace=kernel.workspace,
    )
    ctx = RunContext(
        run_id="e2e-unmod-1",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    task = make_task(goal, checks=['python -c "assert True"'], task_id="e2e-unmod-1")
    result = await loop.run(task, ctx)
    assert result.gate_report.tests_unmodified is False
    assert result.gate_report.admitted is False


@pytest.mark.asyncio
async def test_e2e_oversized_diff_fails_bounds_gate(tmp_path: Path) -> None:
    ws = tmp_path / "fixture"
    ws.mkdir()
    (ws / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git_init(ws)

    # Make a diff exceeding default max_diff_lines (1000)
    large_content = "\n".join(f"X_{i} = {i}" for i in range(1200)) + "\n"
    (ws / "mod.py").write_text(large_content, encoding="utf-8")

    system = "You are a careful coding agent."
    goal = "Large edit"
    schemas = _tool_schemas()

    resp = Message(role="assistant", content=[TextBlock(text="Done.")])
    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    traj = tmp_path / "traj.db"

    from sagiha.domain.trajectory import Completion, TokenUsage

    class ScriptedProvider:
        async def complete(self, request: ModelRequest) -> Completion:
            return Completion(message=resp, usage=TokenUsage(input_tokens=0, output_tokens=0), model="test")

        async def stream(self, request: ModelRequest):
            raise NotImplementedError
            yield

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(ws)),
        telemetry=TelemetryConfig(trajectory_db=str(traj)),
    )
    kernel = build_kernel(config, cassette_path=str(cassette_path))
    loop = RunLoop(
        model_provider=ScriptedProvider(),
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        evaluator=kernel.evaluator,
        max_steps=5,
        system_prompt=system,
        tool_schemas=schemas,
        workspace=kernel.workspace,
    )
    ctx = RunContext(
        run_id="e2e-bounds-1",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    task = make_task(goal, checks=['python -c "assert True"'], task_id="e2e-bounds-1")
    result = await loop.run(task, ctx)
    assert result.gate_report.diff_within_bounds is False
    assert result.gate_report.admitted is False


@pytest.mark.asyncio
async def test_e2e_adding_suppression_fails_suppressions_gate(tmp_path: Path) -> None:
    ws = tmp_path / "fixture"
    ws.mkdir()
    (ws / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git_init(ws)

    # Add suppression marker
    (ws / "mod.py").write_text("VALUE = 1  # type: ignore\n", encoding="utf-8")

    system = "You are a careful coding agent."
    goal = "Add suppression"
    schemas = _tool_schemas()

    resp = Message(role="assistant", content=[TextBlock(text="Done.")])
    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    traj = tmp_path / "traj.db"

    from sagiha.domain.trajectory import Completion, TokenUsage

    class ScriptedProvider:
        async def complete(self, request: ModelRequest) -> Completion:
            return Completion(message=resp, usage=TokenUsage(input_tokens=0, output_tokens=0), model="test")

        async def stream(self, request: ModelRequest):
            raise NotImplementedError
            yield

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(ws)),
        telemetry=TelemetryConfig(trajectory_db=str(traj)),
    )
    kernel = build_kernel(config, cassette_path=str(cassette_path))
    loop = RunLoop(
        model_provider=ScriptedProvider(),
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        evaluator=kernel.evaluator,
        max_steps=5,
        system_prompt=system,
        tool_schemas=schemas,
        workspace=kernel.workspace,
    )
    ctx = RunContext(
        run_id="e2e-suppress-1",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    task = make_task(goal, checks=['python -c "assert True"'], task_id="e2e-suppress-1")
    result = await loop.run(task, ctx)
    assert result.gate_report.no_new_suppressions is False
    assert result.gate_report.admitted is False
