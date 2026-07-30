"""D9: `sagiha run --resume` — CLI-layer argument handling and a full resume round trip."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sagiha.cli import _run_or_resume, app

runner = CliRunner()


def test_run_without_goal_or_resume_fails_cleanly() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    assert "goal is required" in result.output


def test_run_resume_of_unknown_run_id_fails_cleanly(tmp_path: Path) -> None:
    (tmp_path / "c.json").write_text("[]", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            "--resume",
            "does-not-exist",
            "--trajectory-db",
            str(tmp_path / "traj.db"),
            "--cassette",
            str(tmp_path / "c.json"),
        ],
    )
    assert result.exit_code == 1
    assert "No run found" in result.output


@pytest.mark.asyncio
async def test_run_or_resume_round_trip(tmp_path: Path) -> None:
    """Drives the CLI's own async helper directly (not through Typer arg parsing, which is
    covered above) for a full interrupted-then-resumed run, since a real two-step cassette
    round trip needs a scripted provider swapped in — the same technique
    scripts/gen_replay_fixture.py uses to generate the committed replay fixture."""
    from sagiha.adapters.model.cassette import CassetteEntry, request_digest
    from sagiha.composition import build_kernel
    from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
    from sagiha.domain.content import Message, ModelRequest, TextBlock, ToolUseBlock
    from sagiha.domain.trajectory import StreamEvent

    workspace = tmp_path / "ws"
    workspace.mkdir()
    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    trajectory_db = tmp_path / "traj.db"

    class _Scripted:
        def __init__(self, responses: list[Message]) -> None:
            self._responses = responses
            self.i = 0
            self.recorded: list[tuple[ModelRequest, Message]] = []

        async def complete(self, request: ModelRequest) -> Message:
            msg = self._responses[self.i]
            self.i += 1
            self.recorded.append((request, msg))
            return msg

        async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError
            yield  # pragma: no cover

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(workspace)),
        telemetry=TelemetryConfig(trajectory_db=str(trajectory_db)),
    )

    # Phase 1: interrupted after one tool_use step (max_steps=1 caps it mid-flight).
    kernel1 = build_kernel(config, cassette_path=str(cassette_path))
    scripted1 = _Scripted(
        [
            Message(
                role="assistant",
                content=[
                    ToolUseBlock(call_id="c1", tool_name="run_command", arguments={"command": ["true"]})
                ],
            )
        ]
    )
    from sagiha.agency.run_loop import RunLoop, make_task
    from sagiha.domain.control import RunContext

    loop1 = RunLoop(
        model_provider=scripted1,  # type: ignore[arg-type]
        policy_engine=kernel1.policy_engine,
        resource_governor=kernel1.resource_governor,
        tool_registry=kernel1.tool_registry,
        trajectory_store=kernel1.trajectory_store,
        bus=kernel1.bus,
        max_steps=1,
        tool_schemas=list(kernel1.tool_schemas),
        evaluator=kernel1.evaluator,
    )
    run_id = "cli-resume-1"
    task = make_task("run true", checks=[], task_id=run_id)
    ctx1 = RunContext(
        run_id=run_id, autonomy_level="interactive", workspace_root=str(workspace), budget_remaining_usd=10.0
    )
    phase1_result = await loop1.run(task, ctx1)
    assert len(phase1_result.steps) == 1

    # Phase 2: what the resumed request will look like — reconstructed history plus an
    # end-turn response. Record it into the cassette so replay mode can serve it.
    loop2_for_digest = RunLoop(
        model_provider=scripted1,  # unused for digest computation
        policy_engine=kernel1.policy_engine,
        resource_governor=kernel1.resource_governor,
        tool_registry=kernel1.tool_registry,
        trajectory_store=kernel1.trajectory_store,
        bus=kernel1.bus,
        tool_schemas=list(kernel1.tool_schemas),
        evaluator=kernel1.evaluator,
    )
    reconstructed = loop2_for_digest._reconstruct_history(task, phase1_result.steps)
    resumed_request = ModelRequest(
        system=loop2_for_digest._system_prompt,
        messages=reconstructed,
        tools=list(kernel1.tool_schemas),
        role="execution",
    )
    end_turn = Message(role="assistant", content=[TextBlock(text="All done.")])
    entries = [
        CassetteEntry(
            request=resumed_request, response=end_turn, digest=request_digest(resumed_request)
        ).model_dump(mode="json")
    ]
    cassette_path.write_text(json.dumps(entries), encoding="utf-8")

    # Phase 3: resume through the CLI's own async entry point, now in replay mode with the
    # cassette containing exactly the continuation request.
    outcome, payload = await _run_or_resume(
        goal=None,
        checks=[],
        workspace=str(workspace),
        cassette_path=str(cassette_path),
        max_steps=5,
        trajectory_db=str(trajectory_db),
        resume=run_id,
    )
    assert outcome == "ok"
    from sagiha.agency.run_loop import RunLoopResult

    assert isinstance(payload, RunLoopResult)
    assert payload.run_id == run_id
    assert len(payload.steps) == 1  # step 1 folded back in; step 2 ended the turn (no tool call)

    from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore

    store = SQLiteTrajectoryStore(db_path=str(trajectory_db))
    all_steps = await store.steps_for_run(run_id)
    assert [s.step_id.seq for s in all_steps] == [1]  # no seq collision on resume
    final_record = await store.get_run(run_id)
    assert final_record is not None
    assert final_record.status == "completed"
