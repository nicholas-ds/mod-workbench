"""Tests for FrontMatterParser."""

import pytest

from workbench.boards.board_types import BoardError
from workbench.boards.front_matter import FrontMatterParser

GOOD_TEXT = """---
question: Which layout for the queue?
default: compact
priority: 3
---
The queue needs a layout decision.
"""


def parse(text: str):
    return FrontMatterParser().parse(text)


def test_parse_splits_fields_and_body() -> None:
    front_matter = parse(GOOD_TEXT)
    assert front_matter.fields["question"] == "Which layout for the queue?"
    assert front_matter.body == "The queue needs a layout decision.\n"


def test_parse_keeps_unknown_keys() -> None:
    front_matter = parse(GOOD_TEXT)
    assert front_matter.fields["priority"] == 3


def test_parse_error_names_the_reason() -> None:
    with pytest.raises(BoardError) as raised:
        parse("question: no markers\n")
    assert raised.value.reason == "file has no front matter"


def test_parse_rejects_unclosed_front_matter() -> None:
    with pytest.raises(BoardError) as raised:
        parse("---\nquestion: broken\n")
    assert raised.value.reason == "front matter is not closed"


def test_parse_rejects_bad_yaml() -> None:
    with pytest.raises(BoardError) as raised:
        parse("---\nquestion: [unclosed\n---\n")
    assert raised.value.reason.startswith("bad YAML: ")


def test_parse_rejects_non_mapping_front_matter() -> None:
    with pytest.raises(BoardError) as raised:
        parse("---\n- just a list\n---\n")
    assert raised.value.reason == "front matter is not a mapping"


def test_bare_yes_stays_a_string() -> None:
    front_matter = parse("---\ntype: yes\n---\nbody\n")
    assert front_matter.fields["type"] == "yes"


def test_bare_no_on_off_stay_strings() -> None:
    front_matter = parse("---\na: no\nb: on\nc: off\n---\nbody\n")
    assert front_matter.fields["a"] == "no"
    assert front_matter.fields["b"] == "on"
    assert front_matter.fields["c"] == "off"


def test_true_and_false_stay_booleans() -> None:
    front_matter = parse("---\nblocking: true\nhidden: false\n---\nbody\n")
    assert front_matter.fields["blocking"] is True
    assert front_matter.fields["hidden"] is False
