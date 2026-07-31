"""SAGIHA command-line entry point — Sprint 3a: version, run, replay."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Literal

import anyio
import typer

from sagiha.agency.run_loop import RunLoop, RunLoopResult, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.control import RunContext

app = typer.Typer(name="sagiha", help="SAGIHA — Super AGI Harness Agent")


@app.command()
def version() -> None:
    """Print the installed SAGIHA version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("sagiha"))


async def _run_or_resume(
    *,
    goal: str | None,
    checks: list[str],
    workspace: str,
    cassette_path: str,
    max_steps: int,
    trajectory_db: str,
    resume: str | None,
    mode: str = "replay",
    model_name: str = "qwen2.5-coder:7b",
    base_url: str = "http://localhost:11434/v1",
) -> tuple[str, RunLoopResult | str | None]:
    if resume is None and goal is None:
        return "missing_goal", None

    model_mode = "live" if mode == "live" else ("record" if mode == "record" else "replay")
    from sagiha.domain.config import ModelTierConfig

    local_tier = ModelTierConfig(
        provider="openai-compatible",
        model=model_name,
        base_url=base_url,
        api_key_env="",
    )
    config = Config(
        model=ModelConfig(
            mode=model_mode,
            tiers={
                "local": local_tier,
                "workhorse": local_tier,
            },
            roles={"execution": "local"},
        ),
        workspace=WorkspaceConfig(root=workspace),
        telemetry=TelemetryConfig(trajectory_db=trajectory_db),
    )
    kernel = build_kernel(config, cassette_path=cassette_path)
    loop = RunLoop(
        model_provider=kernel.model_provider,
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        max_steps=max_steps,
        tool_schemas=list(kernel.tool_schemas),
        evaluator=kernel.evaluator,
        workspace=kernel.workspace,
        pricing=kernel.config.pricing,
    )

    if resume is not None:
        existing = await kernel.trajectory_store.get_run(resume)
        if existing is None:
            return "no_such_run", resume
        run_id = resume
        task = existing.task
    else:
        assert goal is not None  # guaranteed by the early return above
        run_id = str(uuid.uuid4())
        task = make_task(goal, checks, task_id=run_id)

    ctx = RunContext(
        run_id=run_id,
        autonomy_level=config.autonomy.level,
        workspace_root=str(await anyio.Path(workspace).resolve()),
        budget_remaining_usd=config.governor.max_spend_usd_per_run,
    )
    result = await loop.run(task, ctx, resume=resume is not None)
    return "ok", result


@app.command()
def run(
    goal: str | None = typer.Argument(None, help="Task goal for the agent (omit with --resume)"),
    acceptance: list[str] | None = typer.Option(
        None,
        "--acceptance",
        "-a",
        help="Shell check command (repeatable)",
    ),
    workspace: str = typer.Option(".", "--workspace", "-w"),
    cassette: str | None = typer.Option(None, "--cassette", "-c"),
    max_steps: int = typer.Option(20, "--max-steps"),
    trajectory_db: str = typer.Option(".sagiha/trajectories.db", "--trajectory-db"),
    resume: str | None = typer.Option(
        None, "--resume", help="Continue an interrupted run_id instead of starting a new task"
    ),
    mode: str = typer.Option(
        "replay", "--mode", "-m", help="Model execution mode ('replay', 'live', 'record')"
    ),
    model_name: str = typer.Option("qwen2.5-coder:7b", "--model-name", help="Model name for live mode"),
    base_url: str = typer.Option(
        "http://localhost:11434/v1", "--base-url", help="OpenAI-compatible endpoint URL"
    ),
) -> None:
    """Run a coding task end-to-end (replay cassette by default in Sprint 3a)."""
    checks = acceptance if acceptance else ["true"]
    cassette_path = cassette or ".sagiha/cassettes/default.json"
    outcome, payload = asyncio.run(
        _run_or_resume(
            goal=goal,
            checks=checks,
            workspace=workspace,
            cassette_path=cassette_path,
            max_steps=max_steps,
            trajectory_db=trajectory_db,
            resume=resume,
            mode=mode,
            model_name=model_name,
            base_url=base_url,
        )
    )

    if outcome == "no_such_run":
        typer.echo(f"No run found for run_id={payload} in {trajectory_db}")
        raise SystemExit(1)
    if outcome == "missing_goal":
        typer.echo("goal is required unless --resume is given")
        raise SystemExit(2)

    assert isinstance(payload, RunLoopResult)
    typer.echo(f"run_id={payload.run_id}")
    typer.echo(f"admitted={payload.gate_report.admitted}")
    typer.echo(f"steps={len(payload.steps)}")
    raise SystemExit(0 if payload.gate_report.admitted else 1)


@app.command()
def replay(
    run_id: str = typer.Argument(..., help="Run id or 'verify' sentinel"),
    verify: bool = typer.Option(False, "--verify"),
    cassette: str = typer.Option(".sagiha/cassettes/default.json", "--cassette", "-c"),
    workspace: str = typer.Option(".", "--workspace", "-w"),
    trajectory_db: str = typer.Option(".sagiha/trajectories.db", "--trajectory-db"),
) -> None:
    """Replay a cassette-driven run and optionally verify gate admission."""
    if not verify and run_id != "verify":
        typer.echo("Pass --verify to execute digest-checked cassette replay")
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=workspace),
        telemetry=TelemetryConfig(trajectory_db=trajectory_db),
    )
    kernel = build_kernel(config, cassette_path=cassette)
    # Verification: re-run with the same cassette; mismatch raises CassetteMismatchError.
    from sagiha.adapters.model.cassette import CassetteMismatchError

    loop = RunLoop(
        model_provider=kernel.model_provider,
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        tool_schemas=list(kernel.tool_schemas),
        evaluator=kernel.evaluator,
        workspace=kernel.workspace,
        pricing=kernel.config.pricing,
    )
    new_run_id = str(uuid.uuid4())
    ctx = RunContext(
        run_id=new_run_id,
        autonomy_level="interactive",
        workspace_root=str(Path(workspace).resolve()),
        budget_remaining_usd=config.governor.max_spend_usd_per_run,
    )
    # Goal recovered from cassette is not stored yet — use a placeholder for verify smoke.
    task = make_task("replay verification", ["true"], task_id=new_run_id)
    try:
        result = asyncio.run(loop.run(task, ctx))
    except CassetteMismatchError as exc:
        typer.echo(f"replay verify FAILED: {exc}")
        raise SystemExit(2) from exc
    typer.echo(f"replay_ok run_id={result.run_id} admitted={result.gate_report.admitted}")
    raise SystemExit(0)


@app.command()
def harvest(
    repo: str = typer.Option(".", "--repo", "-r", help="Path to repository to harvest"),
    output: str = typer.Option(
        ".sagiha/benchmark/suite.json", "--output", "-o", help="Output path for BenchmarkSuite JSON"
    ),
    max_commits: int = typer.Option(200, "--max-commits", help="Maximum commits to inspect"),
    test_cmd: str = typer.Option("pytest", "--test-cmd", help="Test command to run for tasks"),
    suite_id: str = typer.Option("s0-baseline", "--suite-id", help="Suite identifier"),
) -> None:
    """Harvest commit-replay evaluation tasks from git repository history (E0)."""
    from sagiha.e0.harvester import Harvester

    typer.echo(f"Harvesting tasks from {repo} (max {max_commits} commits)...")
    harvester = Harvester(repo, test_cmd=test_cmd, max_commits=max_commits)
    suite = asyncio.run(harvester.harvest_suite(suite_id=suite_id))

    harvester.save_suite(suite, output)
    typer.echo(f"Harvested {len(suite.tasks)} tasks -> {output}")


@app.command()
def bench(
    suite_path: str = typer.Option(
        ".sagiha/benchmark/suite.json", "--suite", "-s", help="Path to BenchmarkSuite JSON"
    ),
    mode: str = typer.Option(
        "replay", "--mode", "-m", help="Model execution mode ('replay', 'live', 'record')"
    ),
    cassette: str = typer.Option(".sagiha/cassettes/default.json", "--cassette", "-c", help="Cassette path"),
    output: str = typer.Option(
        ".sagiha/benchmark/report.md", "--output", "-o", help="Output report path (.md or .json)"
    ),
    aa: bool = typer.Option(False, "--aa", help="Run A/A noise floor calibration (2 passes)"),
) -> None:
    """Run E0 evaluation benchmark over a harvested task suite."""

    from sagiha.domain.benchmark import ComparisonResult, NoiseFloor
    from sagiha.e0.harvester import Harvester
    from sagiha.e0.reporter import BenchmarkReporter
    from sagiha.e0.runner import BenchmarkRunner
    from sagiha.e0.statistics import StatisticalAnalyzer

    suite_file = Path(suite_path)
    if not suite_file.exists():
        typer.echo(f"Benchmark suite file not found: {suite_path}")
        raise SystemExit(1)

    suite = Harvester.load_suite(suite_file)
    typer.echo(f"Running benchmark suite '{suite.suite_id}' ({len(suite.tasks)} tasks, mode={mode})...")

    mode_val: Literal["live", "replay", "record"] = (
        "live" if mode == "live" else ("record" if mode == "record" else "replay")
    )
    runner = BenchmarkRunner(
        suite=suite,
        model_mode=mode_val,
        cassette_path=cassette,
        workspace_root=suite.repo,
    )

    run_a = asyncio.run(runner.run_suite(run_id="run-pass-1"))
    nf: NoiseFloor | None = None
    comp: ComparisonResult | None = None

    if aa:
        typer.echo("Running second pass for A/A noise floor calibration...")
        run_b = asyncio.run(runner.run_suite(run_id="run-pass-2"))
        nf = StatisticalAnalyzer.compute_noise_floor(run_a, run_b)
        comp = StatisticalAnalyzer.compare_runs(run_a, run_b)
        typer.echo(
            f"A/A Calibration mean_delta: {nf.mean_delta:.3f}, beats_noise_floor: {comp.beats_noise_floor}"
        )

    if output.endswith(".json"):
        report_content = BenchmarkReporter.render_json(run_a, noise_floor=nf, comparison=comp)
    else:
        report_content = BenchmarkReporter.render_markdown(run_a, noise_floor=nf, comparison=comp)

    out_file = Path(output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_content)

    pass_rate = StatisticalAnalyzer.compute_pass_rate(run_a)
    typer.echo(f"Benchmark complete! Pass rate: {pass_rate:.1%}. Report written to {output}")


if __name__ == "__main__":
    app()
