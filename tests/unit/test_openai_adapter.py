"""Unit tests for OpenAIModelAdapter REST payload mapping, tool-call parsing, and error handling."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from sagiha.adapters.model.cassette import CassetteModelProvider
from sagiha.adapters.model.openai import (
    OpenAIExtraMissingError,
    OpenAIModelAdapter,
    OpenAIModelError,
)
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig, SandboxConfig
from sagiha.domain.content import (
    Message,
    ModelRequest,
    ReasoningBlock,
    TextBlock,
    ToolResultBlock,
    ToolSchema,
    ToolUseBlock,
)


@pytest.mark.asyncio
async def test_openai_extra_missing_error() -> None:
    with patch("sagiha.adapters.model.openai.check_openai_extra_available", return_value=False):
        with pytest.raises(OpenAIExtraMissingError, match="openai.*optional extra is required"):
            OpenAIModelAdapter()


@pytest.mark.asyncio
@respx.mock
async def test_complete_text_response() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello, SAGIHA!",
                    }
                }
            ]
        },
    )

    adapter = OpenAIModelAdapter(base_url="http://localhost:11434/v1")
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Hello")])])
    response = await adapter.complete(request)

    assert response.message.role == "assistant"
    assert len(response.message.content) == 1
    assert isinstance(response.message.content[0], TextBlock)
    assert response.message.content[0].text == "Hello, SAGIHA!"


@pytest.mark.asyncio
@respx.mock
async def test_complete_tool_calls_parsing() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Reading target file...",
                        "tool_calls": [
                            {
                                "id": "call_12345",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": '{"path": "src/main.py"}',
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )

    adapter = OpenAIModelAdapter(base_url="http://localhost:11434/v1")
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Inspect main.py")])])
    response = await adapter.complete(request)

    assert len(response.message.content) == 2
    assert isinstance(response.message.content[0], TextBlock)
    assert response.message.content[0].text == "Reading target file..."
    assert isinstance(response.message.content[1], ToolUseBlock)
    assert response.message.content[1].call_id == "call_12345"
    assert response.message.content[1].tool_name == "read_file"
    assert response.message.content[1].arguments == {"path": "src/main.py"}


@pytest.mark.asyncio
@respx.mock
async def test_reasoning_content_parsing() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "reasoning_content": "Deep reasoning trace here",
                        "content": "Final answer",
                    }
                }
            ]
        },
    )

    adapter = OpenAIModelAdapter()
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Think deeply")])])
    response = await adapter.complete(request)

    assert len(response.message.content) == 2
    assert isinstance(response.message.content[0], ReasoningBlock)
    assert response.message.content[0].opaque == {"reasoning_content": "Deep reasoning trace here"}
    assert isinstance(response.message.content[1], TextBlock)
    assert response.message.content[1].text == "Final answer"


@pytest.mark.asyncio
@respx.mock
async def test_message_history_and_tools_translation() -> None:
    route = respx.post("http://localhost:11434/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Done!",
                    }
                }
            ]
        },
    )

    adapter = OpenAIModelAdapter(model_name="qwen2.5-coder")
    request = ModelRequest(
        system="System instruction",
        messages=[
            Message(role="user", content=[TextBlock(text="Run command")]),
            Message(
                role="assistant",
                content=[
                    ToolUseBlock(
                        call_id="call_99",
                        tool_name="read_file",
                        arguments={"path": "foo.txt"},
                    )
                ],
            ),
            Message(
                role="user",
                content=[
                    ToolResultBlock(
                        call_id="call_99",
                        content=[TextBlock(text="file body")],
                    )
                ],
            ),
        ],
        tools=[
            ToolSchema(
                name="read_file",
                description="Read a file",
                parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            )
        ],
        temperature=0.5,
        max_tokens=2048,
    )

    response = await adapter.complete(request)
    assert response.message.content[0].text == "Done!"

    assert route.called
    sent_request = route.calls.last.request
    sent_payload = json.loads(sent_request.content)

    assert sent_payload["model"] == "qwen2.5-coder"
    assert sent_payload["temperature"] == 0.5
    assert sent_payload["max_tokens"] == 2048
    assert len(sent_payload["messages"]) == 4
    assert sent_payload["messages"][0] == {"role": "system", "content": "System instruction"}
    assert sent_payload["messages"][1] == {"role": "user", "content": "Run command"}
    assert sent_payload["messages"][2] == {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_99",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path": "foo.txt"}',
                },
            }
        ],
    }
    assert sent_payload["messages"][3] == {
        "role": "tool",
        "tool_call_id": "call_99",
        "content": "file body",
    }
    assert len(sent_payload["tools"]) == 1
    assert sent_payload["tools"][0]["function"]["name"] == "read_file"


@pytest.mark.asyncio
@respx.mock
async def test_http_non_200_error_handling() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").respond(
        status_code=500,
        text="Internal Server Error",
    )

    adapter = OpenAIModelAdapter(max_retries=1)
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    with pytest.raises(OpenAIModelError, match="HTTP 500"):
        await adapter.complete(request)


@pytest.mark.asyncio
@respx.mock
async def test_network_drop_handling() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").side_effect = httpx.ConnectError(
        "Connection refused"
    )

    adapter = OpenAIModelAdapter(max_retries=1)
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])

    with pytest.raises(OpenAIModelError, match="failed after 1 attempts"):
        await adapter.complete(request)


@pytest.mark.asyncio
@respx.mock
async def test_malformed_json_arguments() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_bad_json",
                                "type": "function",
                                "function": {
                                    "name": "run_cmd",
                                    "arguments": "{invalid json payload",
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )

    adapter = OpenAIModelAdapter()
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])
    response = await adapter.complete(request)

    assert len(response.message.content) == 1
    tool_block = response.message.content[0]
    assert isinstance(tool_block, ToolUseBlock)
    assert tool_block.arguments == {"raw": "{invalid json payload"}


@pytest.mark.asyncio
@respx.mock
async def test_generate_alias() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"role": "assistant", "content": "Alias output"}}]},
    )

    adapter = OpenAIModelAdapter()
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])
    response = await adapter.generate(request)
    assert response.message.content[0].text == "Alias output"


@pytest.mark.asyncio
async def test_stream_deferred() -> None:
    adapter = OpenAIModelAdapter()
    request = ModelRequest(messages=[Message(role="user", content=[TextBlock(text="Test")])])
    with pytest.raises(NotImplementedError, match="Streaming is deferred"):
        await adapter.stream(request)


@pytest.mark.asyncio
async def test_composition_live_mode() -> None:
    config = Config(model=ModelConfig(mode="live"), sandbox=SandboxConfig(runtime="subprocess"))
    kernel = build_kernel(config)
    assert isinstance(kernel.model_provider, OpenAIModelAdapter)


@pytest.mark.asyncio
async def test_composition_record_mode(tmp_path: Path) -> None:
    cassette_file = tmp_path / "cassette.json"
    config = Config(model=ModelConfig(mode="record"), sandbox=SandboxConfig(runtime="subprocess"))
    kernel = build_kernel(config, cassette_path=str(cassette_file))
    assert isinstance(kernel.model_provider, CassetteModelProvider)
