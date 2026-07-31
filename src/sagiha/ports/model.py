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

from sagiha.domain.content import ModelRequest
from sagiha.domain.trajectory import Completion, StreamEvent

PORT_VERSION: Final = 2
STABILITY: Final = "provisional"


class ModelProvider(Protocol):
    #: v2 (PR-1b): returns `Completion`, not a bare `Message`.
    #:
    #: Migration: an adapter that previously returned `Message` wraps it in
    #: `Completion(message=…, usage=…, model=…)`. Adapters with no usage figure report
    #: `TokenUsage(input_tokens=0, output_tokens=0)` — a legitimate "not measured" for a
    #: replayed cassette entry, and NOT a licence to zero real usage.
    #:
    #: The port is `provisional`, which permits this break; it has one live adapter and
    #: one test double. Taken now rather than after Phase 4 writes real consumers.
    async def complete(self, request: ModelRequest) -> Completion: ...

    # Coroutine that resolves to an async iterator of frames — every port method is async
    # per docs/02-architecture/remoteable-ports.md, including this one.
    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]: ...
