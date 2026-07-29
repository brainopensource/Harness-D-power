"""ModelProvider — see docs/03-contracts-and-models/hexagonal-ports.md#model--control.

Model routing (tiering) is composition, not a port method — the composition root binds one
ModelProvider per role and callers request a role, never a model name. Adding `route()` or a
`tier=` parameter here is the tempting wrong turn: it moves policy into an adapter and breaks
cassette substitution, which only satisfies a narrow port, not a router.

Conformance suite must assert: `test_reasoning_block_round_trip_byte_identical`,
`test_stream_emits_exactly_one_usage_before_end`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Final, Protocol

from sagiha.domain.content import Message, ModelRequest
from sagiha.domain.trajectory import StreamEvent

PORT_VERSION: Final = 1
STABILITY: Final = "stable"


class ModelProvider(Protocol):
    async def complete(self, request: ModelRequest) -> Message: ...

    # Coroutine that resolves to an async iterator of frames — every port method is async
    # per docs/02-architecture/remoteable-ports.md, including this one.
    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]: ...
