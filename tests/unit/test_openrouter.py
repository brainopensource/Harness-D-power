"""Unit tests for OpenRouter model adapter, tier configuration, and header handling."""

from __future__ import annotations

from pathlib import Path

import pytest
import respx

from sagiha.adapters.model.openai import OpenAIModelAdapter
from sagiha.composition import load_env_file
from sagiha.domain.config import Config
from sagiha.domain.content import Message, ModelRequest, TextBlock


@pytest.mark.asyncio
@respx.mock
async def test_openrouter_default_headers_injected() -> None:
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello from OpenRouter!",
                    }
                }
            ]
        },
    )

    adapter = OpenAIModelAdapter(
        model_name="meta-llama/llama-3.3-70b-instruct:free",
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-or-v1-testkey",
    )
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Hi")])])
    response = await adapter.complete(request)

    assert response.message.content[0].text == "Hello from OpenRouter!"
    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.headers["Authorization"] == "Bearer sk-or-v1-testkey"
    assert sent_request.headers["HTTP-Referer"] == "https://github.com/brainopensource/Harness"
    assert sent_request.headers["X-Title"] == "SAGIHA Harness"


def test_openrouter_free_tiers_in_config() -> None:
    config = Config()
    assert "openrouter_free" in config.model.tiers
    assert "openrouter_code" in config.model.tiers
    assert "openrouter_gpt" in config.model.tiers
    assert "openrouter_ling" in config.model.tiers

    tier = config.model.tiers["openrouter_free"]
    assert tier.model == "google/gemma-4-31b-it:free"
    assert tier.base_url == "https://openrouter.ai/api/v1"
    assert tier.api_key_env == "OPENROUTER_API_KEY"


def test_load_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=sk-or-v1-test-env-key\nSOME_OTHER_KEY=123\n")

    parsed = load_env_file(env_file)
    assert parsed.get("OPENROUTER_API_KEY") == "sk-or-v1-test-env-key"
    assert parsed.get("SOME_OTHER_KEY") == "123"
