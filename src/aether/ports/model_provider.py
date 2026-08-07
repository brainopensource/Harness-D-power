"""ModelProvider — streaming completion boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from aether.domain.model_io import ModelRequest, ModelStreamEvent


@runtime_checkable
class ModelProvider(Protocol):
    """One adapter per provider family; a RoutingModelProvider composite
    satisfies multi-model roles (ADR-0007). Adapters enforce the request's
    token ceilings — conservation is kernel policy, not adapter courtesy."""

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]: ...

    async def count_tokens(self, request: ModelRequest) -> int: ...
