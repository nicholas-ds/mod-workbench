"""Tests for BoardBuilder."""

from pathlib import Path

import pytest

from workbench.board_builder import BoardBuilder
from workbench.board_types import BoardError, BoardItem, FrontMatter, Option

FOLDER = Path("boards/open/board-1")
BUILDER = BoardBuilder()

FIELDS = {
    "title": "Queue layout",
    "raised_by": "agent-1",
    "created": "2026-11-07T10:00:00",
    "tags": ["ui"],
    "items": [
        {"file": "layout.png", "caption": "Current layout", "group": "screens"},
    ],
    "questions": [
        {
            "id": "layout",
            "type": "choice",
            "prompt": "Which layout for the queue?",
            "options": [
                {"id": "compact", "label": "Compact", "item": "layout.png"},
                {"id": "wide", "label": "Wide"},
            ],
            "default": "compact",
            "affects": ["ui/queue.md"],
        },
        {
            "id": "rename",
            "type": "yes",
            "prompt": "Rename the queue tab?",
            "suggestion": "Queue",
            "blocking": True,
        },
    ],
    "priority": 3,
}


def expect_error(fields: dict, reason: str) -> None:
    with pytest.raises(BoardError) as raised:
        BUILDER.build(FOLDER, FrontMatter(fields=fields, body=""))
    assert raised.value.folder == FOLDER
    assert raised.value.reason == reason


def choice_fields(options: list, **overrides: object) -> dict:
    question = {
        "id": "q",
        "type": "choice",
        "prompt": "P?",
        "options": options,
        "default": options[0]["id"],
        **overrides,
    }
    return {**FIELDS, "questions": [question]}


def test_builds_board_with_items_and_questions() -> None:
    board = BUILDER.build(FOLDER, FrontMatter(fields=FIELDS, body="Notes.\n"))
    assert board.id == "board-1"
    assert board.folder == FOLDER
    assert board.title == "Queue layout"
    assert board.raised_by == "agent-1"
    assert board.created == "2026-11-07T10:00:00"
    assert board.tags == ("ui",)
    assert board.items == (
        BoardItem(file="layout.png", caption="Current layout", group="screens"),
    )
    layout = board.questions[0]
    assert layout.id == "layout"
    assert layout.type == "choice"
    assert layout.prompt == "Which layout for the queue?"
    assert layout.options == (
        Option(id="compact", label="Compact", item="layout.png"),
        Option(id="wide", label="Wide"),
    )
    assert layout.default == "compact"
    assert layout.suggestion is None
    assert layout.blocking is False
    assert layout.affects == ("ui/queue.md",)
    rename = board.questions[1]
    assert rename.options == ()
    assert rename.default is None
    assert rename.suggestion == "Queue"
    assert rename.blocking is True
    assert rename.affects == ()
    assert board.body == "Notes.\n"


def test_unknown_keys_go_to_extra() -> None:
    board = BUILDER.build(FOLDER, FrontMatter(fields=FIELDS, body=""))
    assert board.extra == {"priority": 3}


def test_choice_needs_two_or_three_options() -> None:
    expect_error(choice_fields([{"id": "a", "label": "A"}]),
                 "choice needs 2 or 3 options")
    expect_error(choice_fields([
        {"id": "a", "label": "A"},
        {"id": "b", "label": "B"},
        {"id": "c", "label": "C"},
        {"id": "d", "label": "D"},
    ]), "choice needs 2 or 3 options")


def test_choice_default_must_be_an_option_id() -> None:
    expect_error(choice_fields(
        [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
        default="nope",
    ), "default is not an option id: nope")


def test_yes_needs_suggestion() -> None:
    fields = {**FIELDS, "questions": [
        {"id": "q", "type": "yes", "prompt": "Rename the tab?"},
    ]}
    expect_error(fields, "yes question needs a suggestion")


def test_unknown_question_type_rejected() -> None:
    fields = {**FIELDS, "questions": [
        {"id": "q", "type": "poll", "prompt": "P?"},
    ]}
    expect_error(fields, "unknown question type: poll")


def test_item_path_escaping_folder_rejected() -> None:
    parent = {**FIELDS, "items": [{"file": "../x.png", "caption": "C"}]}
    expect_error(parent, "item file escapes the board folder: ../x.png")
    absolute = {**FIELDS, "items": [{"file": "/abs.png", "caption": "C"}]}
    expect_error(absolute, "item file escapes the board folder: /abs.png")


def test_duplicate_question_ids_rejected() -> None:
    repeated = {**FIELDS, "questions": [
        {"id": "same", "type": "text", "prompt": "P?"},
        {"id": "same", "type": "text", "prompt": "P again?"},
    ]}
    expect_error(repeated, "duplicate question id: same")


def test_builds_resolved_items_from_front_matter() -> None:
    resolved = {"id": "back", "prompt": "Does Back leave the menu?", "note": "Confirmed by the author.", "date": "2026-11-08"}
    board = BUILDER.build(FOLDER, FrontMatter({**FIELDS, "resolved": [resolved]}, ""))
    assert board.resolved[0].id == "back"
    assert board.resolved[0].date == "2026-11-08"


def test_rejects_resolved_item_without_note() -> None:
    bad = {"id": "back", "prompt": "Does Back leave the menu?", "date": "2026-11-08"}
    with pytest.raises(BoardError, match="resolved item needs"):
        BUILDER.build(FOLDER, FrontMatter({**FIELDS, "resolved": [bad]}, ""))
