"""Benchmark task runner — executes an agent against a manifest/suite of tasks (E0 / Block 2)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Literal, cast

import anyio

from sagiha.adapters.search.best_of_n import BestOfNSearch
from sagiha.agency.context.system_prompt import resolve_system_prompt
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel, build_retrieval_seed, ensure_index
from sagiha.domain.benchmark import BenchmarkResult, BenchmarkRun, BenchmarkSuite, HarvestedTask
from sagiha.domain.config import (
    Config,
    ModelConfig,
    RepairConfig,
    SandboxConfig,
    SearchConfig,
    TelemetryConfig,
    WorkspaceConfig,
)
from sagiha.domain.control import RunContext
from sagiha.domain.graph import RetrievalHit
from sagiha.domain.identity import utc_now
from sagiha.domain.work import GateReport

logger = logging.getLogger(__name__)

#: `GateReport.required_gates`, in the order the reporter's failure breakdown attributes a
#: multi-gate failure to a single "first cause" — deterministic, so the same run always
#: attributes the same way.
_GATE_ATTRIBUTION_ORDER = (
    "tests_unmodified",
    "diff_within_bounds",
    "no_new_suppressions",
    "coverage_not_decreased",
)


class BenchmarkRunnerError(RuntimeError):
    """Base exception for benchmark runner failures."""


def _first_gate_failure(gate_report: GateReport) -> str | None:
    """The first required gate that reports an explicit `False`, in a fixed attribution order.

    `None` means either the run resolved, or every non-passing gate reported `None` (could not
    be evaluated) rather than an explicit failure — those two cases are distinguishable by
    `BenchmarkResult.resolved`, not by this field.
    """
    for name in _GATE_ATTRIBUTION_ORDER:
        if name in gate_report.required_gates and getattr(gate_report, name, None) is False:
            return name
    return None


class BenchmarkRunner:
    """Runs an agent over a benchmark suite, evaluating per-task admission and recording metrics."""

    def __init__(
        self,
        suite: BenchmarkSuite,
        *,
        agent_id: str = "sagiha",
        model_mode: Literal["live", "replay", "record"] = "replay",
        cassette_path: str | None = None,
        workspace_root: str | None = None,
        trajectory_db: str = ".sagiha/trajectories.db",
        max_steps: int | None = None,
        strategy: Literal["single_shot", "bon"] = "single_shot",
        search: SearchConfig | None = None,
        model_config: ModelConfig | None = None,
        sandbox: SandboxConfig | None = None,
        repair: RepairConfig | None = None,
    ) -> None:
        self._suite = suite
        self._agent_id = agent_id
        self._model_mode = model_mode
        self._cassette_path = cassette_path or ".sagiha/cassettes/default.json"
        self._workspace_root = workspace_root or suite.repo
        self._trajectory_db = trajectory_db
        #: `None` (the default) resolves to `config.governor.max_steps_per_run` at each call
        #: site rather than an independent default — this constructor arg used to shadow the
        #: configured 200 with a silent 20 for every bench run (correction 2).
        self._max_steps = max_steps
        self._repair = repair
        #: `"single_shot"` runs the inner loop once per task (the control arm). `"bon"` runs
        #: Best-of-N over real worktrees via `Kernel.candidate_search` (the treatment arm).
        #: Both arms must be run by the *same* runner class against the *same* suite, or the
        #: paired statistics compare two harnesses rather than two strategies.
        self._strategy = strategy
        self._search = search or SearchConfig(enabled=True)
        #: Explicit model binding for the run. Without this the runner fell back to
        #: ModelConfig's defaults (an Anthropic tier) while pointing at whatever
        #: base_url was configured, so a local Ollama endpoint was asked for a
        #: Claude model and returned 404 on every task.
        self._model_config = model_config
        #: `None` preserves `Config`'s own default (`runtime="container"`, the ADR-0016
        #: security posture for real runs). A worktree's `.git` file points *outside* the
        #: worktree directory (`<repo>/.git/worktrees/<id>`), which a container mounting only
        #: the worktree leaf cannot resolve — every coding-profile gate then reports `None`
        #: ("could not evaluate"), not a security failure, just an unmet mount requirement.
        #: Callers that don't need the perimeter (a cheap CI smoke check, a local dev run
        #: without Podman) pass `SandboxConfig(runtime="subprocess")` explicitly.
        self._sandbox = sandbox

    def _model_for_run(self) -> ModelConfig:
        mode_val = cast(Literal["live", "replay", "record"], self._model_mode)
        if self._model_config is not None:
            return self._model_config.model_copy(update={"mode": mode_val})
        return ModelConfig(mode=mode_val)

    def _sandbox_for_run(self) -> SandboxConfig:
        return self._sandbox if self._sandbox is not None else SandboxConfig()

    def _repair_for_run(self) -> RepairConfig:
        return self._repair if self._repair is not None else RepairConfig()

    def _repo_root_for(self, task: HarvestedTask) -> str:
        """The repository this task's worktree is cut from.

        A harvested task's base commit is in the harness repo and resolves to it
        unchanged. An *imported* task (SWE-bench Lite) has a base commit from a
        different project, which is fetched shallowly into the repo cache — the
        alternative was `fatal: invalid reference` on every task, a failure that
        reads exactly like an unsolved benchmark.
        """
        from sagiha.e0.repo_cache import resolve_task_root

        return str(resolve_task_root(task.repo, task.base_commit, workspace_root=self._workspace_root))

    async def run_single_task(self, task: HarvestedTask) -> BenchmarkResult:
        """Dispatches to the configured arm. Both arms return the same `BenchmarkResult`
        shape so `paired_deltas` can pair them task-for-task."""
        if self._strategy == "bon":
            return await self._run_single_task_bon(task)
        return await self._run_single_task_single_shot(task)

    async def _run_single_task_bon(self, task: HarvestedTask) -> BenchmarkResult:
        """Best-of-N arm: `BestOfNSearch` proposes N candidates in their own worktrees, ranks
        the admitted subset, and the selected candidate's gate report decides `resolved`.

        No outer worktree is allocated here — unlike the single-shot arm, the search adapter's
        executor allocates and releases one worktree per candidate itself. Cost is the summed
        cost of **all** candidates (`batch_cost`), not the winner's, so cost-per-resolved-task
        reflects what Best-of-N actually charges.
        """
        run_id = str(uuid.uuid4())
        start_time = time.monotonic()
        try:
            task_repo_root = self._repo_root_for(task)
            config = Config(
                model=self._model_for_run(),
                workspace=WorkspaceConfig(root=task_repo_root),
                telemetry=TelemetryConfig(trajectory_db=self._trajectory_db),
                search=self._search,
                sandbox=self._sandbox_for_run(),
                repair=self._repair_for_run(),
            )
            kernel = build_kernel(config, cassette_path=self._cassette_path)
            search = kernel.candidate_search
            if search is None:
                raise BenchmarkRunnerError(
                    "strategy='bon' requires search.enabled=True — build_kernel returned no CandidateSearch"
                )

            task_spec = make_task(
                goal=f"Fix issue: {task.diff_summary}",
                checks=[task.failing_test_cmd],
                task_id=run_id,
            )
            ctx = RunContext(
                run_id=run_id,
                autonomy_level=config.autonomy.level,
                workspace_root=task_repo_root,
                budget_remaining_usd=config.governor.max_spend_usd_per_run,
                base_commit=task.base_commit,
            )

            n = max(1, config.search.candidates)
            branch_ids = await search.propose(task_spec, ctx, n)
            winner = await search.select(branch_ids)
            gate_report = await search.evaluate(winner)
            elapsed = time.monotonic() - start_time

            # `batch_cost`/`diversity_ratio` are concrete-class-only — the `CandidateSearch`
            # Protocol deliberately has no cost or diversity surface (see `BestOfNSearch`).
            # A different adapter still runs; it just reports neither figure.
            batch_cost = search.batch_cost(branch_ids) if isinstance(search, BestOfNSearch) else None
            diversity = search.diversity_ratio(branch_ids) if isinstance(search, BestOfNSearch) else None

            return BenchmarkResult(
                task_id=task.task_id,
                agent_id=self._agent_id,
                resolved=bool(gate_report and gate_report.admitted),
                gate_report=gate_report,
                cost=batch_cost,
                wall_clock_s=elapsed,
                gate_failure_kind=(
                    None
                    if (gate_report and gate_report.admitted)
                    else (_first_gate_failure(gate_report) if gate_report else None)
                ),
                strategy="bon",
                diversity_ratio=diversity,
                candidates=len(branch_ids),
            )
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            logger.error("Benchmark task %s (bon) failed with exception: %s", task.task_id, exc)
            return BenchmarkResult(
                task_id=task.task_id,
                agent_id=self._agent_id,
                resolved=False,
                gate_report=None,
                cost=None,
                steps=0,
                wall_clock_s=elapsed,
                error=str(exc),
                strategy="bon",
            )

    async def _run_single_task_single_shot(self, task: HarvestedTask) -> BenchmarkResult:
        run_id = str(uuid.uuid4())
        start_time = time.monotonic()

        from sagiha.adapters.workspace.worktree import GitWorktreeManager

        manager = GitWorktreeManager(self._repo_root_for(task))
        branch_id = f"bench-{task.task_id}-{run_id[:8]}"
        allocated = False

        try:
            await manager.allocate(task.base_commit, branch_id, run_id=run_id)
            allocated = True
            # `Workspace` (the port) deliberately has no path accessor — `path_for` is a
            # concrete-class-only escape hatch for exactly this caller, which must rebuild a
            # `Kernel` bound to the worktree's real filesystem location.
            task_root = str(await anyio.Path(manager.path_for(branch_id)).resolve())

            config = Config(
                model=self._model_for_run(),
                workspace=WorkspaceConfig(root=task_root),
                telemetry=TelemetryConfig(trajectory_db=self._trajectory_db),
                sandbox=self._sandbox_for_run(),
                repair=self._repair_for_run(),
            )
            # The control arm must not build search machinery it will never call — otherwise
            # every single-shot task pays construction cost for a `BestOfNSearch` and a second
            # `GitWorktreeManager`, and the "control" arm is no longer the thing it controls for.
            kernel = build_kernel(config, cassette_path=self._cassette_path, include_search=False)

            system_prompt = await resolve_system_prompt(task_root)

            task_spec = make_task(
                goal=f"Fix issue: {task.diff_summary}",
                checks=[task.failing_test_cmd],
                task_id=run_id,
            )

            # AD-5: retrieval-before-edit is a default-on loop *step*, not a tool the model
            # may skip — a harness-issued search precedes the first turn whenever retrieval is
            # enabled. Seed-only-by-shape (ADR-0021): `RunLoop.__init__` is the only place a
            # `RetrievalHit` enters, never refreshed mid-run.
            retrieval_seed: tuple[RetrievalHit, ...] = ()
            if config.retrieval.enabled and kernel.indexer is not None:
                await ensure_index(kernel)
                retrieval_seed = await build_retrieval_seed(
                    kernel.indexer, task_spec.goal, config.retrieval.top_k
                )

            loop = RunLoop(
                model_provider=kernel.model_provider,
                policy_engine=kernel.policy_engine,
                resource_governor=kernel.resource_governor,
                tool_registry=kernel.tool_registry,
                trajectory_store=kernel.trajectory_store,
                bus=kernel.bus,
                max_steps=self._max_steps
                if self._max_steps is not None
                else kernel.config.governor.max_steps_per_run,
                tool_schemas=list(kernel.tool_schemas),
                evaluator=kernel.evaluator,
                workspace=kernel.workspace,
                pricing=kernel.config.pricing,
                context=kernel.config.context,
                repair=kernel.config.repair,
                retrieval_seed=retrieval_seed,
                system_prompt=system_prompt,
            )

            ctx = RunContext(
                run_id=run_id,
                autonomy_level=config.autonomy.level,
                workspace_root=task_root,
                budget_remaining_usd=config.governor.max_spend_usd_per_run,
                # The task's own base_commit, not a self-checkpoint of whatever the worktree
                # happens to be on — the gates must diff against the task's recorded baseline.
                base_commit=task.base_commit,
            )

            loop_result = await loop.run(task_spec, ctx)
            elapsed = time.monotonic() - start_time

            cache_read_total = sum(step.usage.cache_read_tokens for step in loop_result.steps)
            input_total = sum(step.usage.input_tokens for step in loop_result.steps)
            cache_hit = (cache_read_total > 0) if input_total > 0 else None

            return BenchmarkResult(
                task_id=task.task_id,
                agent_id=self._agent_id,
                resolved=loop_result.gate_report.admitted,
                gate_report=loop_result.gate_report,
                cost=loop_result.cost,
                steps=len(loop_result.steps),
                wall_clock_s=elapsed,
                gate_failure_kind=(
                    None if loop_result.gate_report.admitted else _first_gate_failure(loop_result.gate_report)
                ),
                cache_hit=cache_hit,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            logger.error("Benchmark task %s failed with exception: %s", task.task_id, exc)
            return BenchmarkResult(
                task_id=task.task_id,
                agent_id=self._agent_id,
                resolved=False,
                gate_report=None,
                cost=None,
                steps=0,
                wall_clock_s=elapsed,
                error=str(exc),
            )
        finally:
            if allocated:
                await manager.release(branch_id, run_id=run_id)

    async def run_suite(self, run_id: str | None = None, *, k: int = 1) -> BenchmarkRun:
        """Run the full suite once, or `k` times per task when `k > 1`.

        `k >= 3` is the plan's own requirement for reporting variance rather than a point
        estimate (`docs/06-guides-and-patterns/running-benchmarks.md` rule 1). Each repetition
        of a task gets its own worktree and its own `run_id` internally; all repetitions land
        in one flat `BenchmarkRun.results` tuple, distinguishable by `task_id` recurring `k`
        times — the reporter aggregates by grouping on it.
        """
        actual_run_id = run_id or str(uuid.uuid4())
        results: list[BenchmarkResult] = []

        for task in self._suite.tasks:
            for _ in range(max(1, k)):
                result = await self.run_single_task(task)
                results.append(result)

        return BenchmarkRun(
            run_id=actual_run_id,
            suite_id=self._suite.suite_id,
            agent_id=self._agent_id,
            results=tuple(results),
            status="completed",
            started_at=utc_now(),
            completed_at=utc_now(),
        )
