"""DefaultPolicyEngine.authorize() — the I11 binding rule."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aether.domain.ids import RunId, SpanId
from aether.domain.taint import Provenance, TaintSpan
from aether.kernel.policy import DefaultPolicyEngine
from aether.ports.policy_engine import Decision, EffectRequest


def _span(label: Provenance) -> TaintSpan:
    return TaintSpan(span_id=SpanId("s1"), label=label, text="x", source="test", created_at=datetime.now(UTC))


def _request(*, widens: bool, spans: tuple[TaintSpan, ...]) -> EffectRequest:
    return EffectRequest(
        run_id=RunId("r1"),
        effect_class="shell",
        descriptor="rm -rf /",
        justifying_spans=spans,
        widens_capability=widens,
    )


@pytest.mark.parametrize("label", [Provenance.UNTRUSTED_EXTERNAL, Provenance.UNTRUSTED_DERIVED])
async def test_widening_request_justified_by_untrusted_span_fails_closed(label: Provenance) -> None:
    engine = DefaultPolicyEngine()
    decision = await engine.authorize(_request(widens=True, spans=(_span(label),)))
    assert decision.decision is Decision.ASK_FAIL_CLOSED


async def test_widening_request_with_any_untrusted_span_among_trusted_ones_fails_closed() -> None:
    engine = DefaultPolicyEngine()
    spans = (_span(Provenance.TRUSTED_SYSTEM), _span(Provenance.UNTRUSTED_EXTERNAL))
    decision = await engine.authorize(_request(widens=True, spans=spans))
    assert decision.decision is Decision.ASK_FAIL_CLOSED


async def test_widening_request_justified_only_by_trusted_spans_grants() -> None:
    engine = DefaultPolicyEngine()
    spans = (_span(Provenance.TRUSTED_SYSTEM), _span(Provenance.OPERATOR))
    decision = await engine.authorize(_request(widens=True, spans=spans))
    assert decision.decision is Decision.GRANT


async def test_non_widening_request_grants_even_with_untrusted_spans() -> None:
    engine = DefaultPolicyEngine()
    decision = await engine.authorize(_request(widens=False, spans=(_span(Provenance.UNTRUSTED_EXTERNAL),)))
    assert decision.decision is Decision.GRANT
