"""Replayable log of one chat turn's events with live follow support.

Stores every ChatEvent of a turn so a reader that arrives late can replay
the whole turn, then keep receiving live events until the turn finishes.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from workbench.chat.chat_event import ChatEvent


class TurnEventLog:
    """Records one turn's events; supports replay plus live followers."""

    def __init__(self) -> None:
        self._events: list[ChatEvent] = []
        self._subscribers: list[asyncio.Queue[ChatEvent | None]] = []
        self._finished = False

    def append(self, event: ChatEvent) -> None:
        if self._finished:
            return
        self._events.append(event)
        for queue in self._subscribers:
            queue.put_nowait(event)

    def finish(self) -> None:
        self._finished = True
        for queue in self._subscribers:
            queue.put_nowait(None)

    async def follow(self) -> AsyncIterator[ChatEvent]:
        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()
        for event in list(self._events):
            queue.put_nowait(event)
        if self._finished:
            queue.put_nowait(None)
        self._subscribers.append(queue)
        try:
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            self._subscribers.remove(queue)

    def events(self) -> tuple[ChatEvent, ...]:
        return tuple(self._events)

    def is_finished(self) -> bool:
        return self._finished
