import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import thread_archiver
from thread_archiver import ThreadArchiver

NOW = datetime(2026, 11, 8, 12, 30, 0, tzinfo=timezone.utc)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_locked_move_skips_that_file_and_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "messages" / "done" / "a.md", "a\n")
    _write(tmp_path / "messages" / "done" / "b.md", "b\n")
    real_move = shutil.move

    def flaky_move(src: str, dst: str) -> None:
        if str(dst).endswith("a.md"):
            raise OSError("target exists")
        real_move(src, dst)

    monkeypatch.setattr(thread_archiver.shutil, "move", flaky_move)
    archive = ThreadArchiver().archive(tmp_path, NOW)
    assert archive is not None
    assert (archive / "done" / "b.md").exists()
    assert (tmp_path / "messages" / "done" / "a.md").exists()


def test_unreadable_cli_file_is_skipped(tmp_path: Path) -> None:
    _write(tmp_path / "messages" / "cli.md", "---\nview: cli\n---\nhello\n")
    (tmp_path / "messages" / "locked.md").mkdir()
    archive = ThreadArchiver().archive(tmp_path, NOW)
    assert archive is not None
    assert (archive / "cli.md").exists()
    assert (tmp_path / "messages" / "locked.md").is_dir()


def test_done_and_replies_files_move(tmp_path: Path) -> None:
    done = tmp_path / "messages" / "done" / "b1.md"
    reply = tmp_path / "messages" / "replies" / "a1.md"
    _write(done, "---\nview: board\n---\nanswer\n")
    _write(reply, "my reply\n")
    archive = ThreadArchiver().archive(tmp_path, NOW)
    assert archive == tmp_path / "messages" / "archive" / "20261108T123000"
    assert (archive / "done" / "b1.md").exists()
    assert (archive / "replies" / "a1.md").exists()
    assert not done.exists() and not reply.exists()


def test_cli_view_message_moves(tmp_path: Path) -> None:
    cli = tmp_path / "messages" / "20261108T120000+0000-1.md"
    _write(cli, "---\ncreated: 'x'\nview: cli\n---\nhello\n")
    archive = ThreadArchiver().archive(tmp_path, NOW)
    assert (archive / "20261108T120000+0000-1.md").exists()
    assert not cli.exists()


def test_unhandled_workbench_view_message_stays(tmp_path: Path) -> None:
    board = tmp_path / "messages" / "20261108T120000+0000-2.md"
    _write(board, "---\nview: board\n---\ntext\n")
    ThreadArchiver().archive(tmp_path, NOW)
    assert board.exists()


def test_nothing_to_move_returns_none(tmp_path: Path) -> None:
    _write(tmp_path / "messages" / "note.md", "---\nview: board\n---\ntext\n")
    assert ThreadArchiver().archive(tmp_path, NOW) is None
    assert not (tmp_path / "messages" / "archive").exists()
