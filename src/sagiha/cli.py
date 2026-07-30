"""SAGIHA command-line entry point — Sprint 3a: version, run, replay."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import typer

from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.control import RunContext

app = typer.Typer(name="sagiha", help="SAGIHA — Super AGI Harness Agent")


@app.command()
def version() -> None:
    """Print the installed SAGIHA version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("sagiha"))


@app.command()
def run(
    goal: str = typer.Argument(..., help="Task goal for the agent"),
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
) -> None:
    """Run a coding task end-to-end (replay cassette by default in Sprint 3a)."""
    checks = acceptance if acceptance else ["true"]
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=workspace),
        telemetry=TelemetryConfig(trajectory_db=trajectory_db),
    )
    cassette_path = cassette or ".sagiha/cassettes/default.json"
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
    )
    run_id = str(uuid.uuid4())
    ctx = RunContext(
        run_id=run_id,
        autonomy_level=config.autonomy.level,
        workspace_root=str(Path(workspace).resolve()),
        budget_remaining_usd=config.governor.max_spend_usd_per_run,
    )
    task = make_task(goal, checks, task_id=run_id)
    result = asyncio.run(loop.run(task, ctx))
    typer.echo(f"run_id={result.run_id}")
    typer.echo(f"admitted={result.gate_report.admitted}")
    typer.echo(f"steps={len(result.steps)}")
    raise SystemExit(0 if result.gate_report.admitted else 1)


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


if __name__ == "__main__":
    app()
