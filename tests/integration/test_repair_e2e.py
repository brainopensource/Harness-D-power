"""The repair edge end to end through `engine.run()` (TASK-023).

`tests/aether/workflow/test_repair.py` pins the routing and the bounds with
scripted steps. This one runs the real thing: a real git worktree, the real
`Workspace` adapter applying a real unified diff, the real `RealEvaluator`
running a real test command, and a model that fails on the first attempt and
succeeds on the repair — the exact sequence `vision.md` §2 says is the largest
lever on score.

The model endpoint is respx-mocked, so this is deterministic and offline; every
other component is the production one.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
import respx

from aether import engine
from aether.adapters.trajectory_store.sqlite import SqliteTrajectoryStore
from aether.domain.gate import GateStatus
from aether.domain.task import Task, TaskSource
from aether.measurement.evaluator import hash_command

MODEL_BASE_URL = "http://localhost:11434/v1"
BROKEN_CALC = "def add(a, b):\n    return a - b\n"
FIXED_CALC = "def add(a, b):\n    return a + b\n"
RUN_TESTS = "import sys\nfrom calc import add\nsys.exit(0 if add(1, 2) == 3 else 1)\n"


def _git(*args: str, cwd: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _sse(text: str = "") -> bytes:
    chunks: list[dict[str, object]] = []
    if text:
        chunks.append({"choices": [{"delta": {"content": text}, "finish_reason": None}]})
    chunks.append({"choices": [{"delta": {}, "finish_reason": "stop"}]})
    body = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks)
    return (body + "data: [DONE]\n\n").encode()


@pytest.fixture
def failing_repo(tmp_path: Path):  # noqa: ANN201
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=str(repo))
    _git("config", "user.email", "test@example.com", cwd=str(repo))
    _git("config", "user.name", "Test", cwd=str(repo))
    (repo / "calc.py").write_text(BROKEN_CALC)
    (repo / "run_tests.py").write_text(RUN_TESTS)
    (repo / "README.md").write_text("# calc\n")
    _git("add", ".", cwd=str(repo))
    _git("commit", "-q", "-m", "base", cwd=str(repo))
    base_commit = _git("rev-parse", "HEAD", cwd=str(repo)).strip()

    (repo / "calc.py").write_text(FIXED_CALC)
    fixing_diff = _git("diff", cwd=str(repo))
    _git("checkout", "--", "calc.py", cwd=str(repo))

    return str(repo), base_commit, fixing_diff


async def test_a_failed_candidate_is_repaired_and_passes(failing_repo, tmp_path) -> None:  # noqa: ANN001
    repo_path, base_commit, fixing_diff = failing_repo
    test_command = f"{sys.executable} run_tests.py"
    trajectory_db = str(tmp_path / "trajectory.db")

    task = Task(
        task_id="repair-e2e-1",  # type: ignore[arg-type]
        repo=repo_path,
        base_commit=base_commit,
        instructions="add(1, 2) must return 3.",
        environment_image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command(test_command),
        source=TaskSource(manifest_hash="sha256:" + "b" * 64, instance_id="repair-e2e-1"),
    )

    # First completion: a patch that does not fix anything. Second: the fix.
    # That is the whole point of the edge — the first attempt is allowed to be
    # wrong, and the loop is what turns a FAILED into a PASSED.
    responses = [
        httpx.Response(200, content=_sse("")),
        httpx.Response(200, content=_sse(fixing_diff)),
    ]

    with respx.mock:
        respx.post(f"{MODEL_BASE_URL}/chat/completions").mock(side_effect=responses)

        result = await engine.run(
            task,
            repo_path=repo_path,
            worktrees_root=str(tmp_path / "worktrees"),
            topology_path="workflows/linear_repair_v1.yaml",
            resolve_command=lambda spec: test_command,
            model_base_url=MODEL_BASE_URL,
            trajectory_db_path=trajectory_db,
            entry_file="README.md",
        )

    assert result.gate_report.status is GateStatus.PASSED

    store = SqliteTrajectoryStore(trajectory_db)
    kinds = [event.event_type async for event in store.replay(result.run_id)]
    assert kinds.count("repair_iteration_started") == 1
    # retrieve, generate, apply, evaluate, then repair, apply, evaluate.
    assert kinds.count("node_started") == 7


async def test_a_candidate_that_never_passes_stops_at_the_bound(failing_repo, tmp_path) -> None:  # noqa: ANN001
    """The un-repairable case: three iterations, then the run ends with the
    honest FAILED rather than looping."""
    repo_path, base_commit, _fixing_diff = failing_repo
    test_command = f"{sys.executable} run_tests.py"
    trajectory_db = str(tmp_path / "trajectory.db")

    task = Task(
        task_id="repair-e2e-2",  # type: ignore[arg-type]
        repo=repo_path,
        base_commit=base_commit,
        instructions="add(1, 2) must return 3.",
        environment_image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command(test_command),
        source=TaskSource(manifest_hash="sha256:" + "b" * 64, instance_id="repair-e2e-2"),
    )

    with respx.mock:
        respx.post(f"{MODEL_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, content=_sse(""))
        )

        result = await engine.run(
            task,
            repo_path=repo_path,
            worktrees_root=str(tmp_path / "worktrees"),
            topology_path="workflows/linear_repair_v1.yaml",
            resolve_command=lambda spec: test_command,
            model_base_url=MODEL_BASE_URL,
            trajectory_db_path=trajectory_db,
            entry_file="README.md",
        )

    assert result.gate_report.status is GateStatus.FAILED

    store = SqliteTrajectoryStore(trajectory_db)
    kinds = [event.event_type async for event in store.replay(result.run_id)]
    assert kinds.count("repair_iteration_started") == 3  # linear_repair_v1's bound


async def test_an_instrument_error_ends_the_run_without_repairing(failing_repo, tmp_path) -> None:  # noqa: ANN001
    """A `test_command_hash` mismatch is a NONE. The repair edge must not
    burn three iterations trying to fix our own instrument."""
    repo_path, base_commit, _diff = failing_repo
    trajectory_db = str(tmp_path / "trajectory.db")

    task = Task(
        task_id="repair-e2e-3",  # type: ignore[arg-type]
        repo=repo_path,
        base_commit=base_commit,
        instructions="add(1, 2) must return 3.",
        environment_image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command("a command the resolver will not produce"),
        source=TaskSource(manifest_hash="sha256:" + "b" * 64, instance_id="repair-e2e-3"),
    )

    with respx.mock:
        respx.post(f"{MODEL_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, content=_sse(""))
        )

        result = await engine.run(
            task,
            repo_path=repo_path,
            worktrees_root=str(tmp_path / "worktrees"),
            topology_path="workflows/linear_repair_v1.yaml",
            resolve_command=lambda spec: f"{sys.executable} run_tests.py",
            model_base_url=MODEL_BASE_URL,
            trajectory_db_path=trajectory_db,
            entry_file="README.md",
        )

    assert result.gate_report.status is GateStatus.NONE

    store = SqliteTrajectoryStore(trajectory_db)
    kinds = [event.event_type async for event in store.replay(result.run_id)]
    assert kinds.count("repair_iteration_started") == 0
