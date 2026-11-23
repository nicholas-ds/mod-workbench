"""Tests for safe item resolution and item kind detection."""

from pathlib import Path

import pytest

from workbench.boards.board_types import BoardError
from workbench.boards.item_files import ItemKindDetector, SafeItemResolver


def make_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "board-1"
    folder.mkdir()
    (folder / "layout.png").write_bytes(b"fake png")
    return folder


def test_escape_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path)
    (tmp_path / "outside.png").write_bytes(b"fake png")
    with pytest.raises(BoardError) as raised:
        SafeItemResolver().resolve(folder, "../outside.png")
    assert raised.value.folder == folder
    assert "outside.png" in raised.value.reason


def test_absolute_path_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path)
    with pytest.raises(BoardError) as raised:
        SafeItemResolver().resolve(folder, "/abs.png")
    assert raised.value.folder == folder


def test_missing_file_rejected(tmp_path: Path) -> None:
    folder = make_folder(tmp_path)
    with pytest.raises(BoardError):
        SafeItemResolver().resolve(folder, "missing.png")


def test_existing_file_resolves_inside_folder(tmp_path: Path) -> None:
    folder = make_folder(tmp_path)
    resolved = SafeItemResolver().resolve(folder, "layout.png")
    assert resolved == (folder / "layout.png").resolve()


def test_kind_by_extension() -> None:
    detector = ItemKindDetector()
    cases = {
        "a.png": "image", "a.jpg": "image", "a.jpeg": "image", "a.webp": "image",
        "a.gif": "image", "a.swf": "swf", "a.html": "html", "a.htm": "html",
        "a.svg": "svg", "a.txt": "text", "a.md": "text", "a.dat": "other",
    }
    for name, kind in cases.items():
        assert detector.detect(Path(name)) == kind, name
