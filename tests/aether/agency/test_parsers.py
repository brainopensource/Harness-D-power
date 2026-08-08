"""`OutputParser` (T3, `TASK-055`) — one uniform `ParsedOutput` shape,
whichever parser produced it, and `edit_format.py` left alone.
"""

from __future__ import annotations

import pytest

from aether.agency.capabilities.parsers import (
    PARSERS,
    EditFormatParser,
    LessonParser,
    PassthroughText,
    PlanParser,
    UnknownParser,
    get_parser,
)


def test_edit_format_parser_delegates_to_the_real_format() -> None:
    parser = EditFormatParser("unified_diff")
    assert "unified diff" in parser.instructions().lower()

    parsed = parser.parse("diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n")

    assert parsed.kind == "edit"
    assert parsed.edit is not None
    assert parsed.edit.kind == "unified_diff"


def test_edit_format_parser_name_encodes_the_format() -> None:
    assert EditFormatParser("unified_diff").name == "edit:unified_diff"
    assert EditFormatParser("whole_file_codeblock").name == "edit:whole_file_codeblock"


def test_plan_parser_strips_and_returns_text() -> None:
    parsed = PlanParser().parse("  1. do the thing  \n")
    assert parsed.kind == "text"
    assert parsed.text == "1. do the thing"
    assert "3-line" in PlanParser().instructions()


def test_lesson_parser_strips_and_returns_text() -> None:
    parsed = LessonParser().parse("  fix the off-by-one  \n")
    assert parsed.kind == "text"
    assert parsed.text == "fix the off-by-one"


def test_passthrough_states_no_contract() -> None:
    parser = PassthroughText()
    assert parser.instructions() == ""
    assert parser.parse("anything at all").text == "anything at all"


def test_get_parser_raises_at_the_name_resolution_call_site() -> None:
    with pytest.raises(UnknownParser, match="nope"):
        get_parser("nope")


def test_registry_round_trips_every_registered_name() -> None:
    for name in PARSERS:
        assert get_parser(name) is PARSERS[name]
