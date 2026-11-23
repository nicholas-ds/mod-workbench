"""Tests: ChatShutdownJob idles in run and closes the resolver once."""

from __future__ import annotations

import asyncio
import contextlib

from workbench.chat.chat_backend_resolver import ChatBackendResolver
from workbench.chat.chat_backend_store import ChatBackendStore
from workbench.server.chat_shutdown_job import ChatShutdownJob


class NoHandoff:
    def build(self, name: str, from_label: str, events: object) -> str:
        return ""


class ClosingResolver(ChatBackendResolver):
    """Records close_all calls; the job must call it exactly once."""

    def __init__(self) -> None:
        super().__init__({}, ChatBackendStore(None), NoHandoff())
        self.close_all_calls = 0

    async def close_all(self) -> None:
        self.close_all_calls += 1


def test_run_waits_until_cancelled() -> None:
    job = ChatShutdownJob(ClosingResolver())

    async def drive() -> None:
        task = asyncio.create_task(job.run())
        await asyncio.sleep(0)
        assert not task.done()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    asyncio.run(drive())


def test_close_calls_the_resolver_once() -> None:
    resolver = ClosingResolver()
    job = ChatShutdownJob(resolver)

    async def drive() -> None:
        await job.close()

    asyncio.run(drive())
    assert resolver.close_all_calls == 1
