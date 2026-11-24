"""Sends one stuck ping per stuck, never-yet-pinged delivery record."""

from __future__ import annotations

from workbench.notices.loop_tracker import LoopTracker
from workbench.notices.loop_types import LoopSnapshot, LoopStage
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.notice_types import DeliveryRecord, Notice
from workbench.notices.owner_inbox import OwnerInbox


class StuckPinger:
    """Pings each stuck notice once; the inbox pinged flag guards repeats."""

    def __init__(self, tracker: LoopTracker, inbox: OwnerInbox,
                 dispatcher: NoticeDispatcher) -> None:
        self._tracker = tracker
        self._inbox = inbox
        self._dispatcher = dispatcher

    def ping_stuck(self, records: list[DeliveryRecord]) -> int:
        """Send one ping per stuck, unpinged record; return the ping count."""
        sent = 0
        for record in records:
            sent += self._ping_one(record)
        return sent

    def _ping_one(self, record: DeliveryRecord) -> int:
        """Ping one record; 1 when sent, 0 when skipped or failed."""
        try:
            return self._ping_when_stuck(record)
        except Exception:
            return 0

    def _ping_when_stuck(self, record: DeliveryRecord) -> int:
        """Run the skip checks in order, then mark and ping; 1 when pinged."""
        if self._stuck_snapshot(record) is None:
            return 0
        notice = self._pingable_notice(record)
        if notice is None:
            return 0
        self._send_ping(record, notice)
        return 1

    def _stuck_snapshot(self, record: DeliveryRecord) -> LoopSnapshot | None:
        """The snapshot when the loop is stuck, None when untracked or not stuck."""
        snapshot = self._tracker.track(record)
        if snapshot is None or snapshot.stage is not LoopStage.STUCK:
            return None
        return snapshot

    def _pingable_notice(self, record: DeliveryRecord) -> Notice | None:
        """The notice to ping, None when missing, itself a ping, or pinged."""
        notice = self._inbox.notice_of(record)
        if notice is None or notice.event == "stuck":
            return None
        if self._inbox.was_pinged(record):
            return None
        return notice

    def _send_ping(self, record: DeliveryRecord, notice: Notice) -> None:
        """Mark pinged first, then ping; a crash between the two sends no ping."""
        self._inbox.mark_pinged(record)
        self._dispatcher.ping(notice)
