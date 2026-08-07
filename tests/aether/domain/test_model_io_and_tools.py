"""Smoke tests for the model_io/, workspace.py, and tools.py domain shapes."""

from __future__ import annotations

from datetime import UTC, datetime

from aether.domain.ids import RunId, SpanId
from aether.domain.model_io import ModelMessage, ModelRequest, StopEvent, TextDelta
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.tools import ToolCall, ToolResult, ToolSpec
from aether.domain.workspace import FileSlice, PatchResult, WorktreeRef


def _span(label: Provenance = Provenance.AGENT) -> TaintSpan:
    return TaintSpan(
        span_id=SpanId("s1"), label=label, text="hi", source="test", created_at=datetime.now(UTC)
    )


def test_model_message_carries_spans_and_cache_breakpoint() -> None:
    msg = ModelMessage(role="user", spans=(_span(),), cache_breakpoint=True)
    assert msg.cache_breakpoint is True
    assert msg.spans[0].label is Provenance.AGENT


def test_model_request_defaults_tools_to_empty_tuple() -> None:
    request = ModelRequest(model="gpt", messages=(ModelMessage(role="user", spans=()),), max_tokens=100)
    assert request.tools == ()


def test_model_stream_event_union_discriminates_on_kind() -> None:
    delta = TextDelta(text="hello")
    stop = StopEvent(reason="end")
    assert delta.kind == "text"
    assert stop.kind == "stop"


def test_tool_call_and_result_round_trip() -> None:
    spec = ToolSpec(name="grep", description="search", params_json_schema="{}", effect_class="read")
    call = ToolCall(call_id="c1", name=spec.name, args_json="{}", justifying_spans=(SpanId("s1"),))
    result = ToolResult(call_id="c1", spans=(_span(Provenance.UNTRUSTED_EXTERNAL),), exit_code=0)
    assert result.spans[0].label is Provenance.UNTRUSTED_EXTERNAL
    assert call.name == "grep"


def test_worktree_ref_uses_string_abs_hint_not_path() -> None:
    ref = WorktreeRef(worktree_id="w1", run_id=RunId("r1"), base_commit="a" * 40, abs_hint="/tmp/w1")
    assert isinstance(ref.abs_hint, str)


def test_patch_result_and_file_slice() -> None:
    slice_ = FileSlice(repo_rel_path="a.py", start_line=1, end_line=10, text="x = 1\n")
    result = PatchResult(applied=True, rejected_hunks=0)
    assert slice_.end_line == 10
    assert result.applied is True
