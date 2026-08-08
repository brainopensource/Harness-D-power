"""Shared local-model-endpoint availability gate for `@pytest.mark.live` suites.

Mirrors `tests/podman_support.py`'s pattern: skip locally when nothing is
listening, but `AETHER_REQUIRE_LIVE_MODEL=1` turns an absent endpoint into a
hard failure for a runner that claims to have one — matching B2b's gate
("adapter passes conformance," which respx already proves, plus "endpoint is
up" for the one runner that promises it).

**The model is resolved from the endpoint, not hardcoded.** A fixed
`qwen2.5-coder-32b` made this gate report an *adapter* failure whenever a
perfectly healthy endpoint happened to serve something else — which is what it
did the first time a real Ollama came up on this machine. "The endpoint does not
serve the model we asked for" is an environment mismatch and has to read as one;
misattributing it to the adapter is the same defect class as scoring an
instrument error as a test failure (B4), one layer out.
"""

from __future__ import annotations

import os

import httpx
import pytest

LOCAL_BASE_URL = "http://localhost:11434/v1"
#: Preferred model when the endpoint serves it. Overridable with
#: `AETHER_LIVE_MODEL`; otherwise whatever the endpoint actually lists wins.
PREFERRED_MODEL = "qwen2.5-coder-32b"


def _listed_models(base_url: str = LOCAL_BASE_URL) -> list[str] | None:
    """Model ids the endpoint reports, or None when it is unreachable."""
    try:
        response = httpx.get(f"{base_url}/models", timeout=2.0)
    except httpx.HTTPError:
        return None
    if response.status_code >= 500:
        return None
    try:
        payload = response.json()
    except ValueError:
        return []
    return [entry["id"] for entry in payload.get("data", []) if "id" in entry]


def live_model_ready(base_url: str = LOCAL_BASE_URL) -> bool:
    return _listed_models(base_url) is not None


def resolve_live_model(base_url: str = LOCAL_BASE_URL) -> str:
    """The model id to test against: the env override, else the preferred one
    when served, else the first model the endpoint lists."""
    override = os.environ.get("AETHER_LIVE_MODEL")
    if override:
        return override
    models = _listed_models(base_url) or []
    if PREFERRED_MODEL in models:
        return PREFERRED_MODEL
    return models[0] if models else PREFERRED_MODEL


def require_live_model(base_url: str = LOCAL_BASE_URL) -> str:
    """Skip (or hard-fail when promised), and return the model to exercise."""
    models = _listed_models(base_url)

    if models:
        return resolve_live_model(base_url)

    if models is None:
        reason = f"local OpenAI-compatible endpoint required at {base_url}"
    else:
        reason = f"endpoint at {base_url} is up but serves no models"

    if os.environ.get("AETHER_REQUIRE_LIVE_MODEL") == "1":
        pytest.fail(
            f"AETHER_REQUIRE_LIVE_MODEL=1 but {reason}. This runner is supposed to enforce "
            f"B2b's live-endpoint gate; skipping here would report green without testing "
            f"anything. Start a local OpenAI-compatible server (e.g. Ollama) on :11434, or "
            f"point AETHER_LIVE_MODEL at the model it serves."
        )
    pytest.skip(reason)


#: Backwards-compatible alias for callers that only need a name to print.
LOCAL_MODEL = PREFERRED_MODEL
