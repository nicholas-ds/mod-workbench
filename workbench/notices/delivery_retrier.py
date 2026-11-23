"""Redelivery of pending notices on a fixed interval."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.owner_inbox import OwnerInbox


class DeliveryRetrier:
    """Redeliver every pending notice record, one pass per interval."""

    def __init__(self, inbox: OwnerInbox, dispatcher: NoticeDispatcher,
                 sleep: Callable[[float], Awaitable[None]],
                 interval_seconds: float = 30.0) -> None:
        self._inbox = inbox
        self._dispatcher = dispatcher
        self._sleep = sleep
        self._interval_seconds = interval_seconds

    def retry_once(self) -> int:
        """Redeliver every pending record; return how many records it tried."""
        records = self._inbox.pending()
        for record in records:
            self._dispatcher.redeliver(record)
        return len(records)

    async def run(self) -> None:
        """Loop forever: one pass, then sleep; a bad pass never stops the loop."""
        while True:
            try:
                self.retry_once()
            except Exception:  # one bad record must not stop the loop
                pass
            await self._sleep(self._interval_seconds)
