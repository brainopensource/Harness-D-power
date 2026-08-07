"""The real `ValidityInstrument` behind TASK-014's canary.

`measurement/manifest.py` is TCB and may not import `aether.adapters`; this
module is the non-TCB half that may. It does the physical work the canary
policy describes: create a worktree at the task's base commit, apply the patch
under test (or nothing, for the empty-patch direction), and run the task's
pinned test command through the same `RealEvaluator` every benchmark run uses.

One instrument, both directions, both arms. Screening a manifest on a
different instrument than the one that will later score the run is how a
manifest full of tasks that "work" ends up producing instrument errors on the
day of the benchmark.
"""

from __future__ import annotations

from uuid import uuid4

from aether.adapters.workspace.git_cli import GitCliWorkspace, GitCliWorktreeManager
from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import RunId, TaskId
from aether.measurement.evaluator import RealEvaluator, hash_command
from aether.measurement.manifest import EMPTY_PATCH, TaskCandidate
from aether.ports.evaluator import EvalSpec


class WorktreeValidityInstrument:
    """Screens candidates against a local clone of the task's repository.

    `repo_path` is the upstream clone B1's cache (`measurement/repo_cache.py`)
    materialized — the base commit has to be resolvable locally or the task is
    an `instrument_error`, which is exactly what the canary should record
    rather than silently skipping.
    """

    def __init__(
        self,
        repo_path: str,
        worktrees_root: str,
        evaluator: RealEvaluator,
        timeout_ms: int = 900_000,
    ) -> None:
        self._worktrees = GitCliWorktreeManager(repo_path, worktrees_root)
        self._workspace = GitCliWorkspace(worktrees_root)
        self._evaluator = evaluator
        self._timeout_ms = timeout_ms

    @property
    def is_contained(self) -> bool:
        return self._evaluator.is_contained

    async def evaluate_patch(self, candidate: TaskCandidate, patch: str) -> GateReport:
        run_id = RunId(f"canary-{uuid4().hex[:12]}")
        try:
            worktree = await self._worktrees.create(run_id, candidate.base_commit)
        except Exception as exc:  # unresolvable base commit, missing clone, git failure
            return GateReport(
                gate="tests",
                status=GateStatus.NONE,
                instrument_error=f"worktree creation failed for {candidate.instance_id}: {exc}",
            )

        try:
            if patch != EMPTY_PATCH:
                result = await self._workspace.apply_patch(worktree, patch)
                if not result.applied:
                    # An unappliable gold patch is our instrument (or the
                    # upstream record) failing, not the task's tests failing.
                    return GateReport(
                        gate="tests",
                        status=GateStatus.NONE,
                        instrument_error=(
                            f"patch did not apply ({result.rejected_hunks} rejected hunks): "
                            f"{result.detail}"
                        ),
                    )

            return await self._evaluator.evaluate(
                EvalSpec(
                    task_id=TaskId(candidate.instance_id),
                    worktree=worktree,
                    image_digest=candidate.environment_image_digest,
                    test_command_hash=hash_command(candidate.test_command),
                    timeout_ms=self._timeout_ms,
                )
            )
        finally:
            try:
                await self._worktrees.destroy(worktree)
            except Exception:  # noqa: BLE001 - cleanup must never mask a verdict
                pass


__all__ = ["WorktreeValidityInstrument"]
