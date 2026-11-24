"""Tests for PaneSignalReader."""

from __future__ import annotations

from pathlib import Path

from workbench.notices.loop_types import OwnerSignal
from workbench.notices.owner_id import OwnerId
from workbench.notices.pane_signal_reader import PaneSignalReader

_FULL_TOML = (
    'prompt_notice = "n1"\nprompt_at = "t1"\nactivity = "working"\n'
    'activity_at = "t2"\nlast_tool = "edit"\nlast_tool_at = "t3"\n'
    'phase = "code"\nsummary = "doing things"\n'
)


def _reader_for(path: Path | None) -> PaneSignalReader:
    return PaneSignalReader(lambda _owner: path)


def test_full_file_gives_all_fields(tmp_path: Path) -> None:
    path = tmp_path / "status.toml"
    path.write_text(_FULL_TOML, encoding="utf-8")
    signal = _reader_for(path).read(OwnerId.parse("pane:alpha"))
    assert signal == OwnerSignal(
        prompt_notice="n1",
        prompt_at="t1",
        activity="working",
        activity_at="t2",
        last_tool="edit",
        last_tool_at="t3",
        phase="code",
        summary="doing things",
    )


def test_missing_keys_give_empty_strings(tmp_path: Path) -> None:
    path = tmp_path / "status.toml"
    path.write_text('activity = "idle"\nextra = 3\n', encoding="utf-8")
    signal = _reader_for(path).read(OwnerId.parse("pane:alpha"))
    assert signal == OwnerSignal(activity="idle")


def test_missing_file_gives_none(tmp_path: Path) -> None:
    reader = _reader_for(tmp_path / "absent.toml")
    assert reader.read(OwnerId.parse("pane:alpha")) is None


def test_none_path_gives_none() -> None:
    reader = _reader_for(None)
    assert reader.read(OwnerId.parse("pane:alpha")) is None


def test_broken_toml_gives_none(tmp_path: Path) -> None:
    path = tmp_path / "status.toml"
    path.write_text("not [ valid toml", encoding="utf-8")
    reader = _reader_for(path)
    assert reader.read(OwnerId.parse("pane:alpha")) is None
