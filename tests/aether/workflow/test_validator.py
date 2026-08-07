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


# --- The repair edge (TASK-023). `bounded_iteration` was exercised only
# vacuously in Sprint 2 (no topology used a repair block); linear_repair_v1 is
# the first real one, and each way of getting it wrong has a fixture. ---

REPAIR_SOCKETS = {
    "retrieve": ("TaskInput", "RetrievedContext"),
    "generate": ("RetrievedContext", "GeneratedPatch"),
    "apply": ("GeneratedPatch", "AppliedPatch"),
    "evaluate": ("AppliedPatch", "EvaluatedCandidate"),
    "repair": ("EvaluatedCandidate", "GeneratedPatch"),
}


def test_linear_repair_v1_passes_all_checks() -> None:
    topology = _load(WORKFLOWS / "linear_repair_v1.yaml")
    validate_topology(topology, REPAIR_SOCKETS)  # must not raise


def test_a_repair_block_with_no_max_iterations_is_rejected() -> None:
    """An unbounded repair block is an unbounded loop. Acceptance criterion 2."""
    topology = _load(FIXTURES / "bad_repair_unbounded.yaml")
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, REPAIR_SOCKETS)
    assert exc_info.value.check in {"schema", "bounded_iteration"}


def test_a_repair_block_above_the_bound_is_rejected() -> None:
    topology = _load(FIXTURES / "bad_repair_over_bound.yaml")
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, REPAIR_SOCKETS)
    assert exc_info.value.check in {"schema", "bounded_iteration"}


def test_a_repair_loop_that_does_not_close_on_the_judge_is_rejected() -> None:
    """I7 with extra steps: a loop that re-enters `apply` lets an unjudged
    candidate out of the loop."""
    topology = _load(FIXTURES / "bad_repair_not_on_the_judge.yaml")
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, REPAIR_SOCKETS)
    assert exc_info.value.check == "bounded_iteration"


def test_the_unrolled_repair_chains_sockets_are_checked() -> None:
    """`evaluate -> repair -> evaluate` skips `apply`, so repair's
    `GeneratedPatch` output meets evaluate's `AppliedPatch` input. Caught at
    load time, not on iteration 1 of a benchmark run."""
    topology = _load(FIXTURES / "bad_repair_socket_mismatch.yaml")
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, REPAIR_SOCKETS)
    assert exc_info.value.check == "socket_compatibility"


def test_a_repair_block_that_underfunds_its_own_chain_is_rejected() -> None:
    """An iteration budget below the sum of its chain's node budgets denies
    every child lease — a repair block that silently never runs looks exactly
    like one that runs and never helps, and the M2 ablation exists to tell
    those apart."""
    topology = _load(FIXTURES / "bad_repair_underfunded.yaml")
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, REPAIR_SOCKETS)
    assert exc_info.value.check == "bounded_iteration"
    assert "does not cover" in str(exc_info.value)


def test_a_repair_block_with_no_budget_per_iteration_is_rejected() -> None:
    topology = _load(WORKFLOWS / "linear_repair_v1.yaml")
    del topology["repair"]["budget_per_iteration"]
    with pytest.raises(TopologyValidationError) as exc_info:
        validate_topology(topology, REPAIR_SOCKETS)
    assert exc_info.value.check == "bounded_iteration"
