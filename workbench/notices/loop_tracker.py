"""Tracks the loop of delivered notices by joining reader, detector and deriver."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from workbench.notices.loop_stage_deriver import LoopStageDeriver
from workbench.notices.loop_types import LoopInputs, LoopSnapshot, OwnerSignal
from workbench.notices.new_board_detector import NewBoardDetector
from workbench.notices.notice_types import DeliveryRecord, Notice
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox
from workbench.notices.pane_signal_reader import PaneSignalReader


class LoopTracker:
    """Runs one tracking pass per delivered notice and stores the snapshot."""

    def __init__(self, inbox: OwnerInbox, signal_reader: PaneSignalReader,
                 detector: NewBoardDetector, deriver: LoopStageDeriver,
                 boards_open_dir: Path, clock: Callable[[], datetime]) -> None:
        self._inbox = inbox
        self._signal_reader = signal_reader
        self._detector = detector
        self._deriver = deriver
        self._boards_open_dir = boards_open_dir
        self._clock = clock

    def track(self, record: DeliveryRecord) -> LoopSnapshot | None:
        """Follow one delivered notice through the loop, None when untracked."""
        notice = self._tracked_notice(record)
        if notice is None:
            return None
        signal = self._signal(record.owner)
        new_board_since = self._new_board_since(record, notice)
        snapshot = self._snapshot(record, notice, signal, new_board_since)
        self._store(record, snapshot)
        return snapshot

    def _tracked_notice(self, record: DeliveryRecord) -> Notice | None:
        """The stored notice of a pane owner, None for missing or chat owners."""
        notice = self._inbox.notice_of(record)
        if notice is None or record.owner.kind is not OwnerKind.PANE:
            return None
        return notice

    def _signal(self, owner: OwnerId) -> OwnerSignal | None:
        """What the owner's pane reports about its taken prompt."""
        return self._signal_reader.read(owner)

    def _new_board_since(self, record: DeliveryRecord, notice: Notice) -> bool:
        """Whether a new board of this owner appeared since the last try."""
        try:
            since = datetime.fromisoformat(record.last_try)
        except ValueError:
            return False
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        return self._detector.raised_since(self._boards_open_dir, record.owner,
                                           since.astimezone(timezone.utc), notice.board)

    def _snapshot(self, record: DeliveryRecord, notice: Notice, signal: OwnerSignal | None,
                  new_board_since: bool) -> LoopSnapshot:
        """Derive the loop state from the gathered inputs."""
        return self._deriver.derive(LoopInputs(record=record, notice=notice, signal=signal,
                                               new_board_since=new_board_since,
                                               now=self._clock()))

    def _store(self, record: DeliveryRecord, snapshot: LoopSnapshot) -> None:
        """Store the snapshot only when it differs from the stored one."""
        if self._inbox.loop_of(record) != snapshot:
            self._inbox.update_loop(record, snapshot)
