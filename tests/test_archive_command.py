"""Tests for the archive command end to end (board archive step 6, revision 1)."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from workbench.__main__ import WorkbenchCommands
from workbench.mod_init import ModInitializer

NOW = datetime.now(timezone.utc)


def _old_board(root: Path) -> Path:
    repo = root / "mod-a"
    repo.mkdir()
    ModInitializer().init(repo, "Mod A", root)
    board = repo / "boards" / "done" / "old-board"
    note = board / "board.md"
    note.parent.mkdir(parents=True)
    note.write_bytes(b"# old board")
    png = board / "a.png"
    png.write_bytes(b"\0" * 100)
    stamp = (NOW - timedelta(days=60)).timestamp()
    for path in (note, png):
        os.utime(path, (stamp, stamp))
    return board


def test_dry_run_lists_board_and_changes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    board = _old_board(tmp_path)
    monkeypatch.setenv("WORKBENCH_ROOTS", str(tmp_path))

    code = WorkbenchCommands().run(["archive"])

    out = capsys.readouterr().out
    assert code == 0
    assert "dry run" in out
    assert "old-board: 2 files" in out
    assert board.exists()
    assert not (tmp_path / "mod-a" / "boards" / "archive").exists()


def test_apply_zips_board_and_removes_folder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    board = _old_board(tmp_path)
    monkeypatch.setenv("WORKBENCH_ROOTS", str(tmp_path))

    code = WorkbenchCommands().run(["archive", "--apply"])

    out = capsys.readouterr().out
    assert code == 0
    assert "applied" in out
    assert "zipped" in out
    zip_path = tmp_path / "mod-a" / "boards" / "archive" / "old-board.zip"
    assert zip_path.is_file()
    assert not board.exists()


def test_second_apply_finds_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _old_board(tmp_path)
    monkeypatch.setenv("WORKBENCH_ROOTS", str(tmp_path))
    WorkbenchCommands().run(["archive", "--apply"])
    capsys.readouterr()

    code = WorkbenchCommands().run(["archive", "--apply"])

    assert code == 0
    assert "Nothing to archive." in capsys.readouterr().out


def test_days_90_finds_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    board = _old_board(tmp_path)
    monkeypatch.setenv("WORKBENCH_ROOTS", str(tmp_path))

    code = WorkbenchCommands().run(["archive", "--days", "90"])

    assert code == 0
    assert "Nothing to archive." in capsys.readouterr().out
    assert board.exists()
