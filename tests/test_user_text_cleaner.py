"""Tests for UserTextCleaner: one test per behavior."""

from workbench.user_text_cleaner import UserTextCleaner

MARKER = UserTextCleaner.CONTEXT_PREFIX + "b, item i, question q. Leave out parts that are null.)"
CLEANER = UserTextCleaner()


def test_marker_line_alone_is_removed() -> None:
    assert CLEANER.clean(f"{MARKER}\n") == ""


def test_marker_line_before_typed_text_is_removed() -> None:
    assert CLEANER.clean(f"{MARKER}\nrun the tests") == "run the tests"


def test_marker_line_is_removed_wherever_it_appears() -> None:
    assert CLEANER.clean(f"one\n{MARKER}\ntwo") == "one\ntwo"


def test_text_without_marker_stays_stripped() -> None:
    assert CLEANER.clean("  hello  ") == "hello"


def test_text_without_the_context_prefix_stays() -> None:
    text = "The author is looking at board x"
    assert CLEANER.clean(text) == text
