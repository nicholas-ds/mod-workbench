import os
from pathlib import Path

from workbench.boards.board_types import Board, BoardItem
from workbench.boards.permanent_board import PermanentBoardRule

NOW = 1_800_000_000.0


def make_board(tmp_path: Path, tags: tuple[str, ...], age_days: float) -> Board:
    (tmp_path / "a.png").write_bytes(b"x")
    stamp = NOW - age_days * 86400
    os.utime(tmp_path / "a.png", (stamp, stamp))
    return Board(id="atlas", folder=tmp_path, title="Atlas", tags=tags,
                 items=(BoardItem(file="a.png", caption="a"),))


def test_old_renders_are_stale(tmp_path: Path) -> None:
    board = make_board(tmp_path, ("permanent",), 3)
    assert PermanentBoardRule().stale_note(board, NOW) == "renders 3 days old"


def test_fresh_renders_are_not_stale(tmp_path: Path) -> None:
    assert PermanentBoardRule().stale_note(make_board(tmp_path, ("permanent",), 1), NOW) is None


def test_normal_board_is_never_stale(tmp_path: Path) -> None:
    assert PermanentBoardRule().stale_note(make_board(tmp_path, (), 30), NOW) is None
