"""Tests for the board zipper (board archive step 3, revision 1)."""

import zipfile
from pathlib import Path

import pytest

from workbench.archive.archive_types import ArchiveCandidate
from workbench.archive.board_zipper import BoardZipper


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_dry_run_counts_and_writes_nothing(tmp_path: Path) -> None:
    board_dir = tmp_path / "done" / "b1"
    _write(board_dir / "board.md", b"title")
    _write(board_dir / "nested" / "shot.png", b"x" * 100)
    result = BoardZipper().archive(
        ArchiveCandidate(board_dir=board_dir), tmp_path, apply=False
    )
    assert result.board_dir == board_dir
    assert result.file_count == 2
    assert result.total_bytes == 5 + 100
    assert result.archived is False
    assert result.error == ""
    assert not (tmp_path / "archive").exists()
    assert board_dir.exists()


def test_apply_zips_and_removes_folder(tmp_path: Path) -> None:
    board_dir = tmp_path / "done" / "b1"
    note = _write(board_dir / "board.md", b"# board")
    answer = _write(board_dir / "nested" / "deep" / "answers.json", b"{}")
    total_bytes = note.stat().st_size + answer.stat().st_size
    result = BoardZipper().archive(
        ArchiveCandidate(board_dir=board_dir), tmp_path, apply=True
    )
    target = tmp_path / "archive" / "b1.zip"
    assert result.archived is True
    assert result.error == ""
    assert result.file_count == 2
    assert result.total_bytes == total_bytes
    assert target.exists()
    assert not board_dir.exists()
    with zipfile.ZipFile(target) as zf:
        assert zf.testzip() is None
        assert zf.read("b1/board.md") == b"# board"
        assert zf.read("b1/nested/deep/answers.json") == b"{}"
        compress_types = {info.compress_type for info in zf.infolist()}
    assert compress_types == {zipfile.ZIP_LZMA}


def test_existing_zip_is_not_overwritten(tmp_path: Path) -> None:
    board_dir = tmp_path / "done" / "b1"
    _write(board_dir / "board.md", b"new content")
    target = tmp_path / "archive" / "b1.zip"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"sentinel")
    result = BoardZipper().archive(
        ArchiveCandidate(board_dir=board_dir), tmp_path, apply=True
    )
    assert result.archived is False
    assert result.error == "zip already exists"
    assert result.file_count == 1
    assert target.read_bytes() == b"sentinel"
    assert board_dir.exists()
    assert not (tmp_path / "archive" / "b1.zip.tmp").exists()


def test_verify_failure_keeps_folder_and_no_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(BoardZipper, "_verify_zip", lambda *a, **k: False)
    board_dir = tmp_path / "done" / "b1"
    _write(board_dir / "board.md", b"data")
    result = BoardZipper().archive(
        ArchiveCandidate(board_dir=board_dir), tmp_path, apply=True
    )
    assert result.archived is False
    assert result.error == "verify failed"
    assert board_dir.exists()
    assert not (tmp_path / "archive" / "b1.zip").exists()
    assert not (tmp_path / "archive" / "b1.zip.tmp").exists()
