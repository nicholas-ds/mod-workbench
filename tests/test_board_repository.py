"""Tests for BoardRepository."""

from pathlib import Path

from workbench.board_builder import BoardBuilder
from workbench.board_repository import BoardRepository
from workbench.board_types import Board, BoardError
from workbench.front_matter import FrontMatterParser

GOOD_BOARD = """---
title: Which layout for the queue?
created: "2026-11-07T10:00:00"
questions:
  - id: layout
    type: choice
    prompt: Which layout?
    options:
      - id: compact
        label: Compact list
      - id: wide
        label: Wide table
    default: compact
---
The queue needs a layout decision.
"""


def make_repository() -> BoardRepository:
    return BoardRepository(FrontMatterParser(), BoardBuilder())


def make_boards_dir(tmp_path: Path) -> Path:
    boards_dir = tmp_path / "boards"
    (boards_dir / "open").mkdir(parents=True)
    return boards_dir


def write_board(boards_dir: Path, state: str, board_id: str, text: str) -> Path:
    folder = boards_dir / state / board_id
    folder.mkdir(parents=True)
    (folder / "board.md").write_text(text, encoding="utf-8")
    return folder


def test_load_reads_board_md(tmp_path: Path) -> None:
    folder = write_board(make_boards_dir(tmp_path), "open", "board-1", GOOD_BOARD)
    board = make_repository().load(folder)
    assert board.id == "board-1"
    assert board.title == "Which layout for the queue?"
    assert board.folder == folder
    assert board.questions[0].id == "layout"
    assert board.body == "The queue needs a layout decision.\n"


def test_list_open_returns_boards_sorted_by_folder_name(tmp_path: Path) -> None:
    boards_dir = make_boards_dir(tmp_path)
    write_board(boards_dir, "open", "b-b", GOOD_BOARD)
    write_board(boards_dir, "open", "b-a", GOOD_BOARD)
    boards = make_repository().list_boards(boards_dir, "open")
    assert [board.id for board in boards] == ["b-a", "b-b"]


def test_bad_board_md_is_error_item(tmp_path: Path) -> None:
    boards_dir = make_boards_dir(tmp_path)
    write_board(boards_dir, "open", "good", GOOD_BOARD)
    write_board(boards_dir, "open", "bad", "---\ntitle: broken\n---\n")
    results = make_repository().list_boards(boards_dir, "open")
    boards = [r for r in results if isinstance(r, Board)]
    errors = [r for r in results if isinstance(r, BoardError)]
    assert len(boards) == 1
    assert boards[0].id == "good"
    assert len(errors) == 1
    assert errors[0].folder.name == "bad"


def test_missing_dir_gives_empty_list(tmp_path: Path) -> None:
    boards = make_repository().list_boards(tmp_path / "boards", "done")
    assert boards == []
