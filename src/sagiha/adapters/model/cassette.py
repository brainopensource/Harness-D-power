"""Cassette record/replay ModelProvider adapter — digest-keyed (D2 / D10)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from sagiha.domain.content import Message, ModelRequest
from sagiha.domain.trajectory import StreamEvent
from sagiha.ports.model import ModelProvider


class CassetteMismatchError(RuntimeError):
    """Raised when replay request digest does not match or the cassette is exhausted."""


def request_digest(request: ModelRequest) -> str:
    """Canonical SHA-256 digest of a ModelRequest for cassette matching."""
    payload = request.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CassetteEntry(BaseModel):
    request: ModelRequest
    response: Message
    digest: str = ""

    def resolved_digest(self) -> str:
        return self.digest or request_digest(self.request)


class CassetteModelProvider:
    """Record/replay cassette provider implementing ModelProvider.

    In replay mode, runs with zero network API calls by serving recorded responses
    keyed on a canonical ModelRequest digest (D2).
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
        self._by_digest: dict[str, list[CassetteEntry]] = {}
        self._digest_cursors: dict[str, int] = {}

        if self._cassette_path.exists():
            self._load_cassette()

    def _load_cassette(self) -> None:
        raw = self._cassette_path.read_text()
        data = json.loads(raw)
        self._entries = [CassetteEntry.model_validate(item) for item in data]
        self._by_digest = {}
        for entry in self._entries:
            digest = entry.resolved_digest()
            self._by_digest.setdefault(digest, []).append(entry)

    def _save_cassette(self) -> None:
        if self._cassette_path.parent and not self._cassette_path.parent.exists():
            self._cassette_path.parent.mkdir(parents=True, exist_ok=True)
        data = [entry.model_dump(mode="json") for entry in self._entries]
        self._cassette_path.write_text(json.dumps(data, indent=2))

    async def complete(self, request: ModelRequest) -> Message:
        digest = request_digest(request)

        if self._mode == "replay":
            if not self._entries:
                raise CassetteMismatchError(f"Cassette at {self._cassette_path} is empty or missing")
            bucket = self._by_digest.get(digest, [])
            cursor = self._digest_cursors.get(digest, 0)
            if cursor >= len(bucket):
                raise CassetteMismatchError(f"Cassette exhausted or mismatch for digest {digest[:12]}…")
            entry = bucket[cursor]
            self._digest_cursors[digest] = cursor + 1
            return entry.response

        if self._inner_provider is None:
            raise RuntimeError("CassetteModelProvider in record mode requires an inner_provider")

        response = await self._inner_provider.complete(request)
        entry = CassetteEntry(request=request, response=response, digest=digest)
        self._entries.append(entry)
        self._by_digest.setdefault(digest, []).append(entry)
        self._save_cassette()
        return response

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError("Cassette streaming is deferred; use complete() (D15)")
