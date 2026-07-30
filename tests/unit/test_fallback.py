"""Unit tests for FallbackModelAdapter and tier-based failover."""

from __future__ import annotations

from typing import Any

import pytest

from sagiha.adapters.model.fallback import FallbackModelAdapter
from sagiha.adapters.model.openai import OpenAIModelError
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig
from sagiha.domain.content import Message, ModelRequest, TextBlock
from sagiha.ports.model import ModelProvider


class MockModelProvider(ModelProvider):
    """Mock ModelProvider for testing fallback chains."""

    def __init__(self, name: str, should_fail: bool = False, fail_message: str = "Error") -> None:
        self.name = name
        self.should_fail = should_fail
        self.fail_message = fail_message
        self.call_count = 0

    async def complete(self, request: ModelRequest) -> Message:
        self.call_count += 1
        if self.should_fail:
            raise OpenAIModelError(self.fail_message)
        return Message(role="assistant", content=[TextBlock(text=f"Response from {self.name}")])

    async def stream(self, request: ModelRequest) -> Any:
        raise NotImplementedError()


@pytest.mark.asyncio
async def test_fallback_success_on_primary() -> None:
    p1 = MockModelProvider("primary", should_fail=False)
    p2 = MockModelProvider("fallback1", should_fail=False)

    adapter = FallbackModelAdapter([p1, p2])
    req = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    res = await adapter.complete(req)
    assert res.content[0].text == "Response from primary"
    assert p1.call_count == 1
    assert p2.call_count == 0


@pytest.mark.asyncio
async def test_fallback_failover_to_secondary() -> None:
    p1 = MockModelProvider("primary", should_fail=True, fail_message="HTTP 429 Rate Limit")
    p2 = MockModelProvider("fallback1", should_fail=False)

    adapter = FallbackModelAdapter([p1, p2])
    req = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    res = await adapter.complete(req)
    assert res.content[0].text == "Response from fallback1"
    assert p1.call_count == 1
    assert p2.call_count == 1


@pytest.mark.asyncio
async def test_fallback_all_fail_raises_error() -> None:
    p1 = MockModelProvider("p1", should_fail=True)
    p2 = MockModelProvider("p2", should_fail=True)

    adapter = FallbackModelAdapter([p1, p2])
    req = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    with pytest.raises(OpenAIModelError, match="All 2 fallback model providers failed"):
        await adapter.complete(req)


@pytest.mark.asyncio
async def test_build_kernel_with_tier_fallbacks() -> None:
    config = Config(
        model=ModelConfig(
            mode="live",
            active_tier="tier0",
        )
    )
    kernel = build_kernel(config, tier="tier0")
    assert isinstance(kernel.model_provider, FallbackModelAdapter)
    assert len(kernel.model_provider.providers) == 5
