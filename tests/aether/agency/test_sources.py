"""`ContextSource` (T2, `TASK-054`) — provenance is a property of the
source, one byte-budget policy, and `SymbolSource` reachable through the
dispatcher rather than holding an adapter handle.
"""

from __future__ import annotations

from typing import Any

import pytest

from aether.agency.capabilities.sources import (
    SOURCES,
    CurrentFileSource,
    EntryFileSource,
    GateOutputSource,
    InstructionsSource,
    PlanSource,
    PreviousAttemptSource,
    SymbolSource,
    UnknownSource,
    get_source,
)
from aether.domain.budget import BudgetDims
from aether.domain.context import ContextRequest, Layer
from aether.domain.effects import IndexArgs, IndexResult, ReadArgs
from aether.domain.ids import RunId
from aether.domain.taint import Provenance
from aether.domain.task import Task, TaskSource
from aether.domain.workspace import FileSlice, SymbolHit, WorktreeRef

_TASK = Task(
    task_id="t1",  # type: ignore[arg-type]
    repo="r",
    base_commit="0" * 40,
    instructions="`add(a, b)` returns the wrong value.",
    environment_image_digest="sha256:" + "0" * 64,
    test_command_hash="sha256:" + "0" * 64,
    source=TaskSource(manifest_hash="sha256:" + "0" * 64, instance_id="t1"),
)
_WORKTREE = WorktreeRef(worktree_id="wt-0", run_id=RunId("r1"), base_commit="0" * 40, abs_hint="fixture")
_ZERO_BUDGET = BudgetDims()  # Frozen/immutable — safe as a shared default (ruff B008)


def _req(**overrides: Any) -> ContextRequest:
    base = {"task": _TASK, "worktree": _WORKTREE, "instructions": _TASK.instructions}
    base.update(overrides)
    return ContextRequest(**base)


class _FakeDispatch:
    """Structural `EffectDispatch` stand-in: an in-memory file map and a
    canned index result — never a real worktree, never a real indexer."""

    def __init__(self, files: dict[str, str] | None = None, hits: tuple[SymbolHit, ...] = ()) -> None:
        self._files = files or {}
        self._hits = hits
        self.index_calls: list[IndexArgs] = []

    async def read(self, args: ReadArgs, cost_estimate: BudgetDims = _ZERO_BUDGET) -> FileSlice:
        if args.repo_rel_path not in self._files:
            raise FileNotFoundError(args.repo_rel_path)
        return FileSlice(
            repo_rel_path=args.repo_rel_path, start_line=1, end_line=-1, text=self._files[args.repo_rel_path]
        )

    async def index(self, args: IndexArgs, cost_estimate: BudgetDims = _ZERO_BUDGET) -> IndexResult:
        self.index_calls.append(args)
        return IndexResult(hits=self._hits)

    async def shell(self, *a: Any, **kw: Any) -> Any:
        raise NotImplementedError

    async def model(self, *a: Any, **kw: Any) -> Any:
        raise NotImplementedError


# ------------------------------------------------------- provenance is declared once


def test_instructions_source_is_operator_labelled() -> None:
    """The only OPERATOR label in the set — everything else the model reads
    is agent- or repository-derived."""
    assert InstructionsSource.label is Provenance.OPERATOR
    assert InstructionsSource.layer is Layer.L4_TASK


@pytest.mark.parametrize(
    "source",
    [EntryFileSource(), CurrentFileSource(), PreviousAttemptSource(), GateOutputSource("g"), PlanSource()],
)
def test_every_other_shipped_source_is_agent_labelled(source: Any) -> None:
    """Repository content, prior attempts, gate output and the plan are all
    agent-derived, never operator-authored — the label lives on the class."""
    assert source.label is Provenance.AGENT


async def test_instructions_source_carries_the_task_statement_verbatim() -> None:
    blocks = await InstructionsSource().gather(_FakeDispatch(), _req())
    assert len(blocks) == 1
    assert blocks[0].text == _TASK.instructions
    assert blocks[0].label is Provenance.OPERATOR


# --------------------------------------------------------- the one budget policy


async def test_entry_file_source_reads_named_files() -> None:
    dispatch = _FakeDispatch({"mod.py": "def add(a, b):\n    return a - b\n"})
    req = _req(entry_files=("mod.py",))

    blocks = await EntryFileSource().gather(dispatch, req)

    assert len(blocks) == 1
    assert "def add" in blocks[0].text
    assert blocks[0].heading == "=== mod.py ==="
    assert blocks[0].layer is Layer.L3_REPO


async def test_a_missing_file_is_published_not_swallowed() -> None:
    """ "the model was not shown the file" must stay distinguishable from "the
    model was shown the file and failed" (coding_guidelines.md §2.5)."""
    dispatch = _FakeDispatch({})
    req = _req(entry_files=("ghost.py",))

    blocks = await EntryFileSource().gather(dispatch, req)

    assert len(blocks) == 1
    assert "not shown" in blocks[0].heading
    assert "FileNotFoundError" in blocks[0].text


async def test_the_byte_budget_is_enforced_and_the_overflow_is_published() -> None:
    dispatch = _FakeDispatch({"a.py": "x" * 100, "b.py": "y" * 100})
    req = _req(entry_files=("a.py", "b.py"), max_bytes=50)

    blocks = await EntryFileSource().gather(dispatch, req)

    assert len(blocks) == 2
    assert len(blocks[0].text) == 50  # truncated to what remained of the budget
    assert "byte budget exhausted" in blocks[1].text  # nothing left for the second file


async def test_current_file_source_shares_the_same_budget_policy() -> None:
    """A5: `repair.py`'s re-read used to have no budget and swallow errors
    into an opaque string. It now shares EntryFileSource's exact policy."""
    dispatch = _FakeDispatch({})
    req = _req(entry_files=("ghost.py",))

    blocks = await CurrentFileSource().gather(dispatch, req)

    assert len(blocks) == 1
    assert "not shown" in blocks[0].heading
    assert blocks[0].layer is Layer.L5_DIALOGUE  # re-read after an attempt, not the initial retrieval


# ---------------------------------------------------------------- gate output


async def test_gate_output_source_truncates_tail_biased() -> None:
    detail = "PASS\n" * 2000 + "AssertionError: boom"
    req = _req(gate_detail=detail)

    blocks = await GateOutputSource("gate_output", tail=50).gather(_FakeDispatch(), req)

    assert blocks[0].text.endswith("AssertionError: boom")
    assert len(blocks[0].text) == 50


async def test_gate_output_source_placeholder_when_empty() -> None:
    blocks = await GateOutputSource("gate_output").gather(_FakeDispatch(), _req(gate_detail=""))
    assert blocks[0].text == "(the gate reported no output)"


async def test_previous_attempt_placeholder_when_empty() -> None:
    blocks = await PreviousAttemptSource().gather(_FakeDispatch(), _req(previous_attempt=""))
    assert blocks[0].text == "(no patch was produced on the previous attempt)"


# ------------------------------------------------------------------- plan / I11


async def test_plan_source_produces_nothing_when_there_is_no_plan() -> None:
    """A role with no architect ahead of it must not carry an empty 'plan'
    section (a role with an architect always sets `req.plan`)."""
    blocks = await PlanSource().gather(_FakeDispatch(), _req(plan=""))
    assert blocks == ()


async def test_plan_source_is_agent_labelled_never_operator() -> None:
    """The T2.5 fix: architect.py used to concatenate the plan into the task
    instructions, which the OPERATOR-labelled instructions block then carried
    — model output acquiring operator authority through string concatenation.
    Here the plan is its own block and cannot be merged."""
    blocks = await PlanSource().gather(_FakeDispatch(), _req(plan="1. fix add()"))
    assert len(blocks) == 1
    assert blocks[0].label is Provenance.AGENT
    assert blocks[0].layer is Layer.L4_TASK


# ------------------------------------------------------------------ SymbolSource


async def test_symbol_source_reaches_tree_sitter_through_the_dispatcher() -> None:
    """The AC `TASK-054` names: reachable, and reached via `index()`, never
    via a held `Indexer` handle (I5 — every effect passes the choke point)."""
    hit = SymbolHit(repo_rel_path="mod.py", line=1, kind="function", name="add", snippet="def add(a, b): ...")
    dispatch = _FakeDispatch(hits=(hit,))
    req = _req(instructions="fix add")

    blocks = await SymbolSource().gather(dispatch, req)

    assert len(dispatch.index_calls) == 1
    assert "add" in blocks[0].text


def test_symbol_source_holds_no_adapter_handle() -> None:
    """Structural proof of I5: nothing on the instance references an Indexer
    — the only way to reach one is through `dispatch.index()`."""
    source = SymbolSource()
    assert not any("indexer" in attr.lower() for attr in vars(source))


async def test_symbol_source_produces_nothing_on_a_miss() -> None:
    dispatch = _FakeDispatch(hits=())
    blocks = await SymbolSource().gather(dispatch, _req(instructions="fix add"))
    assert blocks == ()


# ----------------------------------------------------------------- the registry


def test_get_source_raises_at_the_name_resolution_call_site() -> None:
    """`UnknownEditFormat`'s precedent: a role naming an unimplemented source
    must fail at load, not at the moment the first prompt is assembled."""
    with pytest.raises(UnknownSource, match="nope"):
        get_source("nope")


def test_every_registered_source_declares_layer_and_label() -> None:
    """A gate that cannot fail is not counted as a gate — this would fail if
    a future source forgot to set either class attribute."""
    for source in SOURCES.values():
        assert isinstance(source.layer, Layer)
        assert isinstance(source.label, Provenance)


def test_get_source_round_trips_every_registered_name() -> None:
    for name in SOURCES:
        assert get_source(name) is SOURCES[name]
