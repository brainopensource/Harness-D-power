"""Commit-replay harvester — mines fix-commits from repository history (ADR-0015 / E0)."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import anyio

from sagiha.domain.benchmark import BenchmarkSuite, HarvestedTask

logger = logging.getLogger(__name__)


class HarvesterError(RuntimeError):
    """Base exception for harvester operations."""


class Harvester:
    """Walks git history in a repository to discover and validate fix-commit tasks."""

    def __init__(
        self,
        repo_dir: str | Path,
        *,
        test_cmd: str = "pytest",
        max_commits: int = 200,
    ) -> None:
        self._repo_dir = Path(repo_dir).resolve()
        self._test_cmd = test_cmd
        self._max_commits = max_commits

    async def _exec_git(self, *args: str) -> str:
        res = await anyio.run_process(
            ["git", *args],
            cwd=self._repo_dir,
            check=False,
        )
        if res.returncode != 0:
            err_msg = res.stderr.decode("utf-8", errors="replace").strip()
            raise HarvesterError(f"git {' '.join(args)} failed: {err_msg}")
        return res.stdout.decode("utf-8", errors="replace").strip()

    async def get_head_sha(self) -> str:
        return await self._exec_git("rev-parse", "HEAD")

    async def list_recent_commits(self) -> list[str]:
        output = await self._exec_git("log", f"-n{self._max_commits}", "--format=%H")
        return [line.strip() for line in output.splitlines() if line.strip()]

    async def inspect_commit(self, commit_sha: str) -> dict[str, Any]:
        stat_output = await self._exec_git("show", "--stat", "--name-only", "--format=%s", commit_sha)
        lines = stat_output.splitlines()
        subject = lines[0] if lines else ""
        files = [line.strip() for line in lines[1:] if line.strip()]
        test_files = [f for f in files if "test" in f.lower() or f.startswith("tests/")]
        source_files = [
            f
            for f in files
            if f not in test_files and (f.endswith(".py") or f.endswith(".ts") or f.endswith(".js"))
        ]

        return {
            "sha": commit_sha,
            "subject": subject,
            "all_files": tuple(files),
            "test_files": tuple(test_files),
            "source_files": tuple(source_files),
        }

    async def create_task(self, commit_sha: str) -> HarvestedTask | None:
        info = await self.inspect_commit(commit_sha)
        if not info["test_files"] or not info["source_files"]:
            return None

        # Determine parent commit SHA
        try:
            parent_sha = await self._exec_git("rev-parse", f"{commit_sha}~1")
        except HarvesterError:
            return None

        task_id = hashlib.sha256(f"{self._repo_dir.name}:{parent_sha}:{commit_sha}".encode()).hexdigest()[:12]

        return HarvestedTask(
            task_id=task_id,
            repo=str(self._repo_dir),
            base_commit=parent_sha,
            target_commit=commit_sha,
            diff_summary=info["subject"],
            failing_test_cmd=f"{self._test_cmd} {' '.join(info['test_files'])}",
            files_changed=info["all_files"],
        )

    async def harvest_suite(self, suite_id: str = "s0-baseline") -> BenchmarkSuite:
        commits = await self.list_recent_commits()
        tasks: list[HarvestedTask] = []

        for sha in commits:
            try:
                task = await self.create_task(sha)
                if task is not None:
                    tasks.append(task)
            except Exception as exc:
                logger.warning("Failed to harvest commit %s: %s", sha, exc)

        return BenchmarkSuite(
            suite_id=suite_id,
            repo=str(self._repo_dir),
            tasks=tuple(tasks),
        )

    @staticmethod
    def save_suite(suite: BenchmarkSuite, dest_path: str | Path) -> None:
        path = Path(dest_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(suite.model_dump(mode="json"), indent=2))

    @staticmethod
    def load_suite(source_path: str | Path) -> BenchmarkSuite:
        path = Path(source_path)
        data = json.loads(path.read_text())
        return BenchmarkSuite.model_validate(data)
