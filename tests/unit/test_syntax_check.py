"""H4 proving tests: `syntax_valid` reflects a real structural check.

`LocalWorkspace.apply_edit` hardcoded `syntax_valid=True` on **both** the success and
the failure path, while the tool catalog normatively promises a structural check before
write. The check is stdlib `ast.parse` — Tree-sitter is the Block-4 multi-language
upgrade, not a prerequisite for honesty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.work import Edit, EditRequest


def _ws(tmp_path: Path) -> LocalWorkspace:
    return LocalWorkspace(root=tmp_path)


@pytest.mark.asyncio
async def test_syntax_breaking_edit_is_not_written(tmp_path: Path) -> None:
    """The file must be byte-identical afterwards. A rejected edit that still wrote
    would be worse than no check at all."""
    target = tmp_path / "mod.py"
    original = "def f():\n    return 1\n"
    target.write_text(original, encoding="utf-8")

    result = await _ws(tmp_path).apply_edit(
        EditRequest(
            path="mod.py",
            edits=(Edit(old_string="return 1", new_string="return ((1"),),
        )
    )

    assert result.syntax_valid is False
    assert result.hunks[0].applied is False
    assert result.hunks[0].reason == "syntax_invalid"
    assert target.read_text(encoding="utf-8") == original, "broken edit was written to disk"


@pytest.mark.asyncio
async def test_model_receives_the_failing_line_number(tmp_path: Path) -> None:
    """A bare 'syntax error' is not actionable; the model needs to know where."""
    target = tmp_path / "mod.py"
    target.write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")

    result = await _ws(tmp_path).apply_edit(
        EditRequest(path="mod.py", edits=(Edit(old_string="b = 2", new_string="b = ("),))
    )

    assert result.syntax_valid is False
    assert result.hunks[0].nearest_match is not None
    assert "line" in result.hunks[0].nearest_match.lower()


@pytest.mark.asyncio
async def test_valid_python_edit_still_applies(tmp_path: Path) -> None:
    target = tmp_path / "mod.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")

    result = await _ws(tmp_path).apply_edit(
        EditRequest(path="mod.py", edits=(Edit(old_string="VALUE = 1", new_string="VALUE = 2"),))
    )

    assert result.syntax_valid is True
    assert result.hunks[0].applied is True
    assert target.read_text(encoding="utf-8") == "VALUE = 2\n"


@pytest.mark.asyncio
async def test_non_python_files_are_written_without_a_syntax_claim(tmp_path: Path) -> None:
    """No parser for .md, so no claim is made — and the edit is not blocked."""
    target = tmp_path / "notes.md"
    target.write_text("# Title\n", encoding="utf-8")

    result = await _ws(tmp_path).apply_edit(
        EditRequest(path="notes.md", edits=(Edit(old_string="# Title", new_string="# (((("),))
    )

    assert result.hunks[0].applied is True
    assert target.read_text(encoding="utf-8") == "# ((((\n"


@pytest.mark.asyncio
async def test_anchor_failure_does_not_claim_syntax_validity(tmp_path: Path) -> None:
    """The failure path hardcoded syntax_valid=True — nothing was ever parsed there."""
    target = tmp_path / "mod.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")

    result = await _ws(tmp_path).apply_edit(
        EditRequest(path="mod.py", edits=(Edit(old_string="NOT_PRESENT", new_string="x"),))
    )

    assert result.hunks[0].reason == "anchor_not_found"
    assert result.syntax_valid is False, "no write happened, so no valid-syntax claim is warranted"
