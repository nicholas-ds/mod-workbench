"""Tests for the LoopTracker factory."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from workbench.notices.loop_tracker import LoopTracker
from workbench.notices.loop_tracker_factory import LoopTrackerFactory


class FakePaneDirectory:
    """A pane directory with no entries."""

    def find(self, key: str) -> None:
        return None


def test_build_returns_tracker(tmp_path: Path) -> None:
    cfg = SimpleNamespace(repo=tmp_path)
    factory = LoopTrackerFactory(
        FakePaneDirectory(),
        lambda: datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc))
    tracker = factory.build(cfg)
    assert isinstance(tracker, LoopTracker)
