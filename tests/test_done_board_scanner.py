"""Tests for the done-board scanner (board archive step 2, revision 1)."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from workbench.archive_policy import ArchivePolicy
from workbench.archive_types import ArchiveCandidate
from workbench.done_board_scanner import DONE_DIR_NAME, DoneBoardScanner

NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)


def _write(path: Path, size: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)
    return path


def _touch(path: Path, days_old: int) -> None:
    stamp = (NOW - timedelta(days=days_old)).timestamp()
    os.utime(path, (stamp, stamp))


def test_open_board_is_ignored(tmp_path: Path) -> None:
    note = _write(tmp_path / "open" / "b1" / "board.md", 10)
    _touch(note, 40)
    assert DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW) == ()


def test_young_board_is_skipped(tmp_path: Path) -> None:
    note = _write(tmp_path / "done" / "b1" / "board.md", 10)
    _touch(note, 5)
    assert DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW) == ()


def test_missing_done_folder_gives_empty(tmp_path: Path) -> None:
    assert DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW) == ()


def test_small_non_png_file_qualifies(tmp_path: Path) -> None:
    note = _write(tmp_path / "done" / "b1" / "board.md", 10)
    _touch(note, 40)
    candidates = DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW)
    assert candidates == (ArchiveCandidate(board_dir=tmp_path / "done" / "b1"),)


def test_small_png_file_qualifies(tmp_path: Path) -> None:
    png = _write(tmp_path / "done" / "b1" / "shot.png", 100)
    _touch(png, 40)
    candidates = DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW)
    assert candidates == (ArchiveCandidate(board_dir=tmp_path / "done" / "b1"),)


def test_exactly_min_age_days_qualifies(tmp_path: Path) -> None:
    note = _write(tmp_path / "done" / "b1" / "board.md", 10)
    _touch(note, 30)
    candidates = DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW)
    assert len(candidates) == 1


def test_newest_file_decides_age(tmp_path: Path) -> None:
    old = _write(tmp_path / "done" / "b1" / "board.md", 10)
    young = _write(tmp_path / "done" / "b1" / "answers.json", 10)
    _touch(old, 40)
    _touch(young, 2)
    assert DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW) == ()


def test_empty_board_folder_is_skipped(tmp_path: Path) -> None:
    (tmp_path / DONE_DIR_NAME / "b1").mkdir(parents=True)
    assert DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW) == ()


def test_candidates_are_sorted(tmp_path: Path) -> None:
    b2 = _write(tmp_path / "done" / "b2" / "board.md", 10)
    b1 = _write(tmp_path / "done" / "b1" / "board.md", 10)
    _touch(b2, 40)
    _touch(b1, 40)
    candidates = DoneBoardScanner().scan(tmp_path, ArchivePolicy(), NOW)
    assert [candidate.board_dir for candidate in candidates] == [
        tmp_path / "done" / "b1",
        tmp_path / "done" / "b2",
    ]
