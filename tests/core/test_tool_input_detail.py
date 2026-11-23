"""Tests for first_input_detail: one test per behavior."""

from workbench.core.tool_input_detail import first_input_detail


def test_first_key_found_wins():
    assert first_input_detail({"pattern": "todo", "command": ""}) == "todo"


def test_command_key_beats_file_and_description_keys():
    assert first_input_detail({"filePath": "b.py", "command": "git status"}) == "git status"


def test_file_path_filePath_and_path_keys_are_accepted():
    assert first_input_detail({"file_path": "a.py"}) == "a.py"
    assert first_input_detail({"filePath": "b.py"}) == "b.py"
    assert first_input_detail({"path": "c.py"}) == "c.py"


def test_long_text_cut_to_100_characters():
    assert first_input_detail({"command": "x" * 120}) == "x" * 100


def test_whitespace_squeezed_to_one_line():
    assert first_input_detail({"command": "a\n b  c "}) == "a b c"


def test_empty_input_gives_empty_string():
    assert first_input_detail({}) == ""
