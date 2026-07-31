"""H2/H2b proving tests: cost telemetry is live, and the governor enforces its limits.

Before PR-1b:
  * `record_spend()` was correct and **called from nowhere** in `src/`, so
    `remaining_budget()` always returned the full budget and the loop's budget break
    at `run_loop.py` was unreachable.
  * The loop emitted `TokenUsage(0, 0)` and `CostSummary(usd=0.0)` on every step.
  * `DefaultResourceGovernor.acquire()` minted a lease and enforced neither
    `max_concurrent_sandboxes` nor the spend limit — both constructor args were
    stored and never read (H2b).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import (
    Config,
    ModelConfig,
    PricingConfig,
    TelemetryConfig,
    WorkspaceConfig,
)
from sagiha.domain.content import Message, ModelRequest, ToolUseBlock
from sagiha.domain.control import RunContext
from sagiha.domain.trajectory import Completion, StreamEvent, TokenUsage
from sagiha.kernel.governor import ConcurrencyLimitError, DefaultResourceGovernor

# --------------------------------------------------------------------------- H2b


@pytest.mark.asyncio
async def test_acquire_enforces_max_concurrent_sandboxes() -> None:
    gov = DefaultResourceGovernor(max_concurrent_sandboxes=2)

    a = await gov.acquire("sandbox", "run-1")
    await gov.acquire("sandbox", "run-1")

    with pytest.raises(ConcurrencyLimitError):
        await gov.acquire("sandbox", "run-1")

    # Releasing frees the slot — the limit is a live count, not a high-water mark.
    await gov.release(a)
    await gov.acquire("sandbox", "run-2")


@pytest.mark.asyncio
async def test_concurrency_limit_is_per_kind_not_global() -> None:
    gov = DefaultResourceGovernor(max_concurrent_sandboxes=1)
    await gov.acquire("sandbox", "r")
    # A different kind is not competing for the sandbox pool.
    await gov.acquire("lsp", "r")


@pytest.mark.asyncio
async def test_acquire_refuses_when_the_run_is_out_of_budget() -> None:
    gov = DefaultResourceGovernor(max_spend_usd_per_run=1.0)
    await gov.record_spend("run-1", 1.0)

    with pytest.raises(ConcurrencyLimitError):
        await gov.acquire("sandbox", "run-1")


# ---------------------------------------------------------------------------- H2


@pytest.mark.asyncio
async def test_record_spend_reduces_remaining_budget() -> None:
    gov = DefaultResourceGovernor(max_spend_usd_per_run=5.0)
    assert await gov.remaining_budget("r") == 5.0
    await gov.record_spend("r", 2.0)
    assert await gov.remaining_budget("r") == 3.0


def test_pricing_config_computes_cost_from_usage() -> None:
    pricing = PricingConfig(usd_per_1m_input=3.0, usd_per_1m_output=15.0)
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert pricing.cost_usd(usage) == pytest.approx(18.0)


def test_local_tiers_are_free_by_default() -> None:
    """A local model costs nothing, and a default that invents a price would be a lie."""
    pricing = PricingConfig()
    assert pricing.cost_usd(TokenUsage(input_tokens=10_000, output_tokens=10_000)) == 0.0


def _git_init(repo: Path) -> None:
    import subprocess

    for args in (
        ("init", "-q"),
        ("config", "user.email", "t@e.com"),
        ("config", "user.name", "T"),
        ("add", "-A"),
        ("commit", "-q", "-m", "base"),
    ):
        subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)


class _CostlyProvider:
    """Reports real usage, so the ledger has something true to record."""

    def __init__(self, usage: TokenUsage) -> None:
        self._usage = usage
        self.calls = 0

    async def complete(self, request: ModelRequest) -> Completion:
        self.calls += 1
        # A tool call, so the loop keeps stepping and the budget break has a chance
        # to fire. A text-only reply ends the turn after one call and would make the
        # budget assertion vacuous.
        return Completion(
            message=Message(
                role="assistant",
                content=[
                    ToolUseBlock(
                        call_id=f"c{self.calls}",
                        tool_name="run_command",
                        arguments={"command": ["echo", str(self.calls)]},
                    )
                ],
            ),
            usage=self._usage,
            model="test-model",
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


def _loop(tmp_path: Path, provider: object, gov: DefaultResourceGovernor) -> tuple[RunLoop, Path]:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git_init(ws)
    cassette = tmp_path / "c.json"
    cassette.write_text("[]", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(ws)),
        telemetry=TelemetryConfig(trajectory_db=str(tmp_path / "t.db")),
        pricing=PricingConfig(usd_per_1m_input=1000.0, usd_per_1m_output=1000.0),
    )
    kernel = build_kernel(config, cassette_path=str(cassette))
    loop = RunLoop(
        model_provider=provider,  # type: ignore[arg-type]
        policy_engine=kernel.policy_engine,
        resource_governor=gov,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        evaluator=kernel.evaluator,
        max_steps=10,
        workspace=kernel.workspace,
        pricing=config.pricing,
    )
    return loop, ws


@pytest.mark.asyncio
async def test_budget_break_is_reachable_and_aborts_the_run(tmp_path: Path) -> None:
    """The break at `remaining_budget <= 0` was dead code until spend was recorded."""
    # 10k in + 10k out at $1000/1M = $0.02 per call, against a $0.01 cap.
    gov = DefaultResourceGovernor(max_spend_usd_per_run=0.01)
    provider = _CostlyProvider(TokenUsage(input_tokens=10_000, output_tokens=10_000))
    loop, _ = _loop(tmp_path, provider, gov)

    ctx = RunContext(
        run_id="budget-1",
        autonomy_level="interactive",
        workspace_root=str(tmp_path / "ws"),
        budget_remaining_usd=0.01,
    )
    await loop.run(make_task("goal", checks=["true"], task_id="budget-1"), ctx)

    # One call spends past the cap; the loop must stop rather than run to max_steps.
    assert provider.calls == 1, "budget break never fired — spend is not being recorded"
    assert await gov.remaining_budget("budget-1") == 0.0


@pytest.mark.asyncio
async def test_run_reports_real_tokens_and_nonzero_cost(tmp_path: Path) -> None:
    gov = DefaultResourceGovernor(max_spend_usd_per_run=100.0)
    provider = _CostlyProvider(TokenUsage(input_tokens=1_000, output_tokens=500))
    loop, ws = _loop(tmp_path, provider, gov)

    ctx = RunContext(
        run_id="cost-1",
        autonomy_level="interactive",
        workspace_root=str(ws),
        budget_remaining_usd=100.0,
    )
    result = await loop.run(make_task("goal", checks=["true"], task_id="cost-1"), ctx)

    step = result.steps[0]
    assert step.usage.input_tokens == 1_000
    assert step.usage.output_tokens == 500
    assert step.cost.usd > 0.0, "cost is still the fabricated 0.0"
    assert step.cost.model_calls == 1
    assert result.cost.usd == pytest.approx(step.cost.usd * result.cost.model_calls, rel=0.01)

    spent = 100.0 - await gov.remaining_budget("cost-1")
    assert spent > 0.0, "record_spend() is still called from nowhere"
