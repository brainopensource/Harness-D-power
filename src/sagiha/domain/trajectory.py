"""Trajectory steps and streaming — see docs/03-contracts-and-models/domain-schemas.md#trajectory."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from sagiha.domain.content import ContentBlock, ReasoningBlock, ToolCall, ToolResult
from sagiha.domain.control import TaskStatus
from sagiha.domain.identity import StepId, utc_now
from sagiha.domain.work import TaskSpec


class RunRecord(BaseModel):
    """Resumable run state (D9) — the `runs` table row.

    Deliberately minimal: `run_id`, `task`, `status`, `updated_at`. Step `seq` is derived from
    `TrajectoryStore.steps_for_run` at resume time, never stored here — engine memory is not the
    source of truth for where a run left off.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    task: TaskSpec
    status: TaskStatus
    updated_at: datetime = Field(default_factory=utc_now)


class TrajectoryStep(BaseModel):
    """Frozen: a mutated step is an audit record that no longer reconstructs what happened."""

    model_config = ConfigDict(frozen=True)

    step_id: StepId
    reasoning: ReasoningBlock | None = None
    summary: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()
    timestamp: datetime = Field(default_factory=utc_now)


class StepScored(BaseModel):
    """Scores are a separate event, never written back into a stored step — see event-catalog.md."""

    model_config = ConfigDict(frozen=True)

    step_id: StepId
    score: float
    dimension: str
    scorer: str
    timestamp: datetime = Field(default_factory=utc_now)


class BlockStart(BaseModel):
    kind: Literal["block_start"] = "block_start"
    index: int
    block_kind: Literal["text", "reasoning", "tool_use"]


class BlockDelta(BaseModel):
    kind: Literal["block_delta"] = "block_delta"
    index: int
    text: str = ""  # text/reasoning increments
    partial_json: str = ""  # tool_use argument increments


class BlockEnd(BaseModel):
    kind: Literal["block_end"] = "block_end"
    index: int
    block: ContentBlock  # the assembled, complete block


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0  # populated where the provider supplies it
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0


class UsageReported(BaseModel):
    kind: Literal["usage"] = "usage"
    usage: TokenUsage


class StreamEnd(BaseModel):
    kind: Literal["stream_end"] = "stream_end"
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "error"]


StreamEvent = Annotated[
    BlockStart | BlockDelta | BlockEnd | UsageReported | StreamEnd,
    Field(discriminator="kind"),
]
