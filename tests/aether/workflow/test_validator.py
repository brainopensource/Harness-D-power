"""Declarative topology validator (TASK-020): five static checks, each with a
malformed fixture proving it can fail. No `--force` escape hatch exists."""

from __future__ import annotations

from pathlib import Path

import pytest

from aether.workflow.validator import TopologyValidationError, load_topology, validate_topology

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "workflow"
WORKFLOWS = Path(__file__).parent.parent.parent.parent / "workflows"

# The canonical M1a socket registry: retrieve -> generate -> apply -> evaluate,
# each node's output type matching the next node's input type.
LINEAR_SOCKETS = {
    "retrieve": ("TaskInput", "RetrievedContext"),
    "generate": ("RetrievedContext", "GeneratedPatch"),
    "apply": ("GeneratedPatch", "AppliedPatch"),
    "evaluate": ("AppliedPatch", "GateReport"),
}


def _load(path: Path) -> dict:
    return load_topology(path.read_text())


def test_linear_v1_passes_all_checks() -> None:
    topology = _load(WORKFLOWS / "linear_v1.yaml")
    validate_topology(topology, LINEAR_SOCKETS)  # must not raise


def test_socket_compatibility_can_fail() -> None:
    topology = _load(FIXTURES / "bad_socket_compatibility.yaml")
    sockets = {"kind_a": ("X", "Y"), "kind_b": ("Z", "W")}
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, sockets)
    assert exc_info.value.check == "socket_compatibility"


def test_evaluator_termination_can_fail() -> None:
    topology = _load(FIXTURES / "bad_evaluator_termination.yaml")
    sockets = {"retrieve": ("A", "B"), "apply": ("B", "C")}
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, sockets)
    assert exc_info.value.check == "evaluator_termination"


def test_bounded_iteration_can_fail() -> None:
    topology = _load(FIXTURES / "bad_bounded_iteration.yaml")
    sockets = {k: ("X", "X") for k in ("retrieve", "generate", "apply", "evaluate", "repair")}
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, sockets)
    assert exc_info.value.check == "bounded_iteration"


def test_declared_fanout_can_fail() -> None:
    topology = _load(FIXTURES / "bad_declared_fanout.yaml")
    sockets = {k: ("X", "X") for k in ("retrieve", "generate", "apply", "evaluate")}
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, sockets)
    assert exc_info.value.check == "declared_fanout"


def test_budget_annotation_can_fail() -> None:
    topology = _load(FIXTURES / "bad_budget_annotation.yaml")
    sockets = {"retrieve": ("A", "B"), "evaluate": ("B", "C")}
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, sockets)
    assert exc_info.value.check == "budget_annotation"


def test_no_force_escape_hatch_exists() -> None:
    import inspect

    from aether.workflow import validator

    signature = inspect.signature(validator.validate_topology)
    assert "force" not in signature.parameters
