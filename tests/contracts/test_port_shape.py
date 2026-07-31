"""Meta-conformance suite: checks the shape of the port contracts themselves, not adapter behavior.

See docs/implementation/contracts-to-code.md and docs/02-architecture/remoteable-ports.md.
Walks every `Protocol` in `sagiha.ports`, resolves annotations, and asserts the five rules that
make a port implementable over a wire and safe under the CAR capability model.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import typing
from types import UnionType

from pydantic import BaseModel

import sagiha.ports as ports_pkg
from sagiha.domain.control import Grant
from sagiha.domain.identity import utc_now

# Documented exemptions from "no untyped dict crosses a port" — see
# docs/02-architecture/remoteable-ports.md#documented-exemptions. Each entry is
# (ProtocolClassName, method_name, parameter_or_return_name).
EXEMPT_DICT_ANY: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("ToolRegistry", "register", "schema"),
    }
)


def _iter_port_protocols() -> list[type]:
    protocols = []
    for info in pkgutil.iter_modules(ports_pkg.__path__):
        module = importlib.import_module(f"sagiha.ports.{info.name}")
        for _name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and getattr(obj, "_is_protocol", False)
                and obj.__module__ == module.__name__
            ):
                protocols.append(obj)
    return protocols


def _iter_port_methods() -> list[tuple[type, str, typing.Callable]]:
    methods = []
    for protocol in _iter_port_protocols():
        for name, member in vars(protocol).items():
            if name.startswith("_"):
                continue
            if inspect.isfunction(member):
                methods.append((protocol, name, member))
    return methods


def _find_bad_dict_any(tp: object) -> bool:
    """True if `tp` contains a `dict[K, Any]` anywhere in its type tree."""
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is dict and len(args) == 2 and args[1] is typing.Any:
        return True
    return any(_find_bad_dict_any(a) for a in args)


_PRIMITIVES = {str, int, float, bool, bytes, type(None)}


def _is_permitted_payload(tp: object) -> bool:
    """Pydantic BaseModel, primitives, aware datetime, Enum, or a homogeneous container of those."""
    from datetime import datetime
    from enum import Enum

    if tp in _PRIMITIVES or tp is datetime:
        return True

    origin = typing.get_origin(tp)
    if origin is None:
        if not isinstance(tp, type):
            return False
        if issubclass(tp, Enum) or issubclass(tp, BaseModel):
            return True
        # A port may hand back another port as a capability handle (e.g.
        # WorktreeManager.allocate() -> Workspace, never a raw path) — see
        # docs/03-contracts-and-models/hexagonal-ports.md#execution. This is transitively
        # wire-safe because the returned Protocol is itself subject to this same suite.
        return getattr(tp, "_is_protocol", False) and tp.__module__.startswith("sagiha.ports")

    args = typing.get_args(tp)
    if origin in (list, tuple, set, frozenset):
        return all(_is_permitted_payload(a) for a in args if a is not Ellipsis)
    if origin is dict:
        return len(args) == 2 and all(_is_permitted_payload(a) for a in args)
    if origin in (typing.Union, UnionType):
        return all(_is_permitted_payload(a) for a in args)
    if origin is typing.Literal:
        return all(type(a) in _PRIMITIVES for a in args)
    if origin is typing.AsyncIterator or (isinstance(origin, type) and origin.__name__ == "AsyncIterator"):
        return all(_is_permitted_payload(a) for a in args)
    return False


def _contains_grant(tp: object) -> bool:
    if tp is Grant:
        return True
    return any(_contains_grant(a) for a in typing.get_args(tp))


def test_no_untyped_dict_crosses_a_port() -> None:
    violations = []
    for protocol, method_name, func in _iter_port_methods():
        hints = typing.get_type_hints(func)
        for param_name, tp in hints.items():
            if not _find_bad_dict_any(tp):
                continue
            if (protocol.__name__, method_name, param_name) in EXEMPT_DICT_ANY:
                continue
            violations.append(f"{protocol.__name__}.{method_name}({param_name}: {tp!r})")
    assert not violations, f"dict[str, Any] crossing a port without a documented exemption: {violations}"


def test_every_port_method_is_async() -> None:
    violations = [
        f"{protocol.__name__}.{method_name}"
        for protocol, method_name, func in _iter_port_methods()
        if not inspect.iscoroutinefunction(func)
    ]
    assert not violations, f"synchronous port methods (every port method must be async): {violations}"


def test_all_port_payloads_are_serializable() -> None:
    violations = []
    for protocol, method_name, func in _iter_port_methods():
        hints = typing.get_type_hints(func)
        for param_name, tp in hints.items():
            if (protocol.__name__, method_name, param_name) in EXEMPT_DICT_ANY:
                continue
            if not _is_permitted_payload(tp):
                violations.append(f"{protocol.__name__}.{method_name}({param_name}: {tp!r})")
    assert not violations, f"non-serializable payload crossing a port: {violations}"


def test_no_grant_in_any_public_signature() -> None:
    violations = []
    for protocol, method_name, func in _iter_port_methods():
        hints = typing.get_type_hints(func)
        for param_name, tp in hints.items():
            if _contains_grant(tp):
                violations.append(f"{protocol.__name__}.{method_name}({param_name})")
    assert not violations, f"Grant crossing a public port signature: {violations}"


def test_no_grant_in_frozen_run_state() -> None:
    """FrozenRunState must never serialize a Grant — freeze is not a reason to freeze permission."""
    from sagiha.domain.control import FrozenRunState

    violations = []
    for name, field_info in FrozenRunState.model_fields.items():
        hint = field_info.annotation
        if hint is not None and _contains_grant(hint):
            violations.append(name)
    assert not violations, f"Grant-typed fields on FrozenRunState: {violations}"
    # Also assert no field name suggests a grant payload.
    assert "grant" not in {n.lower() for n in FrozenRunState.model_fields}


def test_all_datetimes_are_aware() -> None:
    from sagiha.domain.events import Event
    from sagiha.domain.memory import MemoryRecord, Provenance

    assert utc_now().tzinfo is not None

    event = Event(event="test.probe", run_id="r1")
    assert event.timestamp.tzinfo is not None

    record = MemoryRecord(content="x", kind="note", provenance=Provenance.HARNESS)
    assert record.valid_from.tzinfo is not None


def test_at_least_every_port_module_was_discovered() -> None:
    """Guards against the walker silently finding zero ports (e.g. a broken pkgutil path)."""
    protocols = _iter_port_protocols()
    assert len(protocols) == 19, f"expected exactly 19 ports (ADR-0019), found {len(protocols)}: {protocols}"
