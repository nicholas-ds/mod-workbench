"""Tests for first_input_detail: one test per behavior."""

from workbench.tool_input_detail import first_input_detail


def test_first_key_found_wins():
    assert first_input_detail({"pattern": "todo", "command": ""}) == "todo"


def test_long_text_cut_to_60_characters():
    assert first_input_detail({"command": "x" * 80}) == "x" * 60


def test_whitespace_squeezed_to_one_line():
    assert first_input_detail({"command": "a\n b  c "}) == "a b c"


def test_empty_input_gives_empty_string():
    assert first_input_detail({}) == ""
