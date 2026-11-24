"""The background job that redelivers pending notices of every mod."""

from __future__ import annotations

import anyio.to_thread
from collections.abc import Awaitable, Callable

from workbench.core.config import ModConfig
from workbench.mods.mod_registry import ModRegistry
from workbench.notices.delivery_retrier import DeliveryRetrier
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.notice_dispatcher_factory import NoticeDispatcherFactory
from workbench.notices.owner_inbox import OwnerInbox
from workbench.server.background_job import BackgroundJob


class AllModsRetryJob(BackgroundJob):
    """Redeliver the pending notices of every mod on a fixed interval."""

    def __init__(self, registry: ModRegistry, dispatcher_factory: NoticeDispatcherFactory,
                 sleep: Callable[[float], Awaitable[None]],
                 interval_seconds: float = 30.0) -> None:
        self._registry = registry
        self._dispatcher_factory = dispatcher_factory
        self._sleep = sleep
        self._interval_seconds = interval_seconds

    def retry_all_once(self) -> int:
        """Redeliver every pending notice of every mod; return the total tried."""
        total = 0
        for result in self._registry.all():
            if not isinstance(result, ModConfig):
                continue
            try:
                inbox = OwnerInbox.of_mod(result.repo)
                dispatcher: NoticeDispatcher = self._dispatcher_factory.build(result)
                retrier = DeliveryRetrier(inbox, dispatcher, self._sleep,
                                          self._interval_seconds)
                total += retrier.retry_once()
            except Exception:  # one bad mod must not stop the next
                pass
        return total

    async def run(self) -> None:
        """Run until cancelled: one pass over every mod, then sleep."""
        while True:
            await anyio.to_thread.run_sync(self.retry_all_once)
            await self._sleep(self._interval_seconds)
