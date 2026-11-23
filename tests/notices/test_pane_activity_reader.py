"""Tests for PaneActivityReader: idle, busy and missing status files."""

from pathlib import Path

from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.pane_activity_reader import PaneActivityReader

OWNER = OwnerId(OwnerKind.PANE, "main-orchestrator")


def _reader(status_file: Path | None) -> PaneActivityReader:
    return PaneActivityReader(lambda owner: status_file)


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "main-orchestrator.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_idle_when_activity_is_idle(tmp_path: Path) -> None:
    path = _write(tmp_path, 'wmux_surface = "s1"\nactivity = "idle"\n')

    assert _reader(path).is_idle(OWNER) is True


def test_busy_when_activity_is_busy(tmp_path: Path) -> None:
    path = _write(tmp_path, 'activity = "busy"\n')

    assert _reader(path).is_idle(OWNER) is False


def test_false_when_key_missing(tmp_path: Path) -> None:
    path = _write(tmp_path, 'wmux_surface = "s1"\n')

    assert _reader(path).is_idle(OWNER) is False


def test_false_when_file_missing(tmp_path: Path) -> None:
    assert _reader(tmp_path / "gone.toml").is_idle(OWNER) is False


def test_false_when_no_status_file(tmp_path: Path) -> None:
    assert _reader(None).is_idle(OWNER) is False
