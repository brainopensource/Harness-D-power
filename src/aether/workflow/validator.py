"""Declarative topology validator (TASK-020) — TCB, ADR-0014.

Five static checks, each raising a `TopologyValidationError` naming itself.
**No `--force` escape hatch exists** — a topology failing any check is
refused, full stop. `socket_compatibility` is checked against an injected
`node_sockets` mapping (kind -> (input_type, output_type)) rather than by
importing `WorkflowStep` subclasses directly, so this TCB module never has to
import `workflow/nodes/*` (which is itself a consequence of ADR-0014: the
schema and validator are TCB, the topologies and node registrations are not).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "workflow_schema.yaml"


class TopologyValidationError(Exception):
    def __init__(self, check: str, message: str) -> None:
        self.check = check
        super().__init__(f"{check}: {message}")


def _load_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


_SCHEMA = _load_schema()


def load_topology(yaml_text: str) -> dict[str, Any]:
    return yaml.safe_load(yaml_text)


def _node_map(topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["id"]: n for n in topology["nodes"]}


def check_schema(topology: dict[str, Any]) -> None:
    try:
        jsonschema.validate(topology, _SCHEMA)
    except jsonschema.ValidationError as exc:
        raise TopologyValidationError("schema", exc.message) from exc


def check_socket_compatibility(topology: dict[str, Any], node_sockets: Mapping[str, tuple[str, str]]) -> None:
    nodes = _node_map(topology)
    for edge in topology["edges"]:
        from_node = nodes.get(edge["from"])
        to_node = nodes.get(edge["to"])
        if from_node is None or to_node is None:
            raise TopologyValidationError(
                "socket_compatibility", f"edge references unknown node: {edge['from']} -> {edge['to']}"
            )
        from_sockets = node_sockets.get(from_node["kind"])
        to_sockets = node_sockets.get(to_node["kind"])
        if from_sockets is None:
            raise TopologyValidationError(
                "socket_compatibility", f"unregistered node kind '{from_node['kind']}'"
            )
        if to_sockets is None:
            raise TopologyValidationError(
                "socket_compatibility", f"unregistered node kind '{to_node['kind']}'"
            )
        if from_sockets[1] != to_sockets[0]:
            raise TopologyValidationError(
                "socket_compatibility",
                f"edge {edge['from']} ({from_sockets[1]}) -> {edge['to']} ({to_sockets[0]}) socket mismatch",
            )


def check_evaluator_termination(topology: dict[str, Any]) -> None:
    """Every path from every entry node reaches a `kind: evaluate` node —
    structural I7, no topology routes around the judge. An `on_instrument_error`
    edge is the sole exemption (it must route to a terminal flag node instead)."""
    nodes = _node_map(topology)
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for edge in topology["edges"]:
        outgoing.setdefault(edge["from"], []).append(edge)

    # Restricted to nodes that actually appear in `edges` — a node referenced
    # only from a `repair`/`fan_out` block (not yet part of the main DAG) is
    # not a graph entry point and shouldn't be walked here.
    nodes_in_edges = {e["from"] for e in topology["edges"]} | {e["to"] for e in topology["edges"]}
    has_incoming = {edge["to"] for edge in topology["edges"]}
    entry_nodes = [nid for nid in nodes_in_edges if nid not in has_incoming] or list(nodes_in_edges)

    def _reaches_evaluate(node_id: str, visited: frozenset[str]) -> bool:
        if node_id in visited:
            return False
        node = nodes[node_id]
        if node["kind"] == "evaluate":
            return True
        edges_out = [e for e in outgoing.get(node_id, []) if e.get("when") != "on_instrument_error"]
        if not edges_out:
            return False
        return all(_reaches_evaluate(e["to"], visited | {node_id}) for e in edges_out)

    for entry in entry_nodes:
        if not _reaches_evaluate(entry, frozenset()):
            raise TopologyValidationError(
                "evaluator_termination", f"path from '{entry}' does not terminate at an evaluate node"
            )


def check_bounded_iteration(topology: dict[str, Any]) -> None:
    """`max_iterations` bound is defense-in-depth (the schema already ranges it);
    the node-id cross-references jsonschema cannot express are the real check."""
    repair = topology.get("repair")
    if repair is None:
        return  # no repair block — vacuously satisfied
    max_iterations = repair.get("max_iterations")
    if not isinstance(max_iterations, int) or not (1 <= max_iterations <= 16):
        raise TopologyValidationError(
            "bounded_iteration", f"repair.max_iterations must be an int in [1, 16], got {max_iterations!r}"
        )

    nodes = _node_map(topology)
    for field in ("from_node", "back_to"):
        ref = repair.get(field)
        if ref not in nodes:
            raise TopologyValidationError(
                "bounded_iteration", f"repair.{field} references unknown node '{ref}'"
            )
    for via in repair.get("via_nodes", []):
        if via not in nodes:
            raise TopologyValidationError(
                "bounded_iteration", f"repair.via_nodes references unknown node '{via}'"
            )


def check_declared_fanout(topology: dict[str, Any]) -> None:
    fan_out = topology.get("fan_out")
    if not fan_out:
        return  # no fan-out sites — vacuously satisfied
    nodes = _node_map(topology)
    for site in fan_out:
        node_id = site.get("node")
        if node_id not in nodes:
            raise TopologyValidationError("declared_fanout", f"fan_out references unknown node '{node_id}'")
        if "cache_sequencing" not in site:
            raise TopologyValidationError(
                "declared_fanout", f"fan_out site '{node_id}' has no declared cache_sequencing"
            )


def check_budget_annotation(topology: dict[str, Any]) -> None:
    for node in topology["nodes"]:
        if not node.get("budget"):
            raise TopologyValidationError(
                "budget_annotation", f"node '{node['id']}' has no budget annotation"
            )


def validate_topology(topology: dict[str, Any], node_sockets: Mapping[str, tuple[str, str]]) -> None:
    """Runs the schema pass plus all five static checks. No `--force` flag —
    a topology failing any check is refused, full stop."""
    check_schema(topology)
    check_socket_compatibility(topology, node_sockets)
    check_evaluator_termination(topology)
    check_bounded_iteration(topology)
    check_declared_fanout(topology)
    check_budget_annotation(topology)
