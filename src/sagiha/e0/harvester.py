"""Commit-replay harvester — mines fix-commits from repository history (ADR-0015 / E0)."""

from __future__ import annotations

import hashlib
import json
import logging
import shlex
import uuid
from pathlib import Path
from typing import Any

import anyio

from sagiha.domain.benchmark import (
    BenchmarkSuite,
    HarvestedTask,
    SuiteValidation,
    TaskValidation,
)

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
            test_files=tuple(info["test_files"]),
            source_files=tuple(info["source_files"]),
        )

    async def validate_task(self, task: HarvestedTask, *, k_determinism: int = 3) -> TaskValidation:
        """The harvester's own honesty gate (`docs/06-guides-and-patterns/benchmark-curation.md`).

        A task is valid iff, in a scratch worktree at `base_commit`:

        1. Applying the fix commit's test-file changes (retaining the new/changed tests, not
           the source fix) makes `failing_test_cmd` reproduce the failure.
        2. That failure is deterministic — rerun `k_determinism` times; any pass among the
           reruns rejects the task as flaky. *Verify flakiness before inclusion, not after.*
        3. Applying the fix commit's source-file changes on top makes `failing_test_cmd` pass —
           the revert is clean and the recorded fix actually resolves what it claims to.
        """
        from sagiha.adapters.workspace.worktree import GitWorktreeManager

        if not task.test_files or not task.source_files:
            return TaskValidation(task_id=task.task_id, passed=False, reason="missing_file_split")

        manager = GitWorktreeManager(str(self._repo_dir))
        branch_id = f"validate-{task.task_id}-{uuid.uuid4().hex[:8]}"
        try:
            workspace = await manager.allocate(task.base_commit, branch_id, run_id=task.task_id)
        except Exception as exc:  # noqa: BLE001 - reported as an honest validation failure, not raised
            return TaskValidation(task_id=task.task_id, passed=False, reason=f"allocate_failed:{exc}")

        try:
            checkout_tests = await workspace.run(
                ["git", "checkout", task.target_commit, "--", *task.test_files]
            )
            if checkout_tests.exit_code != 0:
                return TaskValidation(task_id=task.task_id, passed=False, reason="test_checkout_failed")

            test_argv = shlex.split(task.failing_test_cmd)
            determinism_failures = 0
            for _ in range(max(1, k_determinism)):
                result = await workspace.run(test_argv)
                if result.exit_code != 0:
                    determinism_failures += 1

            if determinism_failures == 0:
                return TaskValidation(
                    task_id=task.task_id,
                    passed=False,
                    reason="failure_did_not_reproduce",
                    determinism_runs=k_determinism,
                    determinism_failures=determinism_failures,
                )
            if determinism_failures != k_determinism:
                return TaskValidation(
                    task_id=task.task_id,
                    passed=False,
                    reason="flaky_failure",
                    determinism_runs=k_determinism,
                    determinism_failures=determinism_failures,
                )

            checkout_source = await workspace.run(
                ["git", "checkout", task.target_commit, "--", *task.source_files]
            )
            if checkout_source.exit_code != 0:
                return TaskValidation(
                    task_id=task.task_id,
                    passed=False,
                    reason="source_checkout_failed",
                    determinism_runs=k_determinism,
                    determinism_failures=determinism_failures,
                )

            fixed_result = await workspace.run(test_argv)
            if fixed_result.exit_code != 0:
                return TaskValidation(
                    task_id=task.task_id,
                    passed=False,
                    reason="fix_did_not_resolve",
                    determinism_runs=k_determinism,
                    determinism_failures=determinism_failures,
                )

            return TaskValidation(
                task_id=task.task_id,
                passed=True,
                determinism_runs=k_determinism,
                determinism_failures=determinism_failures,
            )
        finally:
            await manager.release(branch_id, run_id=task.task_id)

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

    async def validate_suite(
        self,
        suite: BenchmarkSuite,
        *,
        min_tasks: int = 30,
        k_determinism: int = 3,
    ) -> tuple[BenchmarkSuite, SuiteValidation]:
        """Validate every task in `suite`, returning a suite containing only the valid ones.

        The E0 slice gate (`docs/07-roadmap/phased-migration-matrix.md`): "harvester produces
        ≥30 valid tasks; zero tasks whose base commit fails to revert cleanly." `SuiteValidation.passed`
        checks the count; every individual `TaskValidation` in the result records why a task was
        dropped, so a suite that fails the gate is a diagnosable failure, not a silent shrink.
        """
        results: list[TaskValidation] = []
        valid_tasks: list[HarvestedTask] = []
        for task in suite.tasks:
            validation = await self.validate_task(task, k_determinism=k_determinism)
            results.append(validation)
            if validation.passed:
                valid_tasks.append(task.model_copy(update={"validated": True, "validation_reason": None}))

        validated_suite = suite.model_copy(update={"tasks": tuple(valid_tasks)})
        suite_validation = SuiteValidation(
            suite_id=suite.suite_id,
            total_tasks=len(suite.tasks),
            valid_tasks=len(valid_tasks),
            min_tasks_required=min_tasks,
            task_results=tuple(results),
        )
        return validated_suite, suite_validation

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
