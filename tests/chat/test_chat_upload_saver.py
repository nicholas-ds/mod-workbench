"""Tests for the chat upload saver."""

from pathlib import Path

import pytest

from workbench.chat.chat_upload_saver import ChatUploadSaver


def test_save_writes_bytes_and_returns_a_forward_slash_path(tmp_path: Path) -> None:
    path = ChatUploadSaver().save(str(tmp_path), "notes.txt", b"hello")
    assert path == (tmp_path / "uploads" / "notes.txt").as_posix()
    assert (tmp_path / "uploads" / "notes.txt").read_bytes() == b"hello"


def test_save_creates_the_gitignore_with_one_star_line(tmp_path: Path) -> None:
    ChatUploadSaver().save(str(tmp_path), "a.txt", b"x")
    gitignore = tmp_path / "uploads" / ".gitignore"
    assert gitignore.read_text(encoding="utf-8") == "*\n"


def test_the_same_name_twice_gets_a_number_before_the_extension(
        tmp_path: Path) -> None:
    saver = ChatUploadSaver()
    first = saver.save(str(tmp_path), "name.txt", b"one")
    second = saver.save(str(tmp_path), "name.txt", b"two")
    assert first.endswith("uploads/name.txt")
    assert second.endswith("uploads/name-2.txt")
    assert (tmp_path / "uploads" / "name.txt").read_bytes() == b"one"
    assert (tmp_path / "uploads" / "name-2.txt").read_bytes() == b"two"


def test_path_parts_and_backslashes_end_in_a_plain_uploads_name(
        tmp_path: Path) -> None:
    saver = ChatUploadSaver()
    slash = saver.save(str(tmp_path), "../../evil.txt", b"a")
    backslash = saver.save(str(tmp_path), "C:\\x\\evil.txt", b"b")
    uploads = tmp_path / "uploads"
    assert Path(slash).parent == uploads
    assert Path(backslash).parent == uploads
    assert slash.endswith("uploads/evil.txt")
    assert backslash.endswith("uploads/evil-2.txt")


def test_empty_data_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ChatUploadSaver().save(str(tmp_path), "a.txt", b"")


def test_data_over_max_bytes_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ChatUploadSaver(max_bytes=10).save(str(tmp_path), "a.txt", b"x" * 11)


def test_max_bytes_is_readable() -> None:
    assert ChatUploadSaver(max_bytes=5).max_bytes == 5
