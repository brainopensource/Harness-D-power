"""CLI tests for `sagiha replay` — real-`run_id` replay and `ReplayVerified` emission
(v2-S4 Epic S4.4a).

`_do_replay` is exercised directly (with `RunLoop.run` mocked) rather than through the full
CLI + cassette-digest path — the committed `tests/fixtures/replay_smoke/` pair is a pre-existing
fixture whose digest-matching is unrelated to the `ReplayVerified` wiring under test here (see
`refactor_sagiha_v2_guidelines.md` §2.4's "Known CI trap" note on that fixture).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from sagiha.cli import _do_replay, app
from sagiha.domain.events import ReplayVerified
from sagiha.domain.trajectory import RunRecord
from sagiha.domain.work import GateReport, TaskSpec

runner = CliRunner()


def test_replay_unknown_run_id_fails_cleanly(tmp_path: Path) -> None:
    (tmp_path / "c.json").write_text("[]", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "replay",
            "does-not-exist",
            "--verify",
            "--trajectory-db",
            str(tmp_path / "traj.db"),
            "--cassette",
            str(tmp_path / "c.json"),
            "--workspace",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    assert "No run found" in result.output


class _FakeLoop:
    def __init__(self, run_id: str) -> None:
        self._run_id = run_id

    async def run(self, task, ctx):
        from sagiha.agency.run_loop import RunLoopResult

        return RunLoopResult(task=task, gate_report=GateReport(criteria=()), steps=[], run_id=self._run_id)


@pytest.mark.asyncio
async def test_do_replay_sentinel_never_emits_replay_verified(tmp_path: Path) -> None:
    """The `"verify"` sentinel has no corresponding stored run — `verified_run_id` must stay
    `None` and no `ReplayVerified` event may be emitted against it."""
    (tmp_path / "c.json").write_text("[]", encoding="utf-8")
    emitted: list[object] = []

    class _FakeBus:
        async def emit(self, event: object) -> None:
            emitted.append(event)

    with (
        patch("sagiha.cli.build_kernel") as mock_build_kernel,
        patch("sagiha.cli.RunLoop", side_effect=lambda **kw: _FakeLoop("new-run")),
    ):
        kernel = mock_build_kernel.return_value
        kernel.bus = _FakeBus()
        kernel.trajectory_store.get_run = AsyncMock(return_value=None)
        kernel.governor.max_spend_usd_per_run = 5.0
        kernel.tool_schemas = []

        outcome = await _do_replay(
            run_id="verify",
            cassette=str(tmp_path / "c.json"),
            workspace=str(tmp_path),
            trajectory_db=str(tmp_path / "t.db"),
            tool_cassette=None,
        )

    assert outcome.verified_run_id is None
    assert not any(isinstance(e, ReplayVerified) for e in emitted)


@pytest.mark.asyncio
async def test_do_replay_real_run_id_emits_replay_verified_against_original(tmp_path: Path) -> None:
    """Replaying a real, stored `run_id` must emit `ReplayVerified` tagged with the ORIGINAL
    `run_id` — not the fresh ephemeral run `_do_replay` mints internally to perform the check."""
    (tmp_path / "c.json").write_text("[]", encoding="utf-8")
    emitted: list[object] = []

    class _FakeBus:
        async def emit(self, event: object) -> None:
            emitted.append(event)

    stored_task = TaskSpec(task_id="orig-run", goal="fix it", acceptance=())
    stored_record = RunRecord(run_id="orig-run", task=stored_task, status="completed")

    with (
        patch("sagiha.cli.build_kernel") as mock_build_kernel,
        patch("sagiha.cli.RunLoop", side_effect=lambda **kw: _FakeLoop("ephemeral-run")),
    ):
        kernel = mock_build_kernel.return_value
        kernel.bus = _FakeBus()
        kernel.trajectory_store.get_run = AsyncMock(return_value=stored_record)
        kernel.governor.max_spend_usd_per_run = 5.0
        kernel.tool_schemas = []

        outcome = await _do_replay(
            run_id="orig-run",
            cassette=str(tmp_path / "c.json"),
            workspace=str(tmp_path),
            trajectory_db=str(tmp_path / "t.db"),
            tool_cassette=None,
        )

    assert outcome.verified_run_id == "orig-run"
    replay_events = [e for e in emitted if isinstance(e, ReplayVerified)]
    assert len(replay_events) == 1
    assert replay_events[0].run_id == "orig-run"
    assert replay_events[0].replay_run_id != "orig-run"  # a fresh ephemeral run, not the original
