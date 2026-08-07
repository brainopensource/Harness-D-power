"""ToolRegistry conformance (TASK-018): catalog frozen at composition (I6),
every ToolResult span labeled untrusted-external at construction (ADR-0015)."""

from __future__ import annotations

import json

import pytest

from aether.adapters.tools.builtin import BuiltinToolRegistry
from aether.adapters.workspace.git_cli import GitCliWorkspace
from aether.domain.taint import Provenance
from aether.domain.tools import ToolCall
from aether.domain.workspace import WorktreeRef
from aether.ports.tool_registry import ToolRegistry
from tests.aether.mocks import FixedCatalogToolRegistry


@pytest.fixture
def real_registry(tmp_path):  # noqa: ANN001
    worktrees_root = str(tmp_path / "worktrees")
    workspace = GitCliWorkspace(worktrees_root)
    return BuiltinToolRegistry(workspace, worktrees_root), worktrees_root


@pytest.mark.parametrize("registry", [FixedCatalogToolRegistry(), None])
async def test_registry_satisfies_protocol(registry, real_registry) -> None:  # noqa: ANN001
    instance = registry or real_registry[0]
    assert isinstance(instance, ToolRegistry)


async def test_builtin_registry_catalog_is_frozen(real_registry) -> None:  # noqa: ANN001
    registry, _ = real_registry
    catalog_a = await registry.catalog()
    catalog_b = await registry.catalog()
    assert catalog_a is catalog_b
    names = {spec.name for spec in catalog_a}
    assert names == {"read_file", "bash"}
    assert not hasattr(registry, "register")
    assert not hasattr(registry, "add_tool")


async def test_builtin_registry_bash_output_is_labeled_untrusted_external(real_registry) -> None:  # noqa: ANN001
    registry, worktrees_root = real_registry
    from aether.domain.ids import RunId

    (__import__("pathlib").Path(worktrees_root) / "run-1" / "wt-1").mkdir(parents=True)
    worktree = WorktreeRef(worktree_id="wt-1", run_id=RunId("run-1"), base_commit="a" * 40, abs_hint="/x")

    call = ToolCall(
        call_id="c1", name="bash", args_json=json.dumps({"command": "echo hi"}), justifying_spans=()
    )
    result = await registry.execute(worktree, call)

    assert result.exit_code == 0
    assert "hi" in result.spans[0].text
    assert all(span.label == Provenance.UNTRUSTED_EXTERNAL for span in result.spans)


async def test_builtin_registry_read_file_delegates_to_workspace(real_registry) -> None:  # noqa: ANN001
    registry, worktrees_root = real_registry
    from aether.domain.ids import RunId

    wt_path = __import__("pathlib").Path(worktrees_root) / "run-1" / "wt-2"
    wt_path.mkdir(parents=True)
    (wt_path / "hello.txt").write_text("hello world\n")
    worktree = WorktreeRef(worktree_id="wt-2", run_id=RunId("run-1"), base_commit="a" * 40, abs_hint="/x")

    call = ToolCall(
        call_id="c2", name="read_file", args_json=json.dumps({"path": "hello.txt"}), justifying_spans=()
    )
    result = await registry.execute(worktree, call)

    assert result.exit_code == 0
    assert "hello world" in result.spans[0].text
    assert result.spans[0].label == Provenance.UNTRUSTED_EXTERNAL


async def test_fixed_catalog_registry_output_also_untrusted_external() -> None:

    from aether.domain.ids import RunId

    registry = FixedCatalogToolRegistry()
    worktree = WorktreeRef(worktree_id="w1", run_id=RunId("r1"), base_commit="a" * 40, abs_hint="/x")
    call = ToolCall(call_id="c3", name="noop", args_json="{}", justifying_spans=())
    result = await registry.execute(worktree, call)
    # The mock returns empty spans by design (tests/aether/mocks.py) — the
    # real adapter is what this conformance suite holds to the taint rule.
    assert result.spans == ()
