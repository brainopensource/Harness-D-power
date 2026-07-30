"""Unit tests for E0 Harvester."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sagiha.domain.benchmark import BenchmarkSuite, HarvestedTask
from sagiha.e0.harvester import Harvester


@pytest.mark.asyncio
async def test_harvester_inspect_commit(tmp_path: Path) -> None:
    harvester = Harvester(tmp_path)

    git_show_output = (
        "fix(core): resolve null pointer in parser\nsrc/sagiha/parser.py\ntests/unit/test_parser.py\n"
    )

    with patch.object(harvester, "_exec_git", new=AsyncMock(return_value=git_show_output)):
        info = await harvester.inspect_commit("abc123456789")
        assert info["sha"] == "abc123456789"
        assert info["subject"] == "fix(core): resolve null pointer in parser"
        assert "tests/unit/test_parser.py" in info["test_files"]
        assert "src/sagiha/parser.py" in info["source_files"]


@pytest.mark.asyncio
async def test_harvester_create_task(tmp_path: Path) -> None:
    harvester = Harvester(tmp_path)

    async def mock_exec_git(*args: str) -> str:
        if args[0] == "show":
            return "fix bug\nsrc/foo.py\ntests/test_foo.py"
        if args[0] == "rev-parse":
            return "parent_sha_123"
        return ""

    with patch.object(harvester, "_exec_git", side_effect=mock_exec_git):
        task = await harvester.create_task("child_sha_456")
        assert task is not None
        assert isinstance(task, HarvestedTask)
        assert task.base_commit == "parent_sha_123"
        assert task.target_commit == "child_sha_456"
        assert "test_foo.py" in task.failing_test_cmd


def test_harvester_save_and_load_suite(tmp_path: Path) -> None:
    task = HarvestedTask(
        task_id="t1",
        repo="/tmp/repo",
        base_commit="c1",
        target_commit="c2",
        diff_summary="fix bug",
        failing_test_cmd="pytest tests/test_foo.py",
        files_changed=("src/foo.py", "tests/test_foo.py"),
    )
    suite = BenchmarkSuite(suite_id="s1", repo="/tmp/repo", tasks=(task,))

    dest = tmp_path / "suite.json"
    Harvester.save_suite(suite, dest)
    assert dest.exists()

    loaded = Harvester.load_suite(dest)
    assert loaded.suite_id == "s1"
    assert len(loaded.tasks) == 1
    assert loaded.tasks[0].task_id == "t1"
