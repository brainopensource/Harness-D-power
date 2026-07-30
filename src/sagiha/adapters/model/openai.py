"""OpenAI-compatible ModelProvider adapter — REST API payload mapping and execution (D8/D10)."""

from __future__ import annotations

import importlib.util
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any, Final, cast

import httpx

from sagiha.domain.content import (
    ContentBlock,
    Message,
    ModelRequest,
    ReasoningBlock,
    TextBlock,
    ToolResultBlock,
    ToolSchema,
    ToolUseBlock,
)
from sagiha.domain.trajectory import StreamEvent
from sagiha.ports.model import ModelProvider

logger = logging.getLogger(__name__)

PORT_VERSION: Final = 1


def check_openai_extra_available() -> bool:
    """Returns True if the 'openai' extra/package is installed."""
    return importlib.util.find_spec("openai") is not None


class OpenAIAdapterError(RuntimeError):
    """Base exception for OpenAI adapter errors."""


class OpenAIExtraMissingError(OpenAIAdapterError):
    """Raised when model.mode='live' or 'record' is requested without sagiha[openai] extra installed."""


class OpenAIModelError(OpenAIAdapterError):
    """Raised when an HTTP error or API failure occurs during complete()."""


class OpenAIModelAdapter(ModelProvider):
    """OpenAI-compatible ModelProvider adapter.

    Translates SAGIHA ModelRequest domain objects to/from OpenAI /v1/chat/completions payload schema.
    Communicates via httpx.AsyncClient to local or remote endpoints (Ollama, vLLM, Qwen, OpenAI, OpenRouter).
    """

    def __init__(
        self,
        model_name: str = "deepseek-coder",
        base_url: str = "http://localhost:11434/v1",
        api_key: str | None = None,
        timeout_s: float = 60.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        if not check_openai_extra_available():
            raise OpenAIExtraMissingError(
                "The 'openai' optional extra is required to run in live or record mode. "
                "Install it via `pip install sagiha[openai]` or `uv sync --extra openai`."
            )

        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or "ollama"
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._custom_client = http_client

        headers: dict[str, str] = {}
        if "openrouter.ai" in self._base_url:
            headers["HTTP-Referer"] = "https://github.com/brainopensource/Harness"
            headers["X-Title"] = "SAGIHA Harness"
        if extra_headers:
            headers.update(extra_headers)
        self._extra_headers = headers

    def _build_messages_payload(self, request: ModelRequest) -> list[dict[str, Any]]:
        payload_messages: list[dict[str, Any]] = []

        if request.system:
            payload_messages.append({"role": "system", "content": request.system})

        for msg in request.messages:
            if msg.role == "user":
                tool_results = [b for b in msg.content if isinstance(b, ToolResultBlock)]
                if tool_results:
                    for tr in tool_results:
                        texts = [b.text for b in tr.content if isinstance(b, TextBlock)]
                        content_str = "\n".join(texts) if texts else ""
                        payload_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tr.call_id,
                                "content": content_str,
                            }
                        )
                else:
                    texts = [b.text for b in msg.content if isinstance(b, TextBlock)]
                    content_str = "\n".join(texts)
                    payload_messages.append({"role": "user", "content": content_str})

            elif msg.role == "assistant":
                tool_uses = [b for b in msg.content if isinstance(b, ToolUseBlock)]
                text_blocks = [b.text for b in msg.content if isinstance(b, TextBlock)]
                assistant_item: dict[str, Any] = {
                    "role": "assistant",
                    "content": "\n".join(text_blocks) if text_blocks else None,
                }
                if tool_uses:
                    assistant_item["tool_calls"] = [
                        {
                            "id": tu.call_id,
                            "type": "function",
                            "function": {
                                "name": tu.tool_name,
                                "arguments": json.dumps(tu.arguments),
                            },
                        }
                        for tu in tool_uses
                    ]
                payload_messages.append(assistant_item)
            else:
                texts = [b.text for b in msg.content if isinstance(b, TextBlock)]
                payload_messages.append({"role": msg.role, "content": "\n".join(texts)})

        return payload_messages

    def _build_tools_payload(self, tools: list[ToolSchema]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    def _parse_embedded_tool_block(self, text: str) -> ToolUseBlock | None:
        import re

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        raw_json = match.group(1) if match else None
        if not raw_json:
            match_obj = re.search(r"(\{[\s\S]*\"arguments\"[\s\S]*\})", text)
            if match_obj:
                raw_json = match_obj.group(1)

        if not raw_json:
            return None

        try:
            parsed: Any = json.loads(raw_json)
            if isinstance(parsed, dict):
                data: dict[str, Any] = cast("dict[str, Any]", parsed)
                raw_name = data.get("name") or data.get("tool_name") or data.get("tool") or ""
                name = str(raw_name).lower()
                raw_args: Any = data.get("arguments") or data.get("args") or {}

                if name and isinstance(raw_args, dict):
                    args_dict: dict[str, Any] = {}
                    args_map: dict[str, Any] = cast("dict[str, Any]", raw_args)
                    for k, v in args_map.items():
                        args_dict[str(k)] = v
                    return ToolUseBlock(
                        call_id=f"call_{uuid.uuid4().hex[:8]}",
                        tool_name=name,
                        arguments=args_dict,
                    )
        except Exception:
            pass
        return None

    def _endpoint_url(self) -> str:
        if self._base_url.endswith("/chat/completions"):
            return self._base_url
        return f"{self._base_url}/chat/completions"

    async def complete(self, request: ModelRequest) -> Message:
        payload_messages = self._build_messages_payload(request)
        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": payload_messages,
        }

        if request.tools:
            payload["tools"] = self._build_tools_payload(request.tools)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        url = self._endpoint_url()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            **self._extra_headers,
        }

        client = self._custom_client
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout_s)
            close_client = True

        response_data: dict[str, Any] | None = None
        last_exception: Exception | None = None

        try:
            for attempt in range(1, self._max_retries + 1):
                try:
                    res = await client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        try:
                            response_data = res.json()
                            break
                        except Exception as json_err:
                            raise OpenAIModelError(
                                f"Malformed JSON response from {url}: {res.text[:200]}"
                            ) from json_err
                    else:
                        raise OpenAIModelError(
                            f"OpenAI endpoint returned HTTP {res.status_code}: {res.text[:200]}"
                        )
                except (httpx.RequestError, OpenAIModelError) as exc:
                    last_exception = exc
                    if attempt == self._max_retries:
                        raise OpenAIModelError(
                            f"HTTP request to {url} failed after {attempt} attempts: {exc}"
                        ) from exc
        finally:
            if close_client and client:
                await client.aclose()

        if response_data is None:
            raise OpenAIModelError(f"Failed to obtain response data: {last_exception}")

        choices = response_data.get("choices", [])
        if not choices:
            raise OpenAIModelError(f"OpenAI endpoint returned empty choices array: {response_data}")

        choice = choices[0]
        msg_data = choice.get("message", {})
        text_content = msg_data.get("content")
        reasoning_content = msg_data.get("reasoning_content")
        raw_tool_calls = msg_data.get("tool_calls", [])

        blocks: list[ContentBlock] = []

        if reasoning_content:
            summary_str = str(reasoning_content)[:100]
            blocks.append(
                ReasoningBlock(
                    provider="openai-compatible",
                    opaque={"reasoning_content": reasoning_content},
                    summary=summary_str,
                )
            )

        if text_content:
            blocks.append(TextBlock(text=text_content))

        if not raw_tool_calls and text_content:
            embedded_block = self._parse_embedded_tool_block(text_content)
            if embedded_block:
                blocks.append(embedded_block)

        for tc in raw_tool_calls:
            call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
            func_data = tc.get("function", {})
            tool_name = func_data.get("name", "")
            raw_args = func_data.get("arguments", "{}")

            args_dict: dict[str, Any] = {}
            if isinstance(raw_args, str):
                try:
                    parsed_args: Any = json.loads(raw_args)
                    if isinstance(parsed_args, dict):
                        p_dict: dict[str, Any] = cast("dict[str, Any]", parsed_args)
                        for k, v in p_dict.items():
                            args_dict[str(k)] = v
                    else:
                        args_dict = {"raw": raw_args}
                except json.JSONDecodeError:
                    args_dict = {"raw": raw_args}
            elif isinstance(raw_args, dict):
                r_dict: dict[str, Any] = cast("dict[str, Any]", raw_args)
                for k, v in r_dict.items():
                    args_dict[str(k)] = v

            blocks.append(
                ToolUseBlock(
                    call_id=call_id,
                    tool_name=tool_name.lower(),
                    arguments=args_dict,
                )
            )

        if not blocks:
            blocks.append(TextBlock(text=""))

        return Message(role="assistant", content=blocks)

    async def generate(self, request: ModelRequest) -> Message:
        """Alias for complete() matching prompt method naming."""
        return await self.complete(request)

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        """Async iterator yielding StreamEvents (deferred in Sprint 3; raises NotImplementedError)."""
        raise NotImplementedError("Streaming is deferred; use complete()")
