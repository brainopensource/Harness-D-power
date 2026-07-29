"""Tool calls and message content — see docs/03-contracts-and-models/domain-schemas.md#tools.

The tool namespace is open (`ToolCall.tool_name: str`, validated against the registry at
dispatch) rather than a closed enum — see ADR and docs/03-contracts-and-models/protocols-mcp-a2a.md.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sagiha.domain.graph import DiagnosticItem, SymbolRef


class EffectClass(StrEnum):
    """Governs replay safety. Without it, replaying a recorded trajectory re-executes `git push`."""

    PURE = "pure"  # safe to re-execute
    IDEMPOTENT = "idempotent"  # re-execution converges; may re-run under policy
    DESTRUCTIVE = "destructive"  # never re-executed; always served from recorded observation


class TextBlock(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class ReasoningBlock(BaseModel):
    """Opaque provider-native reasoning, round-tripped verbatim (extended-thinking signatures)."""

    kind: Literal["reasoning"] = "reasoning"
    provider: str
    opaque: dict[str, Any]
    summary: str = ""
    redacted: bool = False


class ToolUseBlock(BaseModel):
    kind: Literal["tool_use"] = "tool_use"
    call_id: str
    tool_name: str
    arguments: dict[str, Any]


class ToolResultBlock(BaseModel):
    kind: Literal["tool_result"] = "tool_result"
    call_id: str
    content: list[ContentBlock]
    is_error: bool = False


class ImageBlock(BaseModel):
    kind: Literal["image"] = "image"
    mime_type: str
    data_uri: str  # data: or a resource URI; never a filesystem path


class ResourceBlock(BaseModel):
    kind: Literal["resource"] = "resource"
    uri: str
    mime_type: str | None = None
    text: str | None = None  # inline when small; else fetch by uri


class DiagnosticBlock(BaseModel):
    kind: Literal["diagnostic"] = "diagnostic"
    diagnostics: tuple[DiagnosticItem, ...]


ContentBlock = Annotated[
    TextBlock
    | ReasoningBlock
    | ToolUseBlock
    | ToolResultBlock
    | ImageBlock
    | ResourceBlock
    | DiagnosticBlock,
    Field(discriminator="kind"),
]

ToolResultBlock.model_rebuild()


class Message(BaseModel):
    role: str
    content: list[ContentBlock]


class ModelRequest(BaseModel):
    messages: list[Message]


class ToolCall(BaseModel):
    """The tool namespace is open — validated against the registry at dispatch, not a closed enum."""

    model_config = ConfigDict(frozen=True)

    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    effect: EffectClass


class ToolResult(BaseModel):
    """`content` rather than a stringified `output`; overflow is explicit, never silently dropped."""

    content: list[ContentBlock]
    truncated: bool = False
    full_output_uri: str | None = None


# --- Tool return payloads, referenced by docs/03-contracts-and-models/tool-catalog.md ---


class DirEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    kind: Literal["file", "dir", "symlink"]
    size_bytes: int | None = None


class Match(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    line: int
    text: str


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    truncated: bool = False
    full_output_uri: str | None = None


class GitResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: str
    output: str
    commit_sha: str | None = None


class SearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    url: str
    snippet: str


class Symbol(BaseModel):
    model_config = ConfigDict(frozen=True)

    ref: SymbolRef
    signature: str
    docstring: str = ""
