"""FallbackModelAdapter — composite ModelProvider that executes an ordered fallback chain of providers."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Final

from sagiha.adapters.model.openai import OpenAIModelError
from sagiha.domain.content import Message, ModelRequest
from sagiha.domain.trajectory import StreamEvent
from sagiha.ports.model import ModelProvider

logger = logging.getLogger(__name__)

PORT_VERSION: Final = 1


class FallbackModelAdapter(ModelProvider):
    """Composite ModelProvider executing an ordered fallback chain of model providers.

    If a primary provider fails due to rate limits, availability, or HTTP errors,
    calls fail over transparently to subsequent providers in order.
    """

    def __init__(self, providers: list[ModelProvider]) -> None:
        if not providers:
            raise ValueError("FallbackModelAdapter requires at least one ModelProvider")
        self._providers = providers

    @property
    def providers(self) -> list[ModelProvider]:
        """Return the underlying list of providers in failover order."""
        return list(self._providers)

    async def complete(self, request: ModelRequest) -> Message:
        last_exception: Exception | None = None
        for i, provider in enumerate(self._providers):
            try:
                return await provider.complete(request)
            except Exception as exc:
                logger.warning(
                    f"ModelProvider candidate {i} ({provider}) failed: {exc}. Trying fallback provider..."
                )
                last_exception = exc

        raise OpenAIModelError(
            f"All {len(self._providers)} fallback model providers failed. Last error: {last_exception}"
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        """Streaming is deferred; raises NotImplementedError."""
        raise NotImplementedError("Streaming is deferred; use complete()")
