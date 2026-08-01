"""Unit tests for FallbackModelAdapter and role-level failover."""

from __future__ import annotations

from typing import Any

import pytest

from sagiha.adapters.model.fallback import FallbackModelAdapter, drop_reasoning_whole_exchange
from sagiha.adapters.model.openai import OpenAIModelError
from sagiha.composition import build_kernel
from sagiha.domain.config import SandboxConfig, Config, ModelConfig
from sagiha.domain.content import Message, ModelRequest, ReasoningBlock, TextBlock
from sagiha.domain.trajectory import Completion, TokenUsage
from sagiha.ports.model import ModelProvider


class MockModelProvider(ModelProvider):
    """Mock ModelProvider for testing fallback chains."""

    def __init__(self, name: str, should_fail: bool = False, fail_message: str = "Error") -> None:
        self.name = name
        self.should_fail = should_fail
        self.fail_message = fail_message
        self.call_count = 0
        self.last_request: ModelRequest | None = None

    async def complete(self, request: ModelRequest) -> Completion:
        self.call_count += 1
        self.last_request = request
        if self.should_fail:
            raise OpenAIModelError(self.fail_message)
        return Completion(
            message=Message(role="assistant", content=[TextBlock(text=f"Response from {self.name}")]),
            usage=TokenUsage(input_tokens=0, output_tokens=0),
            model="test",
        )

    async def stream(self, request: ModelRequest) -> Any:
        raise NotImplementedError()


@pytest.mark.asyncio
async def test_fallback_success_on_primary() -> None:
    p1 = MockModelProvider("primary", should_fail=False)
    p2 = MockModelProvider("fallback1", should_fail=False)

    adapter = FallbackModelAdapter([p1, p2], labels=["primary", "fallback1"], backoff_retries=0)
    req = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    res = await adapter.complete(req)
    assert res.message.content[0].text == "Response from primary"
    assert p1.call_count == 1
    assert p2.call_count == 0


@pytest.mark.asyncio
async def test_fallback_failover_to_secondary_with_backoff_on_rate_limit() -> None:
    p1 = MockModelProvider("primary", should_fail=True, fail_message="HTTP 429 Rate Limit")
    p2 = MockModelProvider("fallback1", should_fail=False)

    adapter = FallbackModelAdapter(
        [p1, p2],
        labels=["primary", "fallback1"],
        backoff_retries=2,
        backoff_base_s=0.001,
    )
    adapter.bind_run("run-1")
    req = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    res = await adapter.complete(req)
    assert res.message.content[0].text == "Response from fallback1"
    # Primary is retried with backoff before hop.
    assert p1.call_count == 3
    assert p2.call_count == 1
    assert adapter.last_failover is not None
    assert adapter.last_failover.from_provider == "primary"
    assert adapter.last_failover.to_provider == "fallback1"
    assert adapter.last_failover.reasoning_dropped is True


@pytest.mark.asyncio
async def test_non_transient_fails_over_without_backoff() -> None:
    p1 = MockModelProvider("primary", should_fail=True, fail_message="Invalid API key")
    p2 = MockModelProvider("fallback1", should_fail=False)

    adapter = FallbackModelAdapter([p1, p2], labels=["a", "b"], backoff_retries=2, backoff_base_s=0.001)
    req = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])
    res = await adapter.complete(req)
    assert res.message.content[0].text == "Response from fallback1"
    assert p1.call_count == 1


@pytest.mark.asyncio
async def test_fallback_drops_reasoning_on_cross_provider_hop() -> None:
    p1 = MockModelProvider("primary", should_fail=True, fail_message="boom")
    p2 = MockModelProvider("fallback1", should_fail=False)
    adapter = FallbackModelAdapter([p1, p2], labels=["a", "b"], backoff_retries=0)
    req = ModelRequest(
        messages=[
            Message(
                role="assistant",
                content=[
                    ReasoningBlock(provider="a", opaque={"x": 1}, summary="secret"),
                    TextBlock(text="hi"),
                ],
            )
        ]
    )
    await adapter.complete(req)
    assert p2.last_request is not None
    assert not any(isinstance(b, ReasoningBlock) for b in p2.last_request.messages[0].content)


@pytest.mark.asyncio
async def test_fallback_all_fail_raises_error() -> None:
    p1 = MockModelProvider("p1", should_fail=True)
    p2 = MockModelProvider("p2", should_fail=True)

    adapter = FallbackModelAdapter([p1, p2], backoff_retries=0)
    req = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    with pytest.raises(OpenAIModelError, match="All 2 fallback model providers failed"):
        await adapter.complete(req)


def test_drop_reasoning_whole_exchange() -> None:
    req = ModelRequest(
        messages=[
            Message(
                role="assistant",
                content=[ReasoningBlock(provider="p", opaque={}, summary="s"), TextBlock(text="ok")],
            )
        ]
    )
    stripped = drop_reasoning_whole_exchange(req)
    assert len(stripped.messages[0].content) == 1
    assert isinstance(stripped.messages[0].content[0], TextBlock)


@pytest.mark.asyncio
async def test_build_kernel_with_tier_and_role_fallback() -> None:
    """tier0 in-tier chain + ModelConfig.fallback role hop to workhorse."""
    config = Config(
        model=ModelConfig(
            mode="live",
            active_tier="tier0",
            fallback="workhorse",
            roles={"execution": "tier0", "planning": "tier0", "compaction": "fast", "judge": "fast"},
        ),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    kernel = build_kernel(config, tier="tier0")
    assert isinstance(kernel.model_provider, FallbackModelAdapter)
    # tier0: 1 primary + 4 in-tier fallbacks; plus workhorse role-level hop.
    assert len(kernel.model_provider.providers) == 6
