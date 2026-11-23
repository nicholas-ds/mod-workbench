"""Server job that closes every chat backend's child processes at shutdown."""

from __future__ import annotations

import asyncio

from workbench.chat.chat_backend_resolver import ChatBackendResolver
from workbench.server.background_job import BackgroundJob


class ChatShutdownJob(BackgroundJob):
    """Idle for the server's whole lifespan; on close, stop the backends."""

    def __init__(self, resolver: ChatBackendResolver) -> None:
        self._resolver = resolver

    async def run(self) -> None:
        await asyncio.Event().wait()

    async def close(self) -> None:
        await self._resolver.close_all()
