"""Live smoke test against a real local OpenAI-compatible endpoint (B2b).

Skips when nothing is listening on :11434; hard-fails when
AETHER_REQUIRE_LIVE_MODEL=1 promises one is there. Not part of the deterministic
conformance suite — see tests/live_support.py.
"""

from __future__ import annotations

import pytest
from tests.live_support import LOCAL_BASE_URL, LOCAL_MODEL, require_live_model

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.domain.model_io import ModelMessage, ModelRequest, StopEvent
from aether.domain.taint import Provenance, TaintSpan


@pytest.mark.live
async def test_local_endpoint_streams_a_real_completion() -> None:
    require_live_model()

    from datetime import UTC, datetime

    from aether.domain.ids import SpanId

    provider = OpenAICompatibleProvider(LOCAL_BASE_URL, LOCAL_MODEL)
    request = ModelRequest(
        model=LOCAL_MODEL,
        messages=(
            ModelMessage(
                role="user",
                spans=(
                    TaintSpan(
                        span_id=SpanId("s1"),
                        label=Provenance.OPERATOR,
                        text="Say hello in one word.",
                        source="live_smoke_test",
                        created_at=datetime.now(UTC),
                    ),
                ),
            ),
        ),
        max_tokens=16,
    )

    events = [event async for event in provider.stream(request)]

    assert isinstance(events[-1], StopEvent)
    assert events[-1].reason != "provider_error"
