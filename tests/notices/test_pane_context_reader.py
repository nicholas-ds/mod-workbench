"""Tests for PaneContextReader."""

from pathlib import Path

from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.pane_context_reader import PaneContextReader


def owner() -> OwnerId:
    return OwnerId(kind=OwnerKind.PANE, key="main")


def reader_with(path: Path | None) -> PaneContextReader:
    return PaneContextReader(status_file_of=lambda _owner: path)


def write_status(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "status.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_none_path_gives_none(tmp_path: Path) -> None:
    assert reader_with(None).read(owner()) is None


def test_missing_file_gives_none(tmp_path: Path) -> None:
    assert reader_with(tmp_path / "absent.toml").read(owner()) is None


def test_invalid_toml_gives_none(tmp_path: Path) -> None:
    path = write_status(tmp_path, "not [valid toml")
    assert reader_with(path).read(owner()) is None


def test_missing_key_gives_none(tmp_path: Path) -> None:
    path = write_status(tmp_path, "wmux_surface = 'main'\n")
    assert reader_with(path).read(owner()) is None


def test_non_numeric_key_gives_none(tmp_path: Path) -> None:
    path = write_status(tmp_path, "context_percent = 'high'\n")
    assert reader_with(path).read(owner()) is None


def test_float_percent_is_returned(tmp_path: Path) -> None:
    path = write_status(tmp_path, "context_percent = 61.5\n")
    assert reader_with(path).read(owner()) == 61.5


def test_int_percent_is_coerced_to_float(tmp_path: Path) -> None:
    path = write_status(tmp_path, "context_percent = 42\n")
    result = reader_with(path).read(owner())
    assert result == 42.0
    assert isinstance(result, float)
