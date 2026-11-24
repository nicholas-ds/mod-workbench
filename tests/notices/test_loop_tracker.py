"""Tests for LoopTracker: the pipeline joining reader, detector and deriver."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from workbench.notices.loop_stage_deriver import LoopStageDeriver
from workbench.notices.loop_tracker import LoopTracker
from workbench.notices.loop_types import LoopSnapshot, LoopStage, OwnerSignal, StallLimits
from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox

_NOW = datetime(2026, 11, 24, 12, 0, 20, tzinfo=timezone.utc)


def _clock() -> datetime:
    return _NOW


class _FakeSignalReader:
    """Hands back a fixed signal for any owner."""

    def __init__(self, signal: OwnerSignal | None) -> None:
        self._signal = signal

    def read(self, owner: OwnerId) -> OwnerSignal | None:
        return self._signal


class _FakeDetector:
    """Always answers with a fixed boolean."""

    def __init__(self, answer: bool) -> None:
        self._answer = answer

    def raised_since(self, boards_open_dir: Path, owner: OwnerId, since: datetime,
                     ignore_board: str) -> bool:
        return self._answer


class _SpyInbox(OwnerInbox):
    """A real inbox that counts update_loop calls."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.updates = 0

    def update_loop(self, record: DeliveryRecord, snapshot: LoopSnapshot) -> None:
        self.updates += 1
        super().update_loop(record, snapshot)


def _notice(notice_id: str, owner: OwnerId) -> Notice:
    return Notice(id=notice_id, owner=owner, board="b1", event="answer",
                  file_path="boards/open/b1/board.md", line="hello",
                  created="2026-11-24T11:59:00+00:00")


def _record(notice_id: str, owner: OwnerId) -> DeliveryRecord:
    return DeliveryRecord(notice_id=notice_id, owner=owner, state=DeliveryState.DELIVERED,
                          attempts=1, last_try="2026-11-24T12:00:00+00:00", error="")


def _taken_signal() -> OwnerSignal:
    return OwnerSignal(prompt_notice="b1 answer", prompt_at="2026-11-24T12:00:05+00:00",
                       activity="working", activity_at="2026-11-24T12:00:07+00:00",
                       last_tool="write", last_tool_at="2026-11-24T12:00:10+00:00",
                       phase="", summary="")


def _tracker(inbox: OwnerInbox, signal: OwnerSignal | None, root: Path) -> LoopTracker:
    return LoopTracker(inbox=inbox, signal_reader=_FakeSignalReader(signal),
                       detector=_FakeDetector(False), deriver=LoopStageDeriver(StallLimits()),
                       boards_open_dir=root / "boards" / "open", clock=_clock)


def test_track_pane_owner_working_stores_snapshot(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    owner = OwnerId(OwnerKind.PANE, "boards-1")
    inbox.write(_notice("n1", owner), True)
    record = _record("n1", owner)
    tracker = _tracker(inbox, _taken_signal(), tmp_path)

    snapshot = tracker.track(record)

    assert snapshot is not None
    assert snapshot.stage is LoopStage.WORKING
    assert inbox.loop_of(record) == snapshot


def test_track_skips_chat_owners(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    owner = OwnerId(OwnerKind.CHAT, "review")
    inbox.write(_notice("n1", owner), True)
    tracker = _tracker(inbox, _taken_signal(), tmp_path)

    assert tracker.track(_record("n1", owner)) is None
    assert inbox.loop_of(_record("n1", owner)) is None


def test_track_returns_none_when_notice_is_missing(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    owner = OwnerId(OwnerKind.PANE, "boards-1")
    ghost = _record("ghost", owner)
    tracker = _tracker(inbox, _taken_signal(), tmp_path)

    assert tracker.track(ghost) is None


def test_second_track_with_unchanged_inputs_does_not_rewrite(tmp_path: Path) -> None:
    inbox = _SpyInbox(tmp_path)
    owner = OwnerId(OwnerKind.PANE, "boards-1")
    inbox.write(_notice("n1", owner), True)
    record = _record("n1", owner)
    tracker = _tracker(inbox, _taken_signal(), tmp_path)

    tracker.track(record)
    tracker.track(record)

    assert inbox.updates == 1
    assert inbox.loop_of(record) is not None
