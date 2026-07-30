"""Phase 1: GateReport D20, call_id/is_error D21, ModelRequest v2 D10."""

from __future__ import annotations

from sagiha.domain.content import (
    Message,
    ModelRequest,
    TextBlock,
    ToolResult,
    ToolSchema,
)
from sagiha.domain.events import ToolCallCompleted, ToolCallFailed
from sagiha.domain.work import CriterionResult, GateReport


def test_gate_report_none_gate_does_not_admit() -> None:
    report = GateReport(
        criteria=(
            CriterionResult(
                description="tests pass",
                check="pytest",
                passed=True,
                required=True,
            ),
        ),
        tests_unmodified=None,
        no_new_suppressions=True,
        coverage_not_decreased=True,
        diff_within_bounds=True,
    )
    assert report.acceptance_met is True
    assert report.admitted is False


def test_gate_report_all_true_admits() -> None:
    report = GateReport(
        criteria=(
            CriterionResult(
                description="tests pass",
                check="pytest",
                passed=True,
                required=True,
            ),
        ),
        tests_unmodified=True,
        no_new_suppressions=True,
        coverage_not_decreased=True,
        diff_within_bounds=True,
    )
    assert report.admitted is True


def test_gate_report_false_gate_rejects() -> None:
    report = GateReport(
        criteria=(
            CriterionResult(
                description="tests pass",
                check="pytest",
                passed=True,
                required=True,
            ),
        ),
        tests_unmodified=False,
        no_new_suppressions=True,
        coverage_not_decreased=True,
        diff_within_bounds=True,
    )
    assert report.admitted is False


def test_tool_result_requires_call_id_and_is_error() -> None:
    result = ToolResult(
        call_id="c-1",
        content=[TextBlock(text="ok")],
        is_error=False,
    )
    assert result.call_id == "c-1"
    assert result.is_error is False


def test_tool_call_completed_carries_call_id() -> None:
    result = ToolResult(
        call_id="c-2",
        content=[TextBlock(text="ok")],
        is_error=False,
    )
    evt = ToolCallCompleted(
        run_id="r1",
        call_id="c-2",
        result=result,
        duration_ms=1.0,
    )
    assert evt.call_id == "c-2"


def test_tool_call_failed_carries_call_id() -> None:
    evt = ToolCallFailed(
        run_id="r1",
        call_id="c-3",
        error_kind="execution_error",
        disposition="SURFACE",
    )
    assert evt.call_id == "c-3"


def test_model_request_v2_fields() -> None:
    req = ModelRequest(
        system="You are a coding agent.",
        messages=[Message(role="user", content=[TextBlock(text="fix it")])],
        tools=[
            ToolSchema(
                name="read_file",
                description="Read a file",
                parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            )
        ],
        max_tokens=1024,
        temperature=0.0,
        role="execution",
    )
    assert req.system.startswith("You are")
    assert req.tools[0].name == "read_file"
    assert req.max_tokens == 1024
    assert req.temperature == 0.0
    assert req.role == "execution"


def test_model_request_v2_defaults() -> None:
    req = ModelRequest(
        messages=[Message(role="user", content=[TextBlock(text="hi")])],
    )
    assert req.system == ""
    assert req.tools == []
    assert req.role == "execution"
    assert req.max_tokens is None
    assert req.temperature is None
