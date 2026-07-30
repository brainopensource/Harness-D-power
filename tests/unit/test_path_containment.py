"""Path containment — kernel refusal and adapter defence in depth.

Regression coverage for the sibling-prefix escape: a `startswith` comparison
against the root string admits `/w/proj-evil/secrets` when the root is
`/w/proj`, because the former genuinely starts with the latter. Both the
authorize-time check and the adapter guard must reject it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.tools.builtins import READ_SCHEMA
from sagiha.adapters.workspace.local import LocalWorkspace, list_dir_entries, resolve_within
from sagiha.domain.content import EffectClass, ToolCall
from sagiha.domain.control import RunContext
from sagiha.kernel.policy.engine import DefaultPolicyEngine, escapes_root

# --- lexical kernel check ------------------------------------------------


@pytest.mark.parametrize(
    "candidate",
    [
        "../outside.txt",
        "../../etc/passwd",
        "sub/../../outside.txt",
        "/etc/passwd",
        "/w/proj-evil/secrets",  # the sibling-prefix escape
    ],
)
def test_escapes_root_rejects_traversal(candidate: str) -> None:
    assert escapes_root("/w/proj", candidate) is True


@pytest.mark.parametrize(
    "candidate",
    [
        ".",
        "file.txt",
        "sub/file.txt",
        "sub/../file.txt",
        "/w/proj/file.txt",
        "/w/proj",
    ],
)
def test_escapes_root_allows_contained(candidate: str) -> None:
    assert escapes_root("/w/proj", candidate) is False


def test_sibling_prefix_is_not_contained() -> None:
    """The specific bug: shared string prefix is not containment."""
    assert escapes_root("/w/proj", "/w/proj-evil/secrets") is True


# --- authorize-time refusal ---------------------------------------------


async def test_authorize_denies_path_outside_workspace_root() -> None:
    engine = DefaultPolicyEngine()
    engine.register_tool_schema("read_file", READ_SCHEMA)
    ctx = RunContext(
        run_id="r1",
        autonomy_level="interactive",
        workspace_root="/w/proj",
        budget_remaining_usd=1.0,
    )

    decision = await engine.authorize(
        ToolCall(
            call_id="c1",
            tool_name="read_file",
            arguments={"path": "../../etc/passwd"},
            effect=EffectClass.PURE,
        ),
        ctx,
    )

    assert decision.allowed is False
    assert decision.grant_id is None
    assert "escapes workspace root" in decision.reason


async def test_authorize_allows_contained_path_and_scopes_the_grant() -> None:
    engine = DefaultPolicyEngine()
    engine.register_tool_schema("read_file", READ_SCHEMA)
    ctx = RunContext(
        run_id="r1",
        autonomy_level="interactive",
        workspace_root="/w/proj",
        budget_remaining_usd=1.0,
    )

    decision = await engine.authorize(
        ToolCall(
            call_id="c1",
            tool_name="read_file",
            arguments={"path": "src/app.py"},
            effect=EffectClass.PURE,
        ),
        ctx,
    )

    assert decision.allowed is True
    assert decision.grant_id is not None
    grant = engine.get_grant(decision.grant_id)
    assert grant is not None
    assert grant.scope_paths == ("src/app.py",)


# --- adapter defence in depth -------------------------------------------


def test_resolve_within_rejects_sibling_prefix_directory(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    sibling = tmp_path / "proj-evil"
    sibling.mkdir()
    (sibling / "secrets").write_text("token", encoding="utf-8")

    with pytest.raises(PermissionError):
        resolve_within(root.resolve(), "../proj-evil/secrets")


def test_resolve_within_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (root / "link").symlink_to(outside)

    with pytest.raises(PermissionError):
        resolve_within(root.resolve(), "link")


async def test_workspace_read_refuses_traversal(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    (tmp_path / "outside.txt").write_text("secret", encoding="utf-8")
    ws = LocalWorkspace(str(root))

    with pytest.raises(PermissionError):
        await ws.read("../outside.txt")


def test_list_dir_refuses_traversal(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(PermissionError):
        list_dir_entries(root.resolve(), "..")
