"""S3.2 proving tests — ExchangeCompactor pairing, no-op, taint summary, 200-step window."""

from __future__ import annotations

import pytest

from sagiha.agency.context.assembler import ContextAssembler, result_message
from sagiha.agency.context.compactor import SUMMARY_TAG, Exchange, TruncatingCompactor
from sagiha.domain.config import ContextConfig
from sagiha.domain.content import (
    Message,
    ReasoningBlock,
    TextBlock,
    ToolResult,
    ToolResultBlock,
    ToolSchema,
    ToolUseBlock,
    is_untrusted_wrapped,
)
from sagiha.domain.work import AcceptanceCriterion, TaskSpec


def _task() -> TaskSpec:
    return TaskSpec(
        task_id="t1",
        goal="long horizon coding task",
        acceptance=(AcceptanceCriterion(description="pass", check="true", required=True),),
        profile="coding",
    )


def _exchange(
    n: int,
    *,
    tainted: bool = False,
    with_reasoning: bool = False,
    big: bool = False,
) -> Exchange:
    call_id = f"c{n}"
    content: list = []
    if with_reasoning:
        content.append(ReasoningBlock(provider="test", opaque={"t": n}, summary=f"thinking {n}"))
    body = ("x" * 4000) if big else f"read file {n}"
    content.append(ToolUseBlock(call_id=call_id, tool_name="read_file", arguments={"path": f"f{n}.py"}))
    assistant = Message(role="assistant", content=content)
    result = ToolResult(
        call_id=call_id,
        content=[TextBlock(text=("Y" * 4000) if big else f"contents {n}")],
        trusted=not tainted,
    )
    results = (result_message(call_id, result, "read_file"),)
    return Exchange.build(assistant, results, tainted=tainted)


def _tool_result_ids(exchanges: tuple[Exchange, ...]) -> set[str]:
    ids: set[str] = set()
    for ex in exchanges:
        for msg in ex.results:
            for block in msg.content:
                if isinstance(block, ToolResultBlock):
                    ids.add(block.call_id)
    return ids


def _tool_use_ids(exchanges: tuple[Exchange, ...]) -> set[str]:
    ids: set[str] = set()
    for ex in exchanges:
        for block in ex.assistant.content:
            if isinstance(block, ToolUseBlock):
                ids.add(block.call_id)
    return ids


@pytest.mark.anyio
async def test_compact_is_noop_when_within_budget() -> None:
    exchanges = tuple(_exchange(i) for i in range(3))
    total = sum(ex.tokens for ex in exchanges)
    out = await TruncatingCompactor().compact(
        exchanges, keep_first=2, keep_last_tokens=total + 1000
    )
    assert out == exchanges


@pytest.mark.anyio
async def test_post_compaction_has_no_orphan_tool_result_ids() -> None:
    """Every surviving tool_result call_id must still have a paired tool_use in its exchange."""
    exchanges = tuple(_exchange(i, big=True) for i in range(10))
    out = await TruncatingCompactor().compact(exchanges, keep_first=2, keep_last_tokens=500)
    assert any(ex.is_summary for ex in out)
    for ex in out:
        if ex.is_summary:
            assert not _tool_result_ids((ex,))
            continue
        uses = _tool_use_ids((ex,))
        results = _tool_result_ids((ex,))
        assert results <= uses, f"orphan tool_result ids: {results - uses}"


@pytest.mark.anyio
async def test_reasoning_dropped_whole_exchange_or_intact() -> None:
    exchanges = (
        _exchange(0, with_reasoning=True),
        *(_exchange(i, big=True) for i in range(1, 8)),
        _exchange(8, with_reasoning=True),
    )
    out = await TruncatingCompactor().compact(exchanges, keep_first=1, keep_last_tokens=800)
    for ex in out:
        if ex.is_summary:
            # Summary never carries a half-reasoning block from a compacted exchange.
            assert not any(isinstance(b, ReasoningBlock) for b in ex.assistant.content)
            continue
        reasons = [b for b in ex.assistant.content if isinstance(b, ReasoningBlock)]
        uses = [b for b in ex.assistant.content if isinstance(b, ToolUseBlock)]
        # Intact exchange: if reasoning was present originally it stays with its tools.
        if reasons:
            assert uses, "reasoning without its exchange tools"


@pytest.mark.anyio
async def test_tainted_summary_carries_untrusted_envelope() -> None:
    middle_tainted = tuple(_exchange(i, tainted=True, big=True) for i in range(6))
    exchanges = (_exchange(0), *middle_tainted, _exchange(99, big=True))
    out = await TruncatingCompactor().compact(exchanges, keep_first=1, keep_last_tokens=200)
    summaries = [ex for ex in out if ex.is_summary]
    assert summaries
    summary = summaries[0]
    assert summary.tainted is True
    text_blocks = [b for b in summary.assistant.content if isinstance(b, TextBlock)]
    assert text_blocks
    assert is_untrusted_wrapped(text_blocks[0].text)
    assert 'source="compacted-untrusted-span"' in text_blocks[0].text
    assert SUMMARY_TAG in text_blocks[0].text or "compacted" in text_blocks[0].text.lower()


@pytest.mark.anyio
async def test_200_step_synthetic_run_under_128k_window() -> None:
    """Exit metric: 200-step synthetic run completes under a 128k window."""
    config = ContextConfig(
        max_context_tokens=128_000,
        keep_first_exchanges=2,
        keep_last_tokens=24_000,
        compact_at_headroom=0.20,
    )
    assembler = ContextAssembler(
        system_prompt="You are a coding agent.",
        tool_schemas=(ToolSchema(name="read_file", description="r", parameters={}),),
        task=_task(),
        config=config,
        compactor=TruncatingCompactor(),
    )

    digests: list[str] = []
    for i in range(200):
        call_id = f"c{i}"
        # ~1k tokens of tool output each step so the window would overflow without compaction.
        payload = ("Z" * 4000) + f" step={i}"
        assistant = Message(
            role="assistant",
            content=[ToolUseBlock(call_id=call_id, tool_name="read_file", arguments={"path": f"f{i}.py"})],
        )
        result = ToolResult(call_id=call_id, content=[TextBlock(text=payload)], trusted=False)
        assembler.append_exchange(assistant, (result_message(call_id, result, "read_file"),), tainted=True)
        assembled = await assembler.assemble(role="execution")
        digests.append(assembled.stable_prefix_digest)
        total = assembled.prefix_tokens + assembled.tail_tokens
        assert total <= config.max_context_tokens, (
            f"step {i}: total={total} exceeds window {config.max_context_tokens}"
        )

    assert len(set(digests)) == 1, "stable_prefix_digest must stay constant across 200 steps"
    # Compaction must have fired at least once for a 200-step saturated run.
    assert any(ex.is_summary for ex in assembler.exchanges)
