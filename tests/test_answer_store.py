"""Tests for AnswerStore."""

import json
from pathlib import Path

import pytest

from workbench.answer_store import AnswerStore
from workbench.board_types import Answer, BoardError


def make_board_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "boards" / "open" / "board-1"
    folder.mkdir(parents=True)
    return folder


def test_missing_file_gives_empty_tuple(tmp_path: Path) -> None:
    answers = AnswerStore().read(make_board_folder(tmp_path))
    assert answers == ()


def test_write_then_read_round_trip(tmp_path: Path) -> None:
    folder = make_board_folder(tmp_path)
    store = AnswerStore()
    answer = Answer(
        question_id="layout",
        picked="wide",
        text=None,
        comment="wide reads better",
        answered_at="2026-11-07T12:00:00",
    )
    store.write(folder, answer)
    raw = json.loads((folder / "answers.json").read_text(encoding="utf-8"))
    assert raw == {
        "answers": [
            {
                "question_id": "layout",
                "picked": "wide",
                "text": None,
                "comment": "wide reads better",
                "answered_at": "2026-11-07T12:00:00",
            }
        ]
    }
    assert store.read(folder) == (answer,)


def test_write_replaces_same_question(tmp_path: Path) -> None:
    folder = make_board_folder(tmp_path)
    store = AnswerStore()
    store.write(folder, Answer("layout", picked="wide", answered_at="12:00"))
    store.write(folder, Answer("layout", picked="compact", answered_at="13:00"))
    store.write(folder, Answer("theme", text="dark", answered_at="13:05"))
    answers = store.read(folder)
    assert [answer.question_id for answer in answers] == ["layout", "theme"]
    assert answers[0].picked == "compact"
    assert answers[0].answered_at == "13:00"


def test_corrupt_json_raises_board_error(tmp_path: Path) -> None:
    folder = make_board_folder(tmp_path)
    (folder / "answers.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(BoardError) as raised:
        AnswerStore().read(folder)
    assert raised.value.folder == folder
