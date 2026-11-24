"""Tests for StuckPinger: one ping per stuck, never-yet-pinged record."""

from __future__ import annotations

from workbench.notices.loop_types import LoopSnapshot, LoopStage
from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId
from workbench.notices.stuck_pinger import StuckPinger


class _FakeTracker:
    """Returns the canned snapshot for every tracked record."""

    def __init__(self, snapshot: LoopSnapshot | None) -> None:
        self._snapshot = snapshot

    def track(self, record: DeliveryRecord) -> LoopSnapshot | None:
        return self._snapshot


class _FakeInbox:
    """In-memory inbox stand-in with per-notice-id pinged flags."""

    def __init__(self, notice: Notice | None) -> None:
        self._notice = notice
        self._pinged: set[str] = set()

    def notice_of(self, record: DeliveryRecord) -> Notice | None:
        return self._notice

    def was_pinged(self, record: DeliveryRecord) -> bool:
        return record.notice_id in self._pinged

    def mark_pinged(self, record: DeliveryRecord) -> None:
        self._pinged.add(record.notice_id)


class _FakeDispatcher:
    """Records pinged notices; raises on the nth ping when told to."""

    def __init__(self, fail_on_call: int = 0) -> None:
        self.pinged: list[Notice] = []
        self._calls = 0
        self._fail_on_call = fail_on_call

    def ping(self, notice: Notice) -> DeliveryRecord:
        self._calls += 1
        if self._calls == self._fail_on_call:
            raise RuntimeError("ping delivery failed")
        self.pinged.append(notice)
        return _record(notice.id)


def _snapshot(stage: LoopStage) -> LoopSnapshot:
    return LoopSnapshot(notice_id="n1", board="b", owner="o", stage=stage,
                        reason="quiet", since="", last_action="", summary="",
                        can_retry=False)


def _notice(event: str = "new_board", notice_id: str = "n1") -> Notice:
    return Notice(id=notice_id, owner=_owner(), board="b", event=event,
                  file_path="f.py", line="1", created="")


def _record(notice_id: str = "n1") -> DeliveryRecord:
    return DeliveryRecord(notice_id=notice_id, owner=_owner(),
                          state=DeliveryState.PENDING, attempts=1,
                          last_try="", error="")


def _owner() -> OwnerId:
    return OwnerId.parse("pane:dev")


def _pinger(tracker: _FakeTracker, inbox: _FakeInbox,
            dispatcher: _FakeDispatcher) -> StuckPinger:
    return StuckPinger(tracker, inbox, dispatcher)


def test_sends_one_ping_for_stuck_unpinged_record() -> None:
    notice = _notice()
    inbox = _FakeInbox(notice)
    dispatcher = _FakeDispatcher()
    pinger = _pinger(_FakeTracker(_snapshot(LoopStage.STUCK)), inbox, dispatcher)

    sent = pinger.ping_stuck([_record()])

    assert sent == 1
    assert dispatcher.pinged == [notice]
    assert inbox.was_pinged(_record())


def test_skips_already_pinged_record() -> None:
    notice = _notice()
    inbox = _FakeInbox(notice)
    dispatcher = _FakeDispatcher()
    pinger = _pinger(_FakeTracker(_snapshot(LoopStage.STUCK)), inbox, dispatcher)
    record = _record()
    inbox.mark_pinged(record)

    sent = pinger.ping_stuck([record])

    assert sent == 0
    assert dispatcher.pinged == []


def test_skips_record_whose_loop_is_not_stuck() -> None:
    inbox = _FakeInbox(_notice())
    dispatcher = _FakeDispatcher()
    pinger = _pinger(_FakeTracker(_snapshot(LoopStage.WORKING)), inbox, dispatcher)

    sent = pinger.ping_stuck([_record()])

    assert sent == 0
    assert dispatcher.pinged == []


def test_skips_notice_that_is_itself_a_ping() -> None:
    inbox = _FakeInbox(_notice(event="stuck"))
    dispatcher = _FakeDispatcher()
    pinger = _pinger(_FakeTracker(_snapshot(LoopStage.STUCK)), inbox, dispatcher)

    sent = pinger.ping_stuck([_record()])

    assert sent == 0
    assert dispatcher.pinged == []


def test_skips_record_without_tracked_snapshot() -> None:
    inbox = _FakeInbox(_notice())
    dispatcher = _FakeDispatcher()
    pinger = _pinger(_FakeTracker(None), inbox, dispatcher)

    sent = pinger.ping_stuck([_record()])

    assert sent == 0
    assert dispatcher.pinged == []


def test_continues_past_a_failing_ping() -> None:
    notice = _notice()
    inbox = _FakeInbox(notice)
    dispatcher = _FakeDispatcher(fail_on_call=1)
    pinger = _pinger(_FakeTracker(_snapshot(LoopStage.STUCK)), inbox, dispatcher)

    sent = pinger.ping_stuck([_record("n1"), _record("n2")])

    assert sent == 1
    assert dispatcher.pinged == [notice]
