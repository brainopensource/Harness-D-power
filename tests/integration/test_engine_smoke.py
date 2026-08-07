"""M1a walking-skeleton smoke test (Sprint 2, Checkpoint 3): one wired
end-to-end run through `engine.run()` against `workflows/linear_v1.yaml` —
retrieve -> generate -> apply -> evaluate, all four real adapters, over a
respx-mocked model endpoint (no live dependency). Asserts the run completes,
produces a coherent tri-state `GateReport` (any status is an acceptable
*result* per ADR-0002), and that events landed in the `TrajectoryStore`."""

from __future__ import annotations

import json
import subprocess
import sys

import httpx
import pytest
import respx

from aether import engine
from aether.domain.gate import GateStatus
from aether.domain.task import Task, TaskSource
from aether.measurement.evaluator import hash_command

WORKFLOWS_ROOT = "workflows"
MODEL_BASE_URL = "http://localhost:11434/v1"


def _git(*args: str, cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _sse(*chunks: dict[str, object]) -> bytes:
    body = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks)
    return (body + "data: [DONE]\n\n").encode()


@pytest.fixture
def fixture_repo(tmp_path):  # noqa: ANN001
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=str(repo))
    _git("config", "user.email", "test@example.com", cwd=str(repo))
    _git("config", "user.name", "Test", cwd=str(repo))
    (repo / "README.md").write_text("# Fixture repo\n\nA tiny repo for the M1a smoke test.\n")
    _git("add", ".", cwd=str(repo))
    _git("commit", "-q", "-m", "init", cwd=str(repo))
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), check=True, capture_output=True, text=True
    ).stdout.strip()
    return str(repo), base_commit


async def test_engine_run_completes_end_to_end_and_produces_a_gate_report(fixture_repo, tmp_path) -> None:  # noqa: ANN001
    repo_path, base_commit = fixture_repo
    worktrees_root = str(tmp_path / "worktrees")
    trajectory_db = str(tmp_path / "trajectory.db")

    test_command = f"{sys.executable} -c \"import sys; sys.exit(0)\""

    task = Task(
        task_id="smoke-task-1",  # type: ignore[arg-type]
        repo=repo_path,
        base_commit=base_commit,
        instructions="Add a docstring to the module.",
        environment_image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command(test_command),
        source=TaskSource(manifest_hash="sha256:" + "b" * 64, instance_id="smoke-1"),
    )

    with respx.mock:
        respx.post(f"{MODEL_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200,
                content=_sse(
                    {"choices": [{"delta": {"content": "diff --git a/x b/x\n"}, "finish_reason": None}]},
                    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                ),
            )
        )

        result = await engine.run(
            task,
            repo_path=repo_path,
            worktrees_root=worktrees_root,
            topology_path=f"{WORKFLOWS_ROOT}/linear_v1.yaml",
            resolve_command=lambda spec: test_command,
            model_base_url=MODEL_BASE_URL,
            model_name="qwen2.5-coder-32b",
            trajectory_db_path=trajectory_db,
            entry_file="README.md",
        )

    assert result.gate_report.status in {GateStatus.PASSED, GateStatus.FAILED, GateStatus.NONE}

    from aether.adapters.trajectory_store.sqlite import SqliteTrajectoryStore

    store = SqliteTrajectoryStore(trajectory_db)
    events = [event async for event in store.replay(result.run_id)]
    event_types = [e.event_type for e in events]

    assert "run_started" in event_types
    assert "run_completed" in event_types
    assert event_types.count("node_started") == 4
    assert event_types.count("node_completed") == 4


async def test_engine_run_evaluate_gate_report_is_passed_when_command_exits_zero(  # noqa: ANN001
    fixture_repo, tmp_path
) -> None:
    repo_path, base_commit = fixture_repo
    worktrees_root = str(tmp_path / "worktrees")

    test_command = f"{sys.executable} -c \"import sys; sys.exit(0)\""
    task = Task(
        task_id="smoke-task-2",  # type: ignore[arg-type]
        repo=repo_path,
        base_commit=base_commit,
        instructions="No-op change.",
        environment_image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command(test_command),
        source=TaskSource(manifest_hash="sha256:" + "b" * 64, instance_id="smoke-2"),
    )

    with respx.mock:
        respx.post(f"{MODEL_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200, content=_sse({"choices": [{"delta": {}, "finish_reason": "stop"}]})
            )
        )

        result = await engine.run(
            task,
            repo_path=repo_path,
            worktrees_root=worktrees_root,
            topology_path=f"{WORKFLOWS_ROOT}/linear_v1.yaml",
            resolve_command=lambda spec: test_command,
            model_base_url=MODEL_BASE_URL,
            trajectory_db_path=str(tmp_path / "trajectory2.db"),
            entry_file="README.md",
        )

    assert result.gate_report.status == GateStatus.PASSED
