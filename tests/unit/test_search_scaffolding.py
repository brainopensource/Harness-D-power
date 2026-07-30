"""Unit tests for Block 3 scaffolding — candidate search adapter."""

from __future__ import annotations

import pytest

from sagiha.adapters.search.sequential import SequentialCandidateSearch
from sagiha.domain.control import RunContext
from sagiha.domain.work import AcceptanceCriterion, TaskSpec


def _make_context() -> RunContext:
    return RunContext(
        run_id="test-run",
        autonomy_level="interactive",
        workspace_root="/tmp/test",
        budget_remaining_usd=5.0,
    )


def _make_task() -> TaskSpec:
    return TaskSpec(
        task_id="task-001",
        goal="Fix failing test",
        acceptance=(AcceptanceCriterion(description="Tests pass", check="pytest"),),
    )


@pytest.mark.asyncio
async def test_propose_returns_n_branch_ids() -> None:
    search = SequentialCandidateSearch()
    branches = await search.propose(_make_task(), _make_context(), n=3)
    assert len(branches) == 3
    assert all(b.startswith("candidate-") for b in branches)


@pytest.mark.asyncio
async def test_evaluate_returns_none() -> None:
    search = SequentialCandidateSearch()
    report = await search.evaluate("candidate-abc")
    assert report is None


@pytest.mark.asyncio
async def test_select_returns_first() -> None:
    search = SequentialCandidateSearch()
    winner = await search.select(["branch-a", "branch-b"])
    assert winner == "branch-a"


@pytest.mark.asyncio
async def test_select_empty_returns_empty_string() -> None:
    search = SequentialCandidateSearch()
    winner = await search.select([])
    assert winner == ""
