"""Cost accounting and the spend cap (Sprint 3.5, A4).

The defect this closes: `composition.py` wrote prompt/completion tokens into
`Actuals` and **never wrote `usd_micros`**, so a run seeded with a dollar
ceiling compared spend against a field that was always zero. The cap could not
fire. These tests are the negative half — they drive spend *past* a ceiling and
assert the dispatcher refuses.
"""

from __future__ import annotations

import pytest

from aether.domain.budget import Actuals, BudgetDims
from aether.domain.ids import RunId
from aether.kernel.governor import ResourceGovernor
from aether.measurement.pricing import (
    UNKNOWN_PRICE,
    ModelPrice,
    cost_usd_micros,
    is_free_endpoint,
    price_for,
    priced,
)
from aether.ports.resource_governor import ReservationDenied


def test_a_priced_model_costs_what_the_rate_card_says() -> None:
    # deepseek-v4-flash: 270_000 µ$/Mtok prompt, 1_100_000 µ$/Mtok completion.
    cost = cost_usd_micros("deepseek/deepseek-v4-flash", 1_000_000, 1_000_000)

    assert cost == 270_000 + 1_100_000


def test_cost_rounds_up_because_a_cap_that_rounds_down_leaks() -> None:
    cost = cost_usd_micros("deepseek/deepseek-v4-flash", 1, 0)

    assert cost == 1  # 0.27 µ$ rounded up, not floored to 0


def test_an_unknown_model_is_expensive_not_free() -> None:
    """A model with no rate card must trip a cap early and loudly. Pricing it
    at zero is how an unbudgeted run looks affordable right up to the invoice."""
    assert price_for("some/model-nobody-priced") is UNKNOWN_PRICE
    assert cost_usd_micros("some/model-nobody-priced", 1000, 1000) > 0


@pytest.mark.parametrize(
    "base_url", ["http://localhost:11434/v1", "http://127.0.0.1:11434/v1", "http://0.0.0.0:8080/v1"]
)
def test_a_local_endpoint_bills_nothing(base_url: str) -> None:
    assert is_free_endpoint(base_url)
    assert cost_usd_micros("qwen2.5:1.5b", 100_000, 100_000, base_url=base_url) == 0


def test_a_remote_endpoint_is_not_free_even_for_an_unknown_model() -> None:
    assert not is_free_endpoint("https://openrouter.ai/api/v1")
    assert cost_usd_micros("qwen2.5:1.5b", 1000, 1000, base_url="https://openrouter.ai/api/v1") > 0


def test_provider_reported_cost_beats_a_computed_one() -> None:
    """A measured number always wins over an estimate — `measurement.md` §6."""
    reported = BudgetDims(prompt_tokens=1000, completion_tokens=1000, usd_micros=42)

    assert priced("deepseek/deepseek-v4-flash", reported).usd_micros == 42


def test_priced_fills_in_usd_when_the_provider_reported_none() -> None:
    dims = priced("deepseek/deepseek-v4-flash", BudgetDims(prompt_tokens=1_000_000))

    assert dims.usd_micros == 270_000
    assert dims.prompt_tokens == 1_000_000  # token counts survive untouched


# ------------------------------------------------------------- the real cap


async def test_a_dollar_ceiling_actually_stops_the_run() -> None:
    """**The gate this sprint exists for.** Spend past the ceiling and the
    governor must refuse — with `usd_micros` unwritten this test passed
    vacuously because every reservation cost zero."""
    governor = ResourceGovernor()
    run_id = RunId("paid-run")
    governor.seed_run_budget(run_id, BudgetDims(usd_micros=200_000))  # $0.20

    granted = 0
    denied: ReservationDenied | None = None
    for _ in range(10):
        # ~74k prompt + 20k completion tokens on deepseek-v4-flash ≈ $0.042
        cost = BudgetDims(usd_micros=cost_usd_micros("deepseek/deepseek-v4-flash", 74_000, 20_000))
        lease = await governor.reserve(run_id, cost)
        if isinstance(lease, ReservationDenied):
            denied = lease
            break
        granted += 1
        await governor.commit(lease.lease_id, Actuals(dims=cost))

    assert denied is not None, "the $0.20 ceiling never fired — the cap is not enforced"
    assert granted < 10
    spent = await governor.spent(run_id)
    assert spent.usd_micros <= 200_000


async def test_an_unpriced_model_trips_the_cap_rather_than_slipping_under_it() -> None:
    governor = ResourceGovernor()
    run_id = RunId("paid-run")
    governor.seed_run_budget(run_id, BudgetDims(usd_micros=200_000))

    cost = BudgetDims(usd_micros=cost_usd_micros("some/unpriced-model", 100_000, 50_000))
    lease = await governor.reserve(run_id, cost)

    assert isinstance(lease, ReservationDenied)


def test_the_rate_card_is_integer_micro_usd() -> None:
    """Float budget arithmetic is banned by type (I3). The rate card is the one
    place a decimal price could sneak in, so it is integers per million."""
    for model, price in [("deepseek/deepseek-v4-flash", price_for("deepseek/deepseek-v4-flash"))]:
        assert isinstance(price, ModelPrice), model
        assert isinstance(price.prompt_usd_micros_per_mtok, int)
        assert isinstance(price.completion_usd_micros_per_mtok, int)


# ------------------------------------- the wiring, not just the arithmetic


def _sse(*chunks: dict[str, object]) -> bytes:
    import json as _json

    body = "".join(f"data: {_json.dumps(c)}\n\n" for c in chunks)
    return (body + "data: [DONE]\n\n").encode()


async def _dispatch_one_model_call(base_url: str, run_id: RunId, governor: ResourceGovernor):  # noqa: ANN202
    """One real model effect through the real composition wiring."""
    import httpx
    import respx

    from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
    from aether.composition import build_dispatcher
    from aether.domain.ids import SpanId
    from aether.domain.model_io import ModelMessage, ModelRequest
    from aether.domain.taint import Provenance, TaintSpan
    from aether.ports.policy_engine import EffectRequest

    provider = OpenAICompatibleProvider(base_url, "deepseek/deepseek-v4-flash")
    dispatcher = build_dispatcher(None, None, provider, None, None, governor, base_url)  # type: ignore[arg-type]

    from datetime import UTC, datetime

    request = ModelRequest(
        model="deepseek/deepseek-v4-flash",
        messages=(
            ModelMessage(
                role="user",
                spans=(
                    TaintSpan(
                        span_id=SpanId("s1"),
                        label=Provenance.OPERATOR,
                        text="hello",
                        source="test",
                        created_at=datetime.now(UTC),
                    ),
                ),
            ),
        ),
        max_tokens=16,
    )

    with respx.mock:
        respx.post(f"{base_url}/chat/completions").mock(
            return_value=httpx.Response(
                200,
                content=_sse(
                    {"choices": [{"delta": {"content": "hi"}, "finish_reason": None}]},
                    {"usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0}, "choices": []},
                    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                ),
            )
        )
        return await dispatcher.dispatch(
            EffectRequest(
                run_id=run_id,  # type: ignore[arg-type]
                effect_class="model",  # type: ignore[arg-type]
                descriptor=request.model_dump_json(),
                justifying_spans=(),
                widens_capability=False,
            ),
            BudgetDims(usd_micros=1_000_000, prompt_tokens=2_000_000),
        )


async def test_a_real_model_dispatch_debits_dollars_not_just_tokens() -> None:
    """End to end through `composition.build_adapter_table`: the ledger must
    show dollars after a paid call, or the cap has nothing to compare against."""
    governor = ResourceGovernor()
    run_id = RunId("paid")

    outcome = await _dispatch_one_model_call("https://openrouter.ai/api/v1", run_id, governor)

    assert outcome.status == "ok"
    spent = await governor.spent(run_id)
    assert spent.prompt_tokens == 1_000_000
    assert spent.usd_micros == 270_000  # the rate card, applied by the adapter closure


async def test_a_local_dispatch_debits_no_dollars() -> None:
    governor = ResourceGovernor()
    run_id = RunId("free")

    await _dispatch_one_model_call("http://127.0.0.1:11434/v1", run_id, governor)

    spent = await governor.spent(run_id)
    assert spent.prompt_tokens == 1_000_000
    assert spent.usd_micros == 0  # local endpoints bill nothing


async def test_a_dollar_only_ceiling_does_not_deny_on_other_dimensions() -> None:
    """Found by tier 2 of the Sprint 3.5 ladder: seeding a $0.20 cap left every
    other dimension at zero, so the first node — which asked only for
    wall-clock — was refused before a cent was spent. A ceiling constrains what
    it names."""
    governor = ResourceGovernor()
    run_id = RunId("paid")
    governor.seed_run_budget(run_id, BudgetDims(usd_micros=200_000))

    lease = await governor.reserve(run_id, BudgetDims(wall_clock_ms=120_000, prompt_tokens=4_000))

    assert not isinstance(lease, ReservationDenied)


async def test_the_named_dimension_is_still_enforced_exactly() -> None:
    governor = ResourceGovernor()
    run_id = RunId("paid")
    governor.seed_run_budget(run_id, BudgetDims(usd_micros=200_000))

    first = await governor.reserve(run_id, BudgetDims(usd_micros=150_000, wall_clock_ms=999_999))
    assert not isinstance(first, ReservationDenied)
    await governor.commit(first.lease_id, Actuals(dims=BudgetDims(usd_micros=150_000)))

    second = await governor.reserve(run_id, BudgetDims(usd_micros=100_000))

    assert isinstance(second, ReservationDenied)
    assert "usd_micros" in second.rationale
