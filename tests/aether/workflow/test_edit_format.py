"""Edit formats as a swappable box (Sprint 3.5, B2).

One conformance suite, N formats — the same pattern I4 applies to adapters, for
the same reason: a seam with one implementation is a guess, and a seam whose
implementations are tested separately drifts.
"""

from __future__ import annotations

import pytest

from aether.workflow.edit_format import (
    DEFAULT_EDIT_FORMAT,
    FORMATS,
    EditFormat,
    UnifiedDiffFormat,
    UnknownEditFormat,
    WholeFileCodeblockFormat,
    get_edit_format,
)

ALL_FORMATS = list(FORMATS.values())


# ------------------------------------------------- the shared contract


@pytest.mark.parametrize("fmt", ALL_FORMATS, ids=lambda f: f.name)
def test_every_format_satisfies_the_protocol(fmt: EditFormat) -> None:
    assert isinstance(fmt, EditFormat)


@pytest.mark.parametrize("fmt", ALL_FORMATS, ids=lambda f: f.name)
def test_every_format_states_its_output_contract(fmt: EditFormat) -> None:
    """The instructions go into the system layer verbatim. A format that says
    nothing leaves the model guessing, which is the state Sprint 3 shipped in."""
    assert len(fmt.instructions()) > 40


@pytest.mark.parametrize("fmt", ALL_FORMATS, ids=lambda f: f.name)
def test_empty_output_parses_to_an_empty_edit_not_an_error(fmt: EditFormat) -> None:
    """A model that said nothing is a *failed attempt*, not a malformed one —
    the two get different detail lines and the repair edge reads them."""
    parsed = fmt.parse("")

    assert parsed.is_empty
    assert not parsed.errors


@pytest.mark.parametrize("fmt", ALL_FORMATS, ids=lambda f: f.name)
def test_prose_only_output_is_reported_as_an_error(fmt: EditFormat) -> None:
    parsed = fmt.parse("I would fix this by changing the function, but here is a poem instead.")

    assert parsed.is_empty
    assert parsed.errors


@pytest.mark.parametrize("fmt", ALL_FORMATS, ids=lambda f: f.name)
def test_parsing_is_pure(fmt: EditFormat) -> None:
    """No I/O in a format: `ApplyStep` performs the writes through the dispatch
    facade, so the choke point still sees every one (I5)."""
    assert not hasattr(fmt, "apply")
    assert not hasattr(fmt, "write")


# ----------------------------------------------------- unified diff


def test_a_fenced_diff_loses_its_fence_and_its_preamble() -> None:
    raw = (
        "Sure! Here is the fix:\n\n"
        "```diff\n"
        "diff --git a/mod.py b/mod.py\n"
        "--- a/mod.py\n"
        "+++ b/mod.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def f(a, b):\n"
        "-    return a - b\n"
        "+    return a + b\n"
        "```\n"
    )

    parsed = UnifiedDiffFormat().parse(raw)

    assert parsed.kind == "unified_diff"
    assert parsed.unified_diff.startswith("diff --git a/mod.py b/mod.py")
    assert "Sure!" not in parsed.unified_diff
    assert "```" not in parsed.unified_diff


def test_a_diff_without_a_header_is_an_error_not_a_silent_empty() -> None:
    parsed = UnifiedDiffFormat().parse("just some code\nreturn a + b\n")

    assert parsed.errors


# ------------------------------------------------ whole-file codeblocks


def test_a_labelled_block_becomes_a_file_write() -> None:
    raw = "```python:src/mod.py\ndef f(a, b):\n    return a + b\n```\n"

    parsed = WholeFileCodeblockFormat().parse(raw)

    assert parsed.kind == "whole_files"
    assert [f.repo_rel_path for f in parsed.files] == ["src/mod.py"]
    assert parsed.files[0].text.endswith("return a + b\n")


def test_several_files_in_one_reply() -> None:
    raw = (
        "```python:a.py\nX = 1\n```\n"
        "some prose between blocks\n"
        "```python:b.py\nY = 2\n```\n"
    )

    parsed = WholeFileCodeblockFormat().parse(raw)

    assert [f.repo_rel_path for f in parsed.files] == ["a.py", "b.py"]


def test_a_syntactically_broken_file_is_rejected_before_it_is_written() -> None:
    """The property a diff cannot offer: the edit is checkable *before* it
    touches the worktree, so a broken file is reported as a broken file rather
    than as a confusing test failure."""
    raw = "```python:mod.py\ndef f(:\n    return\n```\n"

    parsed = WholeFileCodeblockFormat().parse(raw)

    assert not parsed.files
    assert parsed.errors
    assert "not valid Python" in parsed.errors[0]


def test_a_good_file_survives_a_bad_sibling() -> None:
    raw = "```python:good.py\nX = 1\n```\n```python:bad.py\ndef f(:\n```\n"

    parsed = WholeFileCodeblockFormat().parse(raw)

    assert [f.repo_rel_path for f in parsed.files] == ["good.py"]
    assert len(parsed.errors) == 1


# ------------------------------------------------------- the registry


def test_the_default_is_still_the_unablated_one() -> None:
    """`spec.md` §7: no mechanism promotes without an ablation clearing the
    floor. Whole-file looks better on small models; that is a hypothesis until
    it is measured, so it ships selectable and not default."""
    assert DEFAULT_EDIT_FORMAT == "unified_diff"


def test_an_unknown_format_fails_at_construction() -> None:
    with pytest.raises(UnknownEditFormat):
        get_edit_format("telepathy")


def test_a_node_can_select_either_format() -> None:
    assert get_edit_format("unified_diff").name == "unified_diff"
    assert get_edit_format("whole_file_codeblock").name == "whole_file_codeblock"
