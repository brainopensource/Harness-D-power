"""Effects and node import purity tests (TASK-050, spec.md §2 I1, §3)."""

from __future__ import annotations

import importlib
import sys


def test_node_imports_are_pure() -> None:
    """Importing a node must not drag in the adapter stack or httpx.

    TASK-050: ReadArgs, WriteArgs, ApplyPatchArgs, ShellArgs were moved from
    composition.py to domain/effects.py so node modules do not import
    composition.py (which imports adapters at module scope).
    """
    before = set(sys.modules)
    importlib.import_module("aether.workflow.nodes.retrieve")
    pulled = set(sys.modules) - before

    assert not any(m.startswith("httpx") for m in pulled), (
        f"Importing retrieve node dragged in httpx: {pulled}"
    )
    assert not any(m.startswith("aether.adapters") for m in pulled), (
        f"Importing retrieve node dragged in adapters: {pulled}"
    )
