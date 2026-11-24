"""One board with two notices to one owner sends one stuck ping."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from workbench.notices.loop_stage_deriver import LoopStageDeriver
from workbench.notices.loop_tracker import LoopTracker
from workbench.notices.loop_types import OwnerSignal, StallLimits
from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId
from workbench.notices.owner_inbox import OwnerInbox
from workbench.notices.stuck_pinger import StuckPinger

NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
OWNER = OwnerId.parse("pane:main-orchestrator")
BOARD = "delivery-chips-rework"


class _UntakenSignalReader:
    """Reports that the owner never took any prompt."""

    def read(self, owner: OwnerId) -> OwnerSignal | None:
        return None


class _NoNewBoardDetector:
    """Reports that no new board appeared."""

    def raised_since(self, boards_dir: Path, owner: OwnerId, since: datetime,
                     board: str) -> bool:
        return False


class _RecordingDispatcher:
    """Collects the notices that got a ping."""

    def __init__(self) -> None:
        self.pinged: list[Notice] = []

    def ping(self, notice: Notice) -> DeliveryRecord:
        self.pinged.append(notice)
        return DeliveryRecord(notice_id=notice.id, owner=notice.owner,
                              state=DeliveryState.PENDING, attempts=1,
                              last_try="", error="")


def _iso(minutes_before_now: int) -> str:
    return (NOW - timedelta(minutes=minutes_before_now)).isoformat()


def _notice(notice_id: str, event: str, created: str) -> Notice:
    return Notice(id=notice_id, owner=OWNER, board=BOARD, event=event,
                  file_path="cards/delivery-chips.md", line="1", created=created)


def _deliver(inbox: OwnerInbox, notice: Notice, last_try: str) -> None:
    record = inbox.write(notice, True)
    inbox.update(DeliveryRecord(notice_id=record.notice_id, owner=record.owner,
                                state=DeliveryState.DELIVERED, attempts=1,
                                last_try=last_try, error=""))


def _tracker(inbox: OwnerInbox, boards_dir: Path) -> LoopTracker:
    return LoopTracker(inbox, _UntakenSignalReader(), _NoNewBoardDetector(),
                       LoopStageDeriver(StallLimits()), boards_dir, lambda: NOW)


def test_two_notices_one_board_one_owner_one_ping(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path / "inbox")
    _deliver(inbox, _notice("n1", "card", _iso(30)), _iso(10))
    _deliver(inbox, _notice("n2", "answer", _iso(20)), _iso(9))
    dispatcher = _RecordingDispatcher()
    pinger = StuckPinger(_tracker(inbox, tmp_path / "boards"), inbox, dispatcher)

    sent = pinger.ping_stuck(inbox.all_records())

    assert sent == 1
    assert [notice.id for notice in dispatcher.pinged] == ["n2"]


def test_one_notice_one_board_still_pings(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path / "inbox")
    _deliver(inbox, _notice("n1", "card", _iso(30)), _iso(10))
    dispatcher = _RecordingDispatcher()
    pinger = StuckPinger(_tracker(inbox, tmp_path / "boards"), inbox, dispatcher)

    sent = pinger.ping_stuck(inbox.all_records())

    assert sent == 1
    assert [notice.id for notice in dispatcher.pinged] == ["n1"]
