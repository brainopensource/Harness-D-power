"""Shared local-model-endpoint availability gate for `@pytest.mark.live` suites.

Mirrors `tests/podman_support.py`'s pattern: skip locally when nothing is
listening, but `AETHER_REQUIRE_LIVE_MODEL=1` turns an absent endpoint into a
hard failure for a runner that claims to have one — matching B2b's gate
("adapter passes conformance," which respx already proves, plus "endpoint is
up" for the one runner that promises it).
"""

from __future__ import annotations

import os

import httpx
import pytest

LOCAL_BASE_URL = "http://localhost:11434/v1"
LOCAL_MODEL = "qwen2.5-coder-32b"


def live_model_ready(base_url: str = LOCAL_BASE_URL) -> bool:
    try:
        response = httpx.get(f"{base_url}/models", timeout=2.0)
        return response.status_code < 500
    except httpx.HTTPError:
        return False


def require_live_model() -> None:
    if live_model_ready():
        return

    reason = f"local OpenAI-compatible endpoint required at {LOCAL_BASE_URL}"
    if os.environ.get("AETHER_REQUIRE_LIVE_MODEL") == "1":
        pytest.fail(
            f"AETHER_REQUIRE_LIVE_MODEL=1 but {reason} is unreachable. This runner is supposed "
            f"to enforce B2b's live-endpoint gate; skipping here would report green without "
            f"testing anything. Start a local OpenAI-compatible server (e.g. Ollama) serving "
            f"{LOCAL_MODEL} on :11434."
        )
    pytest.skip(reason)
