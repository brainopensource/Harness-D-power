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


#: Exit codes that mean *the test command never ran*, as distinct from "the tests failed".
#: 127 = command not found, 126 = found but not executable, and pytest's own 4 = usage error /
#: 5 = no tests collected. Treating any of these as a reproduced failure is the H-series
#: fabrication in its purest form: the harvester would certify a task whose "failing test"
#: fails because `pytest` is not on PATH in the scratch worktree, and no source fix could ever
#: make it pass. That is precisely how a suite of zero real tasks can look like a suite.
_INFRASTRUCTURE_EXIT_CODES: frozenset[int] = frozenset({126, 127, 4, 5})

#: Stderr fingerprints of "the runner itself is missing", which exit with a plain `1` and are
#: therefore indistinguishable from a failing test by exit code alone. `python -m pytest` under
#: an interpreter without pytest installed prints exactly this and exits 1 — the subtler twin of
#: the 127 case, and the one that survived the first fix.
_INFRASTRUCTURE_STDERR_MARKERS: tuple[str, ...] = (
    "No module named pytest",
    "No module named 'pytest'",
    "command not found",
)


def default_test_command(repo_dir: Path, *, source_dir: str = "src") -> str:
    """The test command for a task, run inside a scratch worktree.

    Two things this must get right, both of which were silently wrong before:

    1. **A concrete interpreter, not a bare `pytest`/`python`.** A scratch worktree inherits the
       caller's `PATH`, where `python` is usually the *system* interpreter with no pytest in it.
       Both failure modes (127 from a missing console script, exit 1 from a missing module) look
       like a failing test to a validator that only reads exit codes.

    2. **`PYTHONPATH=<source_dir>` so the worktree's own source wins.** This is the load-bearing
       one. The venv materialized into the worktree contains an *editable* install of this
       package, whose `.pth` points at the main checkout's `src/`. Without an override,
       `import sagiha` inside a worktree at commit X resolves to whatever is in the developer's
       working tree *right now* — so the harvester validated tasks against current `src/`
       rather than against the task's baseline, and `BenchmarkRunner` measured the same. Worse,
       Best-of-N candidates each edit their own worktree while every candidate's tests import
       one shared source tree, which would make candidate diffs invisible to the gates scoring
       them. `PYTHONPATH` is relative here and the command runs with the worktree as cwd, so it
       resolves per-worktree; it is embedded in `failing_test_cmd` so the recorded task carries
       its own isolation rather than depending on the runner remembering to add it.
    """
    venv_python = repo_dir / ".venv" / "bin" / "python"
    interpreter = str(venv_python) if venv_python.exists() else "python3"
    # `env` rather than a shell string: `workspace.run` takes argv and never spawns a shell.
    return f"env PYTHONPATH={source_dir} {interpreter} -m pytest"


def _is_infrastructure_failure(exit_code: int, stderr: str) -> bool:
    """Did the test command fail to *run*, as opposed to running and reporting failures?"""
    if exit_code in _INFRASTRUCTURE_EXIT_CODES:
        return True
    return any(marker in stderr for marker in _INFRASTRUCTURE_STDERR_MARKERS)


def is_test_file(path: str) -> bool:
    """Is `path` a file pytest would actually collect as a test module?

    Pytest's own default collection rule (`test_*.py` / `*_test.py`), deliberately — the
    previous predicate was `"test" in path.lower() or path.startswith("tests/")`, which
    swept in every fixture and data file living under `tests/`. That put paths like
    `tests/fixtures/replay_smoke/cassette.json` and `tests/fixtures/.../.gitkeep` into
    `failing_test_cmd`, so the harvested command was `pytest <a JSON file>` — which pytest
    exits non-zero on for the wrong reason. Validation then "confirmed" a failing test that
    was really a collection error, and the fix commit could never make it pass: every task
    harvested from a commit touching test fixtures was silently unusable.
    """
    name = path.rsplit("/", 1)[-1]
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


class Harvester:
    """Walks git history in a repository to discover and validate fix-commit tasks."""

    def __init__(
        self,
        repo_dir: str | Path,
        *,
        test_cmd: str | None = None,
        max_commits: int = 200,
    ) -> None:
        self._repo_dir = Path(repo_dir).resolve()
        #: `None` means "resolve a real interpreter for this repo" — see `default_test_command`.
        self._test_cmd = test_cmd or default_test_command(self._repo_dir)
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
        test_files = [f for f in files if is_test_file(f)]
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
            # Without this the worktree has no `.venv`, so a bare `pytest` exits 127 and every
            # stage below misreads "could not run" as "the test failed". `materialize` is what
            # symlinks the interpreter/toolchain in — allocating without it produced a
            # 0-valid-task suite whose rejections all pointed at the wrong cause.
            await manager.materialize(branch_id)
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
                # A command that could not execute is not evidence about the task. Reject the
                # task loudly rather than counting it as a reproduced failure.
                if _is_infrastructure_failure(result.exit_code, result.stderr):
                    return TaskValidation(
                        task_id=task.task_id,
                        passed=False,
                        reason=f"test_command_not_runnable:exit_{result.exit_code}",
                    )
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
            if _is_infrastructure_failure(fixed_result.exit_code, fixed_result.stderr):
                return TaskValidation(
                    task_id=task.task_id,
                    passed=False,
                    reason=f"test_command_not_runnable:exit_{fixed_result.exit_code}",
                    determinism_runs=k_determinism,
                    determinism_failures=determinism_failures,
                )
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
