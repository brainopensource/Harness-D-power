"""v2-S7f in-place repair loop — `RunLoop._step_phase` extraction + repair wrapper.

Uses a scripted `Evaluator` (queued `GateReport`s) rather than the real `GateEvaluator`, so
these tests exercise the repair loop's control flow, event emission, and prompt content in
isolation from gate-evaluation correctness — already covered by `test_sprint3a_e2e.py`.
"""

from __future__ import annotations

import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from sagiha.agency.run_loop import RunLoop, make_task, render_repair_prompt
from sagiha.composition import build_kernel
from sagiha.domain.config import (
    Config,
    GovernorConfig,
    ModelConfig,
    RepairConfig,
    SandboxConfig,
    TelemetryConfig,
    WorkspaceConfig,
)
from sagiha.domain.content import Message, ModelRequest, TextBlock
from sagiha.domain.control import RunContext
from sagiha.domain.events import Event, GateEvaluated, RepairAbandoned, RepairAttemptStarted
from sagiha.domain.trajectory import Completion, StreamEvent, TokenUsage
from sagiha.domain.work import CriterionResult, GateReport, RepairContext


def _git_init(repo: Path) -> None:
    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)

    run("init", "-q")
    run("config", "user.email", "test@example.com")
    run("config", "user.name", "Test")
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-q", "-m", "base")


class _EndsTurnImmediately:
    """Never calls a tool — every `_step_phase` is exactly one model call."""

    def __init__(self) -> None:
        self.call_count = 0

    async def complete(self, request: ModelRequest) -> Completion:
        self.call_count += 1
        return Completion(
            message=Message(role="assistant", content=[TextBlock(text=f"turn {self.call_count}")]),
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            model="test",
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


class _ScriptedEvaluator:
    """Returns queued `GateReport`s in order, one per `evaluate()` call. Raises if exhausted,
    so a test that calls this more times than expected fails loudly rather than reusing the
    last report and masking a repair-loop bug."""

    def __init__(self, reports: list[GateReport]) -> None:
        self._reports = list(reports)
        self.call_count = 0

    async def evaluate(self, task: object, ctx: object) -> GateReport:
        self.call_count += 1
        if not self._reports:
            raise AssertionError("_ScriptedEvaluator exhausted — evaluate() called more than scripted")
        return self._reports.pop(0)


_FAILING = GateReport(
    criteria=(
        CriterionResult(description="t", check="pytest -q", passed=False, required=True, output="E: boom"),
    ),
    tests_unmodified=True,
    diff_within_bounds=True,
    no_new_suppressions=True,
)
_PASSING = GateReport(
    criteria=(CriterionResult(description="t", check="pytest -q", passed=True, required=True, output=""),),
    tests_unmodified=True,
    diff_within_bounds=True,
    no_new_suppressions=True,
)


def _build_loop(
    tmp_path: Path,
    *,
    evaluator: _ScriptedEvaluator,
    repair: RepairConfig,
    model: _EndsTurnImmediately,
    governor: GovernorConfig | None = None,
) -> tuple[RunLoop, RunContext]:
    ws = tmp_path / "fixture"
    ws.mkdir()
    _git_init(ws)
    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(ws)),
        telemetry=TelemetryConfig(trajectory_db=str(tmp_path / "traj.db")),
        sandbox=SandboxConfig(runtime="subprocess"),
        governor=governor or GovernorConfig(),
    )
    kernel = build_kernel(config, cassette_path=str(cassette_path))
    loop = RunLoop(
        model_provider=model,  # type: ignore[arg-type]
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        evaluator=evaluator,  # type: ignore[arg-type]
        max_steps=5,
        workspace=kernel.workspace,
        repair=repair,
    )
    ctx = RunContext(
        run_id="repair-test",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    return loop, ctx


async def _collect_events(bus: object) -> list[Event]:
    events: list[Event] = []

    async def _on_event(event: Event) -> None:
        events.append(event)

    bus.subscribe_observer(_on_event)  # type: ignore[attr-defined]
    return events


@pytest.mark.asyncio
async def test_repair_reenters_on_failed_gate(tmp_path: Path) -> None:
    evaluator = _ScriptedEvaluator([_FAILING, _PASSING])
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(
        tmp_path, evaluator=evaluator, repair=RepairConfig(enabled=True, max_attempts=3), model=model
    )
    events = await _collect_events(loop._bus)  # type: ignore[attr-defined]
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    assert result.gate_report.admitted is True
    assert evaluator.call_count == 2
    assert model.call_count == 2
    gate_events = [e for e in events if isinstance(e, GateEvaluated)]
    assert [e.attempt for e in gate_events] == [1, 2]


@pytest.mark.asyncio
async def test_repair_stops_on_admitted(tmp_path: Path) -> None:
    evaluator = _ScriptedEvaluator([_PASSING])
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(
        tmp_path, evaluator=evaluator, repair=RepairConfig(enabled=True, max_attempts=3), model=model
    )
    events = await _collect_events(loop._bus)  # type: ignore[attr-defined]
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    assert result.gate_report.admitted is True
    assert evaluator.call_count == 1
    assert not [e for e in events if isinstance(e, RepairAttemptStarted)]


@pytest.mark.asyncio
async def test_repair_respects_max_attempts(tmp_path: Path) -> None:
    always_failing = [
        GateReport(
            criteria=(
                CriterionResult(
                    description="t", check="pytest -q", passed=False, required=True, output=f"fail {i}"
                ),
            ),
            tests_unmodified=True,
            diff_within_bounds=True,
            no_new_suppressions=True,
        )
        for i in range(4)
    ]
    evaluator = _ScriptedEvaluator(always_failing)
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(
        tmp_path, evaluator=evaluator, repair=RepairConfig(enabled=True, max_attempts=3), model=model
    )
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    assert result.gate_report.admitted is False
    assert evaluator.call_count == 4  # max_attempts + 1


@pytest.mark.asyncio
async def test_repair_no_progress_abandons(tmp_path: Path) -> None:
    # Identical failure signature (same failed gates, same output) on attempts 1 and 2.
    evaluator = _ScriptedEvaluator([_FAILING, _FAILING, _PASSING])
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(
        tmp_path,
        evaluator=evaluator,
        repair=RepairConfig(enabled=True, max_attempts=3, stop_on_no_progress=True),
        model=model,
    )
    events = await _collect_events(loop._bus)  # type: ignore[attr-defined]
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    assert result.gate_report.admitted is False
    assert evaluator.call_count == 2  # abandoned before a 3rd evaluation
    abandoned = [e for e in events if isinstance(e, RepairAbandoned)]
    assert len(abandoned) == 1
    assert abandoned[0].reason == "no_progress"


@pytest.mark.asyncio
async def test_repair_prompt_contains_failure_output() -> None:
    repair = RepairContext(
        attempt=2,
        failed_criteria=(
            CriterionResult(
                description="t", check="pytest -q", passed=False, required=True, output="AssertionError: boom"
            ),
        ),
        failed_gates=("tests_unmodified",),
        truncated_output="AssertionError: boom",
    )
    prompt = render_repair_prompt(repair)
    assert "repair attempt 2" in prompt
    assert "AssertionError: boom" in prompt
    assert "tests_unmodified" in prompt
    assert "Do not modify test files" in prompt


@pytest.mark.asyncio
async def test_repair_disabled_matches_legacy(tmp_path: Path) -> None:
    """`RepairConfig(enabled=False)` (the default) must behave byte-identically to the
    pre-S7f loop: exactly one gate evaluation, no repair turn, regardless of admission."""
    evaluator = _ScriptedEvaluator([_FAILING])
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(tmp_path, evaluator=evaluator, repair=RepairConfig(enabled=False), model=model)
    events = await _collect_events(loop._bus)  # type: ignore[attr-defined]
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    assert result.gate_report.admitted is False
    assert evaluator.call_count == 1
    assert model.call_count == 1
    assert not [e for e in events if isinstance(e, (RepairAttemptStarted, RepairAbandoned))]
    gate_events = [e for e in events if isinstance(e, GateEvaluated)]
    assert len(gate_events) == 1
    assert gate_events[0].attempt == 1


@pytest.mark.asyncio
async def test_repair_preserves_stable_prefix(tmp_path: Path) -> None:
    evaluator = _ScriptedEvaluator([_FAILING, _PASSING])
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(
        tmp_path, evaluator=evaluator, repair=RepairConfig(enabled=True, max_attempts=3), model=model
    )
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    digests = {step.prefix_digest for step in result.steps}
    assert len(digests) == 1


@pytest.mark.asyncio
async def test_repair_does_not_run_on_budget_park(tmp_path: Path) -> None:
    # Gate evaluation is unconditional (legacy semantics, unchanged by S7f) — only the
    # *repair attempt* must not fire when the run parked before ever taking a step.
    evaluator = _ScriptedEvaluator([_FAILING])
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(
        tmp_path,
        evaluator=evaluator,
        repair=RepairConfig(enabled=True, max_attempts=3),
        model=model,
        governor=GovernorConfig(max_spend_usd_per_run=0.0),
    )
    events = await _collect_events(loop._bus)  # type: ignore[attr-defined]
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    assert result.parked is True
    assert evaluator.call_count == 1
    assert model.call_count == 0
    assert not [e for e in events if isinstance(e, RepairAttemptStarted)]


@pytest.mark.asyncio
async def test_repair_does_not_run_on_stuck(tmp_path: Path) -> None:
    class _RepeatsSameToolCall:
        async def complete(self, request: ModelRequest) -> Completion:
            from sagiha.domain.content import ToolUseBlock

            return Completion(
                message=Message(
                    role="assistant",
                    content=[
                        ToolUseBlock(call_id="c1", tool_name="run_command", arguments={"command": ["true"]})
                    ],
                ),
                usage=TokenUsage(input_tokens=1, output_tokens=1),
                model="test",
            )

        async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError
            yield  # pragma: no cover

    evaluator = _ScriptedEvaluator([_PASSING])  # exactly one post-loop evaluation
    ws = tmp_path / "fixture"
    ws.mkdir()
    _git_init(ws)
    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(ws)),
        telemetry=TelemetryConfig(trajectory_db=str(tmp_path / "traj.db")),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    kernel = build_kernel(config, cassette_path=str(cassette_path))
    loop = RunLoop(
        model_provider=_RepeatsSameToolCall(),  # type: ignore[arg-type]
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        evaluator=evaluator,  # type: ignore[arg-type]
        max_steps=10,
        workspace=kernel.workspace,
        repair=RepairConfig(enabled=True, max_attempts=3),
    )
    ctx = RunContext(
        run_id="repair-stuck",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=5.0,
    )
    task = make_task("fix it", checks=["true"], task_id="t1")

    result = await loop.run(task, ctx)

    assert result.gate_report.admitted is True  # gate still evaluates once, per legacy semantics
    assert evaluator.call_count == 1


@pytest.mark.asyncio
async def test_repair_turn_is_trusted(tmp_path: Path) -> None:
    evaluator = _ScriptedEvaluator([_FAILING, _PASSING])
    model = _EndsTurnImmediately()
    loop, ctx = _build_loop(
        tmp_path, evaluator=evaluator, repair=RepairConfig(enabled=True, max_attempts=3), model=model
    )
    task = make_task("fix it", checks=["true"], task_id="t1")

    await loop.run(task, ctx)

    assembler = loop._assembler  # type: ignore[attr-defined]
    assert assembler is not None
    assert not any(ex.tainted for ex in assembler.exchanges)
