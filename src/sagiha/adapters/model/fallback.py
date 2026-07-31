"""FallbackModelAdapter — role-level failover with backoff-first economics.

See docs/03-contracts-and-models/frozen-run-state.md and Sprint v2-S3 PR-3.4.

The previous adapter blindly walked an ordered list of same-URL model names. Role-level
failover is different: the composition root binds a primary tier and an optional
`ModelConfig.fallback` tier, and this adapter:

1. Retries the current provider with short backoff on *transient* errors (rate limits,
   5xx) before giving up on it — backoff-first economics, not instant hop.
2. Emits `ProviderFailover` when moving to the next provider (checkpoint signal).
3. Drops reasoning blocks **whole-exchange** on any hop past the primary — cross-provider
   signed reasoning is not portable and a half-dropped block is a provider-rejected request.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Final

from sagiha.adapters.model.openai import OpenAIModelError
from sagiha.domain.content import ContentBlock, Message, ModelRequest, ReasoningBlock
from sagiha.domain.events import ProviderFailover
from sagiha.domain.trajectory import Completion, StreamEvent
from sagiha.kernel.bus import EventBus
from sagiha.ports.model import ModelProvider

logger = logging.getLogger(__name__)

PORT_VERSION: Final = 1

_TRANSIENT_MARKERS: Final[tuple[str, ...]] = (
    "429",
    "rate limit",
    "timeout",
    "503",
    "502",
    "unavailable",
    "overloaded",
)


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def drop_reasoning_whole_exchange(request: ModelRequest) -> ModelRequest:
    """Strip every `ReasoningBlock` from every message — whole-exchange, never half."""

    def _strip(blocks: list[ContentBlock]) -> list[ContentBlock]:
        return [b for b in blocks if not isinstance(b, ReasoningBlock)]

    messages = [
        Message(role=m.role, content=_strip(list(m.content))) if any(isinstance(b, ReasoningBlock) for b in m.content) else m
        for m in request.messages
    ]
    if messages == request.messages:
        return request
    return request.model_copy(update={"messages": messages})


class FallbackModelAdapter(ModelProvider):
    """Composite ModelProvider with backoff-first, role-level failover."""

    def __init__(
        self,
        providers: list[ModelProvider],
        *,
        labels: list[str] | None = None,
        bus: EventBus | None = None,
        backoff_retries: int = 2,
        backoff_base_s: float = 0.05,
    ) -> None:
        if not providers:
            raise ValueError("FallbackModelAdapter requires at least one ModelProvider")
        self._providers = providers
        self._labels = labels or [f"provider-{i}" for i in range(len(providers))]
        if len(self._labels) != len(providers):
            raise ValueError("labels length must match providers length")
        self._bus = bus
        self._backoff_retries = max(0, backoff_retries)
        self._backoff_base_s = backoff_base_s
        self._run_id: str | None = None
        #: Set when a failover hop occurs during the most recent `complete` call.
        self.last_failover: ProviderFailover | None = None

    def bind_run(self, run_id: str) -> None:
        """Attach the active run id so failover events correlate to a trajectory."""
        self._run_id = run_id

    @property
    def providers(self) -> list[ModelProvider]:
        """Return the underlying list of providers in failover order."""
        return list(self._providers)

    async def _try_provider(self, provider: ModelProvider, request: ModelRequest) -> Completion:
        last_exc: BaseException | None = None
        attempts = 1 + self._backoff_retries
        for attempt in range(attempts):
            try:
                return await provider.complete(request)
            except Exception as exc:
                last_exc = exc
                if attempt + 1 >= attempts or not _is_transient(exc):
                    raise
                delay = self._backoff_base_s * (2**attempt)
                logger.warning(
                    "Transient model error on %s (attempt %d/%d): %s; backing off %.3fs",
                    provider,
                    attempt + 1,
                    attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    async def complete(self, request: ModelRequest) -> Completion:
        self.last_failover = None
        last_exception: Exception | None = None
        for i, provider in enumerate(self._providers):
            req = request if i == 0 else drop_reasoning_whole_exchange(request)
            reasoning_dropped = req is not request
            try:
                return await self._try_provider(provider, req)
            except Exception as exc:
                logger.warning(
                    "ModelProvider %s (%s) failed: %s",
                    self._labels[i],
                    provider,
                    exc,
                )
                last_exception = exc
                if i + 1 >= len(self._providers):
                    break
                event = ProviderFailover(
                    run_id=self._run_id or "",
                    from_provider=self._labels[i],
                    to_provider=self._labels[i + 1],
                    reason=str(exc),
                    reasoning_dropped=reasoning_dropped
                    or any(
                        isinstance(b, ReasoningBlock)
                        for m in request.messages
                        for b in m.content
                    ),
                )
                # If the next hop will strip, mark it even when this request had no reasoning yet —
                # the policy is whole-exchange drop on any cross-provider resume.
                if i + 1 > 0:
                    event = event.model_copy(update={"reasoning_dropped": True})
                self.last_failover = event
                if self._bus is not None and self._run_id:
                    await self._bus.emit(event)

        raise OpenAIModelError(
            f"All {len(self._providers)} fallback model providers failed. Last error: {last_exception}"
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        """Streaming is deferred; raises NotImplementedError."""
        raise NotImplementedError("Streaming is deferred; use complete()")
        yield  # pragma: no cover
