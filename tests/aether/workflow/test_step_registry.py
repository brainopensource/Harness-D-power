"""Node registration by kind (Sprint 3.5, B1).

Sprint 2 keyed the executor's step map by **node id** while sockets were keyed
by **kind**, and `engine.run` hard-coded the five instances in a dict literal.
Two consequences, both structural:

* a topology with two nodes of one kind — every Best-of-N topology at M3 —
  raised `KeyError` at run time;
* a node's implementation could not be chosen from data, which is the whole
  premise of ADR-0014.

Both are fixed by registering factories per kind and building one instance per
node from that node's own `params`.
"""

from __future__ import annotations

from typing import Any

import pytest

from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import RunId
from aether.kernel.bus import EventBus
from aether.kernel.governor import ResourceGovernor
from aether.workflow.executor import UnregisteredNodeKind, WorkflowExecutor
from aether.workflow.step import StepContext, WorkflowStep


class _Echo(WorkflowStep[Any, Any]):
    """Records the params it was built with and passes its payload along."""

    node_kind = "echo"

    def __init__(self, params: Any) -> None:
        self.params = params
        self.calls = 0

    async def run(self, ctx: StepContext, payload: Any) -> Any:
        self.calls += 1
        return payload


class _Verdict(WorkflowStep[Any, Any]):
    node_kind = "evaluate"

    async def run(self, ctx: StepContext, payload: Any) -> Any:
        class _Out:
            report = GateReport(gate="tests", status=GateStatus.PASSED)

        return _Out()


def _two_generate_topology() -> dict[str, Any]:
    """The shape that used to be unrepresentable: two nodes, one kind, each
    configured differently."""
    return {
        "schema_version": "1.0.0",
        "topology_id": "two_of_a_kind",
        "description": "test",
        "nodes": [
            {"id": "gen_a", "kind": "echo", "params": {"temperature": 0}, "budget": {}},
            {"id": "gen_b", "kind": "echo", "params": {"temperature": 1}, "budget": {}},
            {"id": "evaluate", "kind": "evaluate", "budget": {}},
        ],
        "edges": [{"from": "gen_a", "to": "gen_b"}, {"from": "gen_b", "to": "evaluate"}],
    }


async def test_two_nodes_of_one_kind_get_two_instances() -> None:
    built: list[_Echo] = []

    def echo_factory(params: Any) -> WorkflowStep[Any, Any]:
        step = _Echo(params)
        built.append(step)
        return step

    executor = WorkflowExecutor(
        _two_generate_topology(),
        {"echo": echo_factory, "evaluate": lambda p: _Verdict()},
        EventBus(),
        ResourceGovernor(),
    )

    await executor.execute(RunId("run-1"), object())

    assert len(built) == 2, "one instance per node, not one per kind"
    assert [s.params["temperature"] for s in built] == [0, 1]
    assert all(s.calls == 1 for s in built)


def test_a_node_receives_its_own_params() -> None:
    seen: list[Any] = []
    WorkflowExecutor(
        _two_generate_topology(),
        {"echo": lambda p: seen.append(p) or _Echo(p), "evaluate": lambda p: _Verdict()},
        EventBus(),
        ResourceGovernor(),
    )

    assert seen == [{"temperature": 0}, {"temperature": 1}]


def test_a_node_without_params_gets_an_empty_mapping_not_none() -> None:
    topology = _two_generate_topology()
    del topology["nodes"][0]["params"]

    seen: list[Any] = []
    WorkflowExecutor(
        topology,
        {"echo": lambda p: seen.append(p) or _Echo(p), "evaluate": lambda p: _Verdict()},
        EventBus(),
        ResourceGovernor(),
    )

    assert seen[0] == {}


def test_an_unregistered_kind_fails_at_construction_not_mid_run() -> None:
    """A benchmark that dies on iteration three of task forty because a kind
    was never registered has already burned the run."""
    with pytest.raises(UnregisteredNodeKind) as exc_info:
        WorkflowExecutor(
            _two_generate_topology(),
            {"evaluate": lambda p: _Verdict()},  # 'echo' missing
            EventBus(),
            ResourceGovernor(),
        )

    assert "echo" in str(exc_info.value)


def test_the_engine_registry_covers_every_kind_the_topologies_use() -> None:
    """The registry and the shipped topologies must agree, or a run fails at
    load on a file that is checked into this repository."""
    from pathlib import Path

    from aether.engine import NODE_SOCKETS, build_step_registry
    from aether.workflow.validator import load_topology

    registry = build_step_registry(None, model_name="m")  # type: ignore[arg-type]
    workflows = Path(__file__).resolve().parents[3] / "workflows"

    for path in sorted(workflows.glob("*.yaml")):
        topology = load_topology(path.read_text())
        kinds = {node["kind"] for node in topology["nodes"]}
        assert kinds <= set(registry), f"{path.name} uses unregistered kinds {kinds - set(registry)}"
        assert kinds <= set(NODE_SOCKETS), f"{path.name} uses kinds with no declared sockets"


def test_every_registered_kind_builds_with_empty_params() -> None:
    """A factory that only works when a topology spells out every param makes
    the defaults a lie."""
    from aether.engine import build_step_registry

    registry = build_step_registry(None, model_name="m")  # type: ignore[arg-type]

    for kind, factory in registry.items():
        step = factory({})
        assert step.node_kind == kind
