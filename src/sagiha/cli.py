"""SAGIHA command-line entry point — Sprint 3a: version, run, replay."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import anyio
import typer

from sagiha.agency.run_loop import RunLoop, RunLoopResult, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.control import RunContext
from sagiha.domain.events import ReplayVerified

if TYPE_CHECKING:
    from sagiha.adapters.tools.cassette import CassetteToolRegistry

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
        context=kernel.config.context,
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


@dataclass
class ReplayOutcome:
    loop_result: RunLoopResult | None
    cassette_tool_registry: CassetteToolRegistry | None
    #: The real `run_id` whose recorded task this replay verified — `None` for the `"verify"`
    #: sentinel path (no corresponding stored run) or when `run_id` was not found at all. Only
    #: a non-`None` value is eligible for a `ReplayVerified` event: emitting one against the
    #: sentinel would tag a run_id that does not exist in this trajectory store.
    verified_run_id: str | None
    run_not_found: bool = False


async def _do_replay(
    *,
    run_id: str,
    cassette: str,
    workspace: str,
    trajectory_db: str,
    tool_cassette: str | None,
) -> ReplayOutcome:
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=workspace),
        telemetry=TelemetryConfig(trajectory_db=trajectory_db),
    )
    kernel = build_kernel(config, cassette_path=cassette)

    tool_registry = kernel.tool_registry
    cassette_tool_registry = None
    if tool_cassette is not None:
        from sagiha.adapters.tools.cassette import CassetteToolRegistry

        cassette_tool_registry = CassetteToolRegistry(kernel.tool_registry, tool_cassette, mode="replay")  # type: ignore[arg-type]
        tool_registry = cassette_tool_registry

    loop = RunLoop(
        model_provider=kernel.model_provider,
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        tool_schemas=list(kernel.tool_schemas),
        evaluator=kernel.evaluator,
        workspace=kernel.workspace,
        pricing=kernel.config.pricing,
        context=kernel.config.context,
    )
    new_run_id = str(uuid.uuid4())
    ctx = RunContext(
        run_id=new_run_id,
        autonomy_level="interactive",
        workspace_root=str(await anyio.Path(workspace).resolve()),
        budget_remaining_usd=config.governor.max_spend_usd_per_run,
    )

    verified_original_run_id: str | None = None
    if run_id == "verify":
        # No stored run to recover a goal from — the generic CI smoke path.
        task = make_task("replay verification", ["true"], task_id=new_run_id)
    else:
        existing = await kernel.trajectory_store.get_run(run_id)
        if existing is None:
            return ReplayOutcome(
                loop_result=None,
                cassette_tool_registry=None,
                verified_run_id=None,
                run_not_found=True,
            )
        task = existing.task
        verified_original_run_id = run_id

    result = await loop.run(task, ctx)
    if verified_original_run_id is not None:
        await kernel.bus.emit(ReplayVerified(run_id=verified_original_run_id, replay_run_id=new_run_id))
    return ReplayOutcome(
        loop_result=result,
        cassette_tool_registry=cassette_tool_registry,
        verified_run_id=verified_original_run_id,
    )


@app.command()
def replay(
    run_id: str = typer.Argument(..., help="Run id or 'verify' sentinel"),
    verify: bool = typer.Option(False, "--verify"),
    cassette: str = typer.Option(".sagiha/cassettes/default.json", "--cassette", "-c"),
    workspace: str = typer.Option(".", "--workspace", "-w"),
    trajectory_db: str = typer.Option(".sagiha/trajectories.db", "--trajectory-db"),
    tool_cassette: str | None = typer.Option(
        None,
        "--tool-cassette",
        help="Also verify tool dispatch against a recorded tool cassette (ADR-0020): "
        "PURE-classified calls re-execute, everything else is served from the recording.",
    ),
) -> None:
    """Replay a cassette-driven run and optionally verify gate admission.

    Against a real `run_id`, replays that run's own recorded goal (loaded via
    `TrajectoryStore.get_run`) rather than a placeholder, and — on success — emits
    `ReplayVerified` against the ORIGINAL `run_id`. That event is one of the exporter's four
    eligibility criteria (v2-S4 Epic S4.4); without it, "replay-verified" was not expressible
    for any run that was not the `"verify"` sentinel.
    """
    if not verify and run_id != "verify":
        typer.echo("Pass --verify to execute digest-checked cassette replay")
    from sagiha.adapters.model.cassette import CassetteMismatchError

    try:
        outcome = asyncio.run(
            _do_replay(
                run_id=run_id,
                cassette=cassette,
                workspace=workspace,
                trajectory_db=trajectory_db,
                tool_cassette=tool_cassette,
            )
        )
    except CassetteMismatchError as exc:
        typer.echo(f"replay verify FAILED: {exc}")
        raise SystemExit(2) from exc

    if outcome.run_not_found or outcome.loop_result is None:
        typer.echo(f"No run found for run_id={run_id} in {trajectory_db}")
        raise SystemExit(1)

    cassette_tool_registry = outcome.cassette_tool_registry
    if cassette_tool_registry is not None:
        total = cassette_tool_registry.re_executed + cassette_tool_registry.served_from_cassette
        pct = (cassette_tool_registry.re_executed / total * 100) if total else 0.0
        typer.echo(
            f"tool_reexecution: {cassette_tool_registry.re_executed}/{total} steps ({pct:.1f}%) "
            f"re-executed; {cassette_tool_registry.served_from_cassette} served from cassette"
        )
    result = outcome.loop_result
    typer.echo(f"replay_ok run_id={result.run_id} admitted={result.gate_report.admitted}")
    if outcome.verified_run_id is not None:
        typer.echo(f"ReplayVerified emitted for run_id={outcome.verified_run_id}")
    raise SystemExit(0)


@app.command()
def harvest(
    repo: str = typer.Option(".", "--repo", "-r", help="Path to repository to harvest"),
    output: str = typer.Option(
        ".sagiha/benchmark/suite.json", "--output", "-o", help="Output path for BenchmarkSuite JSON"
    ),
    max_commits: int = typer.Option(200, "--max-commits", help="Maximum commits to inspect"),
    test_cmd: str = typer.Option("python -m pytest", "--test-cmd", help="Test command to run for tasks"),
    suite_id: str = typer.Option("s0-baseline", "--suite-id", help="Suite identifier"),
    validate: bool = typer.Option(
        True, "--validate/--no-validate", help="Validate clean revert + reproducing failure per task"
    ),
    min_tasks: int = typer.Option(
        30, "--min-tasks", help="Minimum valid tasks required (E0 slice gate); exits non-zero below it"
    ),
    k_determinism: int = typer.Option(
        3, "--k-determinism", help="Reruns of the failing test to probe for flakiness"
    ),
) -> None:
    """Harvest commit-replay evaluation tasks from git repository history (E0)."""
    from sagiha.e0.harvester import Harvester

    typer.echo(f"Harvesting tasks from {repo} (max {max_commits} commits)...")
    harvester = Harvester(repo, test_cmd=test_cmd, max_commits=max_commits)
    suite = asyncio.run(harvester.harvest_suite(suite_id=suite_id))
    typer.echo(f"Harvested {len(suite.tasks)} candidate tasks")

    if not validate:
        harvester.save_suite(suite, output)
        typer.echo(f"Harvested {len(suite.tasks)} tasks -> {output} (unvalidated: --no-validate)")
        return

    typer.echo(f"Validating {len(suite.tasks)} candidate tasks (k={k_determinism})...")
    validated_suite, suite_validation = asyncio.run(
        harvester.validate_suite(suite, min_tasks=min_tasks, k_determinism=k_determinism)
    )
    for result in suite_validation.task_results:
        if not result.passed:
            typer.echo(f"  reject {result.task_id}: {result.reason}")

    harvester.save_suite(validated_suite, output)
    typer.echo(
        f"Validated {suite_validation.valid_tasks}/{suite_validation.total_tasks} tasks "
        f"(need >= {min_tasks}) -> {output}"
    )
    if not suite_validation.passed:
        typer.echo(
            f"FAILED: only {suite_validation.valid_tasks} valid tasks, need >= {min_tasks} (E0 slice gate)"
        )
        raise SystemExit(1)


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
    runs: int = typer.Option(
        1, "--runs", "-k", help="Repetitions per task, for reporting variance (k>=3 recommended)"
    ),
    compare: str = typer.Option(
        "",
        "--compare",
        help="Two comma-separated arms to compare, e.g. 'single_shot,bon'. Runs both and reports "
        "the paired delta. Requires --aa (or --noise-floor) so the delta is judged against a floor.",
    ),
    noise_floor_path: str = typer.Option(
        "",
        "--noise-floor",
        help="Path to a previously written A/A report JSON, reused as the floor for --compare.",
    ),
) -> None:
    """Run E0 evaluation benchmark over a harvested task suite."""

    from sagiha.domain.benchmark import BenchmarkRun, ComparisonResult, NoiseFloor
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

    def _runner(strategy: Literal["single_shot", "bon"]) -> BenchmarkRunner:
        return BenchmarkRunner(
            suite=suite,
            model_mode=mode_val,
            cassette_path=cassette,
            workspace_root=suite.repo,
            strategy=strategy,
            agent_id=f"sagiha-{strategy}",
        )

    nf: NoiseFloor | None = None
    comp: ComparisonResult | None = None

    if compare:
        arms = [a.strip() for a in compare.split(",") if a.strip()]
        valid = {"single_shot", "bon"}
        if len(arms) != 2 or not set(arms) <= valid or arms[0] == arms[1]:
            typer.echo(f"--compare needs two distinct arms from {sorted(valid)}, got {compare!r}")
            raise SystemExit(1)

        control_arm = cast(Literal["single_shot", "bon"], arms[0])
        treatment_arm = cast(Literal["single_shot", "bon"], arms[1])

        # The floor comes first and from the *control* arm, run against itself. A treatment
        # delta judged against no floor — or against a floor measured under a different
        # launch_mode/arm — is the H5 failure shape: a number with nothing to beat.
        if noise_floor_path:
            nf = NoiseFloor.model_validate(json.loads(Path(noise_floor_path).read_text())["noise_floor"])
            typer.echo(f"Reusing noise floor from {noise_floor_path} (n={nf.n_tasks})")
        elif aa:
            typer.echo(f"A/A calibration on the control arm ({control_arm})...")
            floor_a = asyncio.run(_runner(control_arm).run_suite(run_id="aa-pass-1", k=runs))
            floor_b = asyncio.run(_runner(control_arm).run_suite(run_id="aa-pass-2", k=runs))
            nf = StatisticalAnalyzer.compute_noise_floor(floor_a, floor_b)
            typer.echo(f"  floor mean_delta={nf.mean_delta:.4f} CI={nf.confidence_interval} n={nf.n_tasks}")
        else:
            typer.echo(
                "--compare without --aa or --noise-floor would publish a delta with nothing to "
                "judge it against; beats_noise_floor would be None. Re-run with --aa."
            )
            raise SystemExit(1)

        typer.echo(f"Control arm: {control_arm}...")
        run_control = asyncio.run(_runner(control_arm).run_suite(run_id=f"{control_arm}-run", k=runs))
        typer.echo(f"Treatment arm: {treatment_arm}...")
        run_treatment = asyncio.run(_runner(treatment_arm).run_suite(run_id=f"{treatment_arm}-run", k=runs))

        comp = StatisticalAnalyzer.compare_runs(run_control, run_treatment, noise_floor=nf)
        report_run = run_treatment
        control_for_report: BenchmarkRun | None = run_control
    else:
        runner = _runner("single_shot")
        run_a = asyncio.run(runner.run_suite(run_id="run-pass-1", k=runs))
        control_for_report = None

        if aa:
            typer.echo("Running second pass for A/A noise floor calibration...")
            run_b = asyncio.run(runner.run_suite(run_id="run-pass-2", k=runs))
            nf = StatisticalAnalyzer.compute_noise_floor(run_a, run_b)
            comp = StatisticalAnalyzer.compare_runs(run_a, run_b, noise_floor=nf)
            typer.echo(
                f"A/A Calibration mean_delta: {nf.mean_delta:.3f}, "
                f"beats_noise_floor: {comp.beats_noise_floor}"
            )
        report_run = run_a

    if output.endswith(".json"):
        report_content = BenchmarkReporter.render_json(
            report_run, noise_floor=nf, comparison=comp, control=control_for_report
        )
    else:
        report_content = BenchmarkReporter.render_markdown(
            report_run, noise_floor=nf, comparison=comp, control=control_for_report
        )

    out_file = Path(output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_content)

    pass_rate = StatisticalAnalyzer.compute_pass_rate(report_run)
    typer.echo(f"Benchmark complete! Pass rate: {pass_rate:.1%}. Report written to {output}")
    if comp is not None and control_for_report is not None:
        verdict = BenchmarkReporter.verdict(report_run, control_for_report, comp)
        typer.echo(verdict)


@dataclass
class ExportOutcome:
    ledger: list[str]
    #: `SFTSample` or `DPOSample` objects, ready to serialize — empty when refused or nothing
    #: was eligible.
    samples: list[object]
    refused: bool = False


async def _do_export(
    *,
    format_: str,
    trajectory_db: str,
    spdx_license: str | None,
    redact_patterns: list[str],
    include_reasoning: bool,
) -> ExportOutcome:
    from sagiha.adapters.tools.builtins import BUILTIN_SCHEMAS, TOOL_DESCRIPTIONS
    from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
    from sagiha.domain.content import ToolSchema
    from sagiha.domain.trajectory import RunRecord, TrajectoryStep
    from sagiha.outer_loop.export.dpo import export_dpo_pairs
    from sagiha.outer_loop.export.eligibility import RunEligibility, assess
    from sagiha.outer_loop.export.license import is_export_permitted
    from sagiha.outer_loop.export.sft import export_sft_samples

    ledger: list[str] = []
    if not is_export_permitted(spdx_license):
        ledger.append(f"REFUSED: export requires an allowlisted SPDX license, got {spdx_license!r}")
        return ExportOutcome(ledger=ledger, samples=[], refused=True)

    tool_schemas = tuple(
        ToolSchema(name=name, description=TOOL_DESCRIPTIONS[name], parameters=BUILTIN_SCHEMAS[name])
        for name in sorted(BUILTIN_SCHEMAS)
    )
    store = SQLiteTrajectoryStore(trajectory_db)
    records: list[RunRecord] = await store.list_runs()
    ledger.append(f"{len(records)} run(s) in {trajectory_db}")

    steps_by_run: dict[str, list[TrajectoryStep]] = {}
    eligibility_by_run: dict[str, RunEligibility] = {}
    for record in records:
        steps = await store.steps_for_run(record.run_id)
        events = await store.events_for_run(record.run_id)
        steps_by_run[record.run_id] = steps
        elig = assess(record, steps, events)
        eligibility_by_run[record.run_id] = elig
        if elig.eligible:
            ledger.append(f"  eligible {record.run_id}")
        else:
            ledger.append(f"  excluded {record.run_id}: {', '.join(elig.reasons())}")

    if format_ == "sft":
        all_samples: list[object] = []
        total_hits = 0
        for record in records:
            elig = eligibility_by_run[record.run_id]
            if not elig.eligible:
                continue
            samples, hits = await export_sft_samples(
                record=record,
                steps=steps_by_run[record.run_id],
                tool_schemas=tool_schemas,
                admitted=bool(elig.admitted),
                redact_patterns=redact_patterns,
                include_reasoning=include_reasoning,
            )
            all_samples.extend(samples)
            total_hits += hits
        ledger.append(f"SFT: {len(all_samples)} sample(s), {total_hits} redaction hit(s)")
        return ExportOutcome(ledger=ledger, samples=all_samples)

    pairs, hits = await export_dpo_pairs(
        records=records,
        steps_by_run=steps_by_run,
        eligibility_by_run=eligibility_by_run,
        tool_schemas=tool_schemas,
        redact_patterns=redact_patterns,
    )
    ledger.append(f"DPO: {len(pairs)} pair(s), {hits} redaction hit(s)")
    return ExportOutcome(ledger=ledger, samples=list(pairs))


@app.command()
def export(
    format_: str = typer.Option("sft", "--format", help="Export format: 'sft' or 'dpo'"),
    min_gate: str = typer.Option(
        "admitted", "--min-gate", help="Eligibility floor (only 'admitted' is supported today)"
    ),
    trajectory_db: str = typer.Option(".sagiha/trajectories.db", "--trajectory-db"),
    out: str = typer.Option("data/", "--out", "-o", help="Output directory for the JSONL file"),
    spdx_license: str | None = typer.Option(
        None, "--spdx-license", help="SPDX identifier of the exported repo (fails closed if omitted)"
    ),
    include_reasoning: bool = typer.Option(
        False, "--include-reasoning", help="Include reasoning blocks (provider-policy permitting)"
    ),
) -> None:
    """Export admitted, replay-verified, untainted, in-budget trajectories as SFT or DPO JSONL.

    Prints an eligibility ledger — how many runs, and why each excluded run was excluded.
    Honest negatives are deliverables: an export that finds nothing eligible says so, rather
    than emitting an empty file silently.
    """
    import json

    if format_ not in ("sft", "dpo"):
        typer.echo(f"Unknown --format {format_!r}; expected 'sft' or 'dpo'")
        raise SystemExit(2)
    if min_gate != "admitted":
        typer.echo(f"Unsupported --min-gate {min_gate!r}; only 'admitted' is implemented today")
        raise SystemExit(2)

    redact_patterns = TelemetryConfig().redact_patterns
    outcome = asyncio.run(
        _do_export(
            format_=format_,
            trajectory_db=trajectory_db,
            spdx_license=spdx_license,
            redact_patterns=redact_patterns,
            include_reasoning=include_reasoning,
        )
    )

    for line in outcome.ledger:
        typer.echo(line)

    if outcome.refused:
        raise SystemExit(1)
    if not outcome.samples:
        typer.echo("No eligible samples exported.")
        raise SystemExit(0)

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{format_}.jsonl"
    with out_file.open("w", encoding="utf-8") as f:
        for sample in outcome.samples:
            f.write(json.dumps(sample.model_dump(mode="json")) + "\n")  # type: ignore[attr-defined]
    typer.echo(f"Wrote {len(outcome.samples)} sample(s) to {out_file}")
    raise SystemExit(0)


if __name__ == "__main__":
    app()
