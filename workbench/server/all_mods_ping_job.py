"""The background job that sends stuck pings for every mod."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from workbench.core.config import ModConfig
from workbench.mods.mod_registry import ModRegistry
from workbench.notices.loop_tracker_factory import LoopTrackerFactory
from workbench.notices.notice_dispatcher_factory import NoticeDispatcherFactory
from workbench.notices.owner_inbox import OwnerInbox
from workbench.notices.stuck_pinger import StuckPinger
from workbench.server.background_job import BackgroundJob


class AllModsPingJob(BackgroundJob):
    """Ping the stuck notices of every mod on a fixed interval."""

    def __init__(self, registry: ModRegistry, tracker_factory: LoopTrackerFactory,
                 dispatcher_factory: NoticeDispatcherFactory,
                 sleep: Callable[[float], Awaitable[None]],
                 interval_seconds: float = 30.0) -> None:
        self._registry = registry
        self._tracker_factory = tracker_factory
        self._dispatcher_factory = dispatcher_factory
        self._sleep = sleep
        self._interval_seconds = interval_seconds

    def ping_all_once(self) -> int:
        """Ping every stuck notice of every mod; return the total pinged."""
        total = 0
        for result in self._registry.all():
            if not isinstance(result, ModConfig):
                continue
            try:
                inbox = OwnerInbox.of_mod(result.repo)
                pinger = StuckPinger(self._tracker_factory.build(result), inbox,
                                     self._dispatcher_factory.build(result))
                total += pinger.ping_stuck(inbox.all_records())
            except Exception:  # one bad mod must not stop the next
                pass
        return total

    async def run(self) -> None:
        """Run until cancelled: one pass over every mod, then sleep."""
        while True:
            self.ping_all_once()
            await self._sleep(self._interval_seconds)
