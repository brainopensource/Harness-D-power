"""Cassette record/replay ModelProvider adapter — see docs/05-tech-stack/composition-and-configuration.md."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from sagiha.domain.content import Message, ModelRequest
from sagiha.domain.trajectory import BlockDelta, StreamEnd, StreamEvent
from sagiha.ports.model import ModelProvider


class CassetteEntry(BaseModel):
    request: ModelRequest
    response: Message


class CassetteModelProvider:
    """Record/replay cassette provider implementing ModelProvider.

    In replay mode, runs with zero network API calls by serving recorded responses.
    """

    def __init__(
        self,
        cassette_path: str,
        mode: Literal["record", "replay"] = "replay",
        inner_provider: ModelProvider | None = None,
    ) -> None:
        self._cassette_path = Path(cassette_path)
        self._mode = mode
        self._inner_provider = inner_provider
        self._entries: list[CassetteEntry] = []
        self._replay_index = 0

        if self._cassette_path.exists():
            self._load_cassette()

    def _load_cassette(self) -> None:
        raw = self._cassette_path.read_text()
        data = json.loads(raw)
        self._entries = [CassetteEntry.model_validate(item) for item in data]

    def _save_cassette(self) -> None:
        if self._cassette_path.parent and not self._cassette_path.parent.exists():
            self._cassette_path.parent.mkdir(parents=True, exist_ok=True)
        data = [entry.model_dump(mode="json") for entry in self._entries]
        self._cassette_path.write_text(json.dumps(data, indent=2))

    async def complete(self, request: ModelRequest) -> Message:
        if self._mode == "replay":
            if not self._entries:
                raise RuntimeError(
                    f"Cassette at {self._cassette_path} is empty or missing"
                )
            if self._replay_index >= len(self._entries):
                entry = self._entries[-1]
            else:
                entry = self._entries[self._replay_index]
                self._replay_index += 1
            return entry.response

        # Record mode
        if self._inner_provider is None:
            raise RuntimeError(
                "CassetteModelProvider in record mode requires an inner_provider"
            )

        response = await self._inner_provider.complete(request)
        self._entries.append(CassetteEntry(request=request, response=response))
        self._save_cassette()
        return response

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        msg = await self.complete(request)

        async def _iter() -> AsyncIterator[StreamEvent]:
            yield BlockDelta(index=0, text=str(msg.content))
            yield StreamEnd(stop_reason="end_turn")

        return _iter()
