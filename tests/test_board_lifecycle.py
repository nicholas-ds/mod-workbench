"""Tests for BoardLifecycle."""

from pathlib import Path

import pytest

from workbench.board_lifecycle import BoardLifecycle
from workbench.board_types import Board, BoardError


def make_board(tmp_path: Path, state: str, board_id: str) -> Board:
    folder = tmp_path / "boards" / state / board_id
    folder.mkdir(parents=True)
    (folder / "board.md").write_text("---\ntitle: T\nquestions: []\n---\n", encoding="utf-8")
    return Board(id=board_id, folder=folder, title="T")


def test_close_moves_folder_to_done(tmp_path: Path) -> None:
    board = make_board(tmp_path, "open", "board-1")
    closed = BoardLifecycle().close(board)
    done_folder = tmp_path / "boards" / "done" / "board-1"
    assert closed.folder == done_folder
    assert done_folder.exists()
    assert not board.folder.exists()


def test_reopen_moves_back(tmp_path: Path) -> None:
    done_board = make_board(tmp_path, "done", "board-1")
    reopened = BoardLifecycle().reopen(done_board)
    open_folder = tmp_path / "boards" / "open" / "board-1"
    assert reopened.folder == open_folder
    assert open_folder.exists()
    assert not done_board.folder.exists()


def test_close_refuses_when_target_exists(tmp_path: Path) -> None:
    board = make_board(tmp_path, "open", "board-1")
    target = tmp_path / "boards" / "done" / "board-1"
    target.mkdir(parents=True)
    with pytest.raises(BoardError):
        BoardLifecycle().close(board)
    assert board.folder.exists()
    assert target.exists()


def test_permanent_board_cannot_be_closed(tmp_path) -> None:
    folder = tmp_path / "boards" / "open" / "atlas"
    folder.mkdir(parents=True)
    board = Board(id="atlas", folder=folder, title="Atlas", tags=("permanent",))
    with pytest.raises(BoardError):
        BoardLifecycle().close(board)
    assert folder.exists()
