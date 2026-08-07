"""WorkflowStep/StepContext — node and socket types only (ADR-0013, M0)."""

from __future__ import annotations

import inspect
import typing

import pytest

from aether.domain.ids import Frozen, LeaseId, NodeId, RunId
from aether.workflow.step import StepContext, WorkflowStep


class _Input(Frozen):
    text: str


class _Output(Frozen):
    result: str


class _EchoStep(WorkflowStep[_Input, _Output]):
    node_kind = "echo"
    input_type = _Input
    output_type = _Output

    async def run(self, ctx: StepContext, payload: _Input) -> _Output:
        return _Output(result=payload.text)


def _context() -> StepContext:
    return StepContext(run_id=RunId("r1"), node_id=NodeId("n1"), lease=LeaseId("lease-1"))


async def test_concrete_step_with_frozen_bound_types_runs() -> None:
    step = _EchoStep()
    out = await step.run(_context(), _Input(text="hi"))
    assert out.result == "hi"


async def test_base_run_raises_not_implemented_stub_rule() -> None:
    class _Unimplemented(WorkflowStep[_Input, _Output]):
        node_kind = "unimplemented"
        input_type = _Input
        output_type = _Output

    with pytest.raises(NotImplementedError):
        await _Unimplemented().run(_context(), _Input(text="x"))


def test_input_digest_is_unimplemented_stub_not_a_fake_pass() -> None:
    with pytest.raises(NotImplementedError):
        _EchoStep().input_digest(_Input(text="x"))


def test_step_context_carries_only_ids_no_adapter_handles() -> None:
    """StepContext must carry only the three NewType ids — never an adapter
    handle, Path, or callable — so 'no adapter handles' is enforced by type,
    not convention."""
    hints = typing.get_type_hints(StepContext)
    assert set(hints.keys()) == {"run_id", "node_id", "lease"}
    for field_name, hint in hints.items():
        assert typing.get_origin(hint) is None, f"StepContext.{field_name} is a container type: {hint!r}"
        assert not inspect.isroutine(hint), f"StepContext.{field_name} is callable: {hint!r}"


def test_in_and_out_type_vars_are_bound_by_frozen() -> None:
    from aether.workflow.step import In, Out

    assert In.__bound__ is Frozen
    assert Out.__bound__ is Frozen
