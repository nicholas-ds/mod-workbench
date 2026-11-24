"""Tests for NewBoardDetector."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from workbench.notices.board_owner_store import BoardOwnerStore
from workbench.notices.new_board_detector import NewBoardDetector
from workbench.notices.owner_id import OwnerId, OwnerKind

def _since() -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=1)


def _board(tmp_path: Path, name: str, owner: OwnerId) -> Path:
    folder = tmp_path / "open" / name
    folder.mkdir(parents=True)
    BoardOwnerStore().write_once(folder, owner)
    return folder


def _raised(tmp_path: Path, owner: OwnerId, ignore_board: str = "old-board") -> bool:
    return NewBoardDetector(BoardOwnerStore()).raised_since(
        tmp_path / "open", owner, _since(), ignore_board
    )


def test_new_board_of_same_owner_gives_true(tmp_path: Path) -> None:
    _board(tmp_path, "fresh-board", OwnerId.parse("pane:alpha"))
    assert _raised(tmp_path, OwnerId(OwnerKind.PANE, "alpha"))


def test_board_named_like_ignore_board_gives_false(tmp_path: Path) -> None:
    _board(tmp_path, "old-board", OwnerId.parse("pane:alpha"))
    assert not _raised(tmp_path, OwnerId(OwnerKind.PANE, "alpha"))


def test_board_of_other_owner_gives_false(tmp_path: Path) -> None:
    _board(tmp_path, "fresh-board", OwnerId.parse("pane:beta"))
    assert not _raised(tmp_path, OwnerId(OwnerKind.PANE, "alpha"))


def test_board_stamped_before_since_gives_false(tmp_path: Path) -> None:
    folder = _board(tmp_path, "fresh-board", OwnerId.parse("pane:alpha"))
    stamp = folder / "owner.json"
    old = (_since() - timedelta(minutes=5)).timestamp()
    os.utime(stamp, (old, old))
    assert not _raised(tmp_path, OwnerId(OwnerKind.PANE, "alpha"))


def test_missing_boards_open_dir_gives_false(tmp_path: Path) -> None:
    assert not _raised(tmp_path, OwnerId(OwnerKind.PANE, "alpha"))
