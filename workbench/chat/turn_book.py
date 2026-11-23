"""Shared state of all named chat turns: logs, pumps, holds and queued text.

One TurnBook per backend. Both chat runners keep their per-session turn
machinery here instead of private dicts, so the base ChatBackend can run
the turn lifecycle once for every backend.
"""

from __future__ import annotations

import asyncio
from collections import deque

from workbench.chat.chat_event import ChatEvent
from workbench.chat.turn_event_log import TurnEventLog


class TurnBook:
    """Track running turns, their logs and pumps, open holds and queued text."""

    def __init__(self) -> None:
        self._running: set[str] = set()
        self._logs: dict[str, TurnEventLog] = {}
        self._pumps: dict[str, asyncio.Task[None]] = {}
        self._holds: dict[str, set[str]] = {}
        self._queued: dict[str, deque[str]] = {}

    def is_running(self, name: str) -> bool:
        return name in self._running

    def begin(self, name: str, log: TurnEventLog, pump: asyncio.Task[None]) -> None:
        self._running.add(name)
        self._logs[name] = log
        self._pumps[name] = pump

    def end(self, name: str) -> None:
        self._running.discard(name)
        self._logs.pop(name, None)
        self._pumps.pop(name, None)

    def log_of(self, name: str) -> TurnEventLog | None:
        return self._logs.get(name)

    def pump_of(self, name: str) -> asyncio.Task[None] | None:
        return self._pumps.get(name)

    def offer(self, name: str, event: ChatEvent) -> None:
        log = self._logs.get(name)
        if log is not None:
            log.append(event)

    def hold(self, name: str, request_id: str) -> None:
        self._holds.setdefault(name, set()).add(request_id)

    def release(self, name: str, request_id: str) -> None:
        holds = self._holds.get(name)
        if holds is not None:
            holds.discard(request_id)

    def take_holds(self, name: str) -> frozenset[str]:
        return frozenset(self._holds.pop(name, set()))

    def enqueue(self, name: str, text: str) -> None:
        self._queued.setdefault(name, deque()).append(text)

    def dequeue(self, name: str) -> str | None:
        queued = self._queued.get(name)
        if queued is None:
            return None
        text = queued.popleft()
        if not queued:
            self._queued.pop(name, None)
        return text

    def drop_queue(self, name: str) -> None:
        self._queued.pop(name, None)
