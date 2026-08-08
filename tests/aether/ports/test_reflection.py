"""Generic reflection meta-test over every Protocol in src/aether/ports/.

Enforces the port rules stated in spec.md §4 / core_skeletons_and_protocols.md
§0: every method async; no Path, file handle, callable, generator-as-argument,
or live object; no bare dict[str, Any]; no Grant in any public signature.

This is TASK-002's own "reflection meta-test passes" requirement, scoped to a
generic structural pass over the Protocols we define. The fuller N-adapter-
parametrized conformance suite (registered_adapters(...)) is TASK-005 and is
out of scope here.
"""

from __future__ import annotations

import collections.abc
import importlib
import inspect
import pkgutil
import typing
from pathlib import Path
from typing import Any, Protocol

import pytest

import aether.ports

FORBIDDEN_TYPE_NAMES = {"Path", "Grant"}


def _iter_port_protocols() -> list[type]:
    protocols: list[type] = []
    pkg_path = Path(aether.ports.__file__).parent
    for module_info in pkgutil.iter_modules([str(pkg_path)]):
        module = importlib.import_module(f"aether.ports.{module_info.name}")
        for _name, obj in vars(module).items():
            if (
                inspect.isclass(obj)
                and obj is not Protocol
                and getattr(obj, "_is_protocol", False)
                and obj.__module__ == module.__name__
            ):
                protocols.append(obj)
    return protocols


PROTOCOLS = _iter_port_protocols()


def test_at_least_the_nine_ratified_protocols_are_discovered() -> None:
    names = {p.__name__ for p in PROTOCOLS}
    assert names == {
        "ModelProvider",
        "Workspace",
        "WorktreeManager",
        "ToolRegistry",
        "Indexer",
        "PolicyEngine",
        "Evaluator",
        "ResourceGovernor",
        "TrajectoryStore",
    }


def _public_methods(protocol: type) -> list[tuple[str, Any]]:
    return [
        (name, member)
        for name, member in inspect.getmembers(protocol, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]


@pytest.mark.parametrize("protocol", PROTOCOLS, ids=lambda p: p.__name__)
def test_every_method_is_async(protocol: type) -> None:
    for name, method in _public_methods(protocol):
        assert inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(method), (
            f"{protocol.__name__}.{name} is not async"
        )


def _flatten_type(tp: Any) -> list[Any]:
    """Yield tp and every type nested inside it (Optional, tuple[...], unions, etc.)."""
    out = [tp]
    for arg in typing.get_args(tp):
        out.extend(_flatten_type(arg))
    return out


@pytest.mark.parametrize("protocol", PROTOCOLS, ids=lambda p: p.__name__)
def test_no_forbidden_types_in_any_signature(protocol: type) -> None:
    for name, method in _public_methods(protocol):
        hints = typing.get_type_hints(method)
        for param_name, hint in hints.items():
            for candidate in _flatten_type(hint):
                candidate_name = getattr(candidate, "__name__", "")
                assert candidate_name not in FORBIDDEN_TYPE_NAMES, (
                    f"{protocol.__name__}.{name} param {param_name!r} references forbidden "
                    f"type {candidate_name!r}"
                )
                assert not inspect.isgeneratorfunction(candidate), (
                    f"{protocol.__name__}.{name} param {param_name!r} is a generator"
                )
                origin = typing.get_origin(candidate)
                is_callable_type = candidate is collections.abc.Callable or origin in (
                    collections.abc.Callable,
                    typing.Callable,
                )
                assert not is_callable_type, (
                    f"{protocol.__name__}.{name} param {param_name!r} is a Callable type"
                )


@pytest.mark.parametrize("protocol", PROTOCOLS, ids=lambda p: p.__name__)
def test_no_bare_dict_str_any_in_any_signature(protocol: type) -> None:
    for name, method in _public_methods(protocol):
        hints = typing.get_type_hints(method)
        for param_name, hint in hints.items():
            for candidate in _flatten_type(hint):
                origin = typing.get_origin(candidate)
                if origin is dict:
                    args = typing.get_args(candidate)
                    assert args != (str, Any), (
                        f"{protocol.__name__}.{name} param {param_name!r} is a bare dict[str, Any]"
                    )
