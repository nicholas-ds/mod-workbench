"""Tests for BoardValidator."""

from pathlib import Path

from workbench.boards.board_builder import BoardBuilder
from workbench.boards.board_check import BoardValidator
from workbench.boards.board_repository import BoardRepository
from workbench.boards.front_matter import FrontMatterParser

GOOD_BOARD = """---
title: Which layout for the queue?
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
items:
  - file: shot.png
    caption: Current queue
  - file: sketch.html
    caption: Wide table sketch
---
Body text.
"""


def make_validator() -> BoardValidator:
    repository = BoardRepository(FrontMatterParser(), BoardBuilder())
    return BoardValidator(repository)


def write_board(folder: Path, text: str = GOOD_BOARD) -> Path:
    folder.mkdir(parents=True)
    (folder / "board.md").write_text(text, encoding="utf-8")
    return folder


def test_check_valid_board_is_empty(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1")
    (folder / "shot.png").write_bytes(b"png")
    (folder / "sketch.html").write_text("<!-- workbench-base-style --><p>wide</p>", encoding="utf-8")

    assert make_validator().check(folder) == ()


def test_check_reports_each_problem(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1")

    problems = make_validator().check(folder)

    assert len(problems) == 2
    assert "shot.png" in problems[0]
    assert "sketch.html" in problems[1]


def test_check_reports_raised_by_without_registered_pane(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1", GOOD_BOARD.replace("items:", "raised_by: ghost\nitems:"))
    (folder / "shot.png").write_bytes(b"png")
    (folder / "sketch.html").write_text("<!-- workbench-base-style --><p>wide</p>", encoding="utf-8")
    repository = BoardRepository(FrontMatterParser(), BoardBuilder())

    problems = BoardValidator(repository, tmp_path / "status").check(folder)

    assert len(problems) == 1
    assert "no pane registered for raised_by 'ghost'" in problems[0]


def test_check_accepts_raised_by_with_registered_pane(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1", GOOD_BOARD.replace("items:", "raised_by: workbench\nitems:"))
    (folder / "shot.png").write_bytes(b"png")
    (folder / "sketch.html").write_text("<!-- workbench-base-style --><p>wide</p>", encoding="utf-8")
    (tmp_path / "status").mkdir()
    (tmp_path / "status" / "workbench.toml").write_text('wmux_surface = "surf-1"\n', encoding="utf-8")
    repository = BoardRepository(FrontMatterParser(), BoardBuilder())

    assert BoardValidator(repository, tmp_path / "status").check(folder) == ()


def test_check_reports_html_item_without_base_style(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1")
    (folder / "shot.png").write_bytes(b"png")
    (folder / "sketch.html").write_text("<p>plain</p>", encoding="utf-8")

    problems = make_validator().check(folder)

    assert len(problems) == 1
    assert "base style" in problems[0]


def test_check_accepts_chat_raised_by_without_status_file(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1",
                         GOOD_BOARD.replace("items:", "raised_by: chat-main\nitems:"))
    (folder / "shot.png").write_bytes(b"png")
    (folder / "sketch.html").write_text("<!-- workbench-base-style --><p>wide</p>",
                                        encoding="utf-8")
    repository = BoardRepository(FrontMatterParser(), BoardBuilder())

    assert BoardValidator(repository, tmp_path / "status").check(folder) == ()


def test_check_reports_bare_chat_prefix(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1",
                         GOOD_BOARD.replace("items:", "raised_by: chat-\nitems:"))
    (folder / "shot.png").write_bytes(b"png")
    (folder / "sketch.html").write_text("<!-- workbench-base-style --><p>wide</p>",
                                        encoding="utf-8")
    repository = BoardRepository(FrontMatterParser(), BoardBuilder())

    problems = BoardValidator(repository, tmp_path / "status").check(folder)

    assert problems == ("board-1: raised_by 'chat-' has no chat name. "
                        "Use chat-<name>, for example chat-main.",)


def make_named_validator(mod_name: str) -> BoardValidator:
    repository = BoardRepository(FrontMatterParser(), BoardBuilder())
    return BoardValidator(repository, None, mod_name)


def add_item_files(folder: Path) -> None:
    (folder / "shot.png").write_bytes(b"png")
    (folder / "sketch.html").write_text("<!-- workbench-base-style --><p>wide</p>", encoding="utf-8")


def test_check_rejects_status_board_that_names_another_chat(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "mod-status",
                         GOOD_BOARD.replace("items:", "raised_by: chat-main\nitems:"))
    add_item_files(folder)
    problems = make_named_validator("Research").check(folder)
    assert problems == ("mod-status: raised_by is 'chat-main', expected 'chat-Research'. "
                        "Notes on this board go to the wrong chat.",)


def test_check_accepts_status_board_that_names_its_own_chat(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "mod-status",
                         GOOD_BOARD.replace("items:", "raised_by: chat-Research\nitems:"))
    add_item_files(folder)
    assert make_named_validator("Research").check(folder) == ()


def test_check_ignores_raised_by_of_other_boards_for_chat_name(tmp_path: Path) -> None:
    folder = write_board(tmp_path / "board-1",
                         GOOD_BOARD.replace("items:", "raised_by: chat-main\nitems:"))
    add_item_files(folder)
    assert make_named_validator("Research").check(folder) == ()
