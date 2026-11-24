"""Keeps only the still-active loop snapshots, sorted by urgency."""

from __future__ import annotations

from datetime import datetime, timezone

from workbench.notices.loop_types import LoopSnapshot, LoopStage

_DONE_MAX_SECONDS = 600
_OPEN_MAX_SECONDS = 21600
_STAGE_ORDER = (LoopStage.STUCK, LoopStage.WORKING, LoopStage.GOT_IT,
                LoopStage.SENDING, LoopStage.DONE)


class ActiveLoopFilter:
    """Selects the loops that still need attention, most urgent first."""

    def select(self, snapshots: list[LoopSnapshot], now: datetime) -> list[LoopSnapshot]:
        """Return the active snapshots by stage order, newest first, pure."""
        active = [s for s in snapshots if self._is_active(s, now)]
        active.sort(key=self._since_of, reverse=True)
        active.sort(key=lambda s: _STAGE_ORDER.index(s.stage))
        return active

    def _is_active(self, snapshot: LoopSnapshot, now: datetime) -> bool:
        """Whether the snapshot's stage is young enough, False for bad `since`."""
        try:
            since = self._since_of(snapshot)
        except ValueError:
            return False
        age = (now - since).total_seconds()
        limit = _DONE_MAX_SECONDS if snapshot.stage is LoopStage.DONE else _OPEN_MAX_SECONDS
        return age < limit

    def _since_of(self, snapshot: LoopSnapshot) -> datetime:
        """The parsed `since`, naive times read as UTC."""
        since = datetime.fromisoformat(snapshot.since)
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        return since
