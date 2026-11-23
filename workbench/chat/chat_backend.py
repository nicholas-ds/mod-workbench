"""Backend ABC for the chat panes: shared turn machinery, backend-specific I/O.

run/follow/submit/stop/retire and the pump lifecycle are written once here;
a subclass implements the backend turn, interrupt, forget and read views.
Turn state (running, logs, pumps, holds, queues) lives in the TurnBook.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from workbench.chat.chat_command import COMMAND_CLEAR, ChatCommand
from workbench.chat.chat_event import ChatEvent, KIND_ERROR, KIND_HANDOFF, KIND_NOTICE, KIND_USER
from workbench.chat.handoff_inbox import HandoffInbox
from workbench.chat.handoff_notice import HandoffNoticeBuilder
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.session_summary import SessionSummary
from workbench.chat.slash_command_lister import SlashCommandInfo
from workbench.chat.turn_book import TurnBook
from workbench.chat.turn_event_log import TurnEventLog


@dataclass(frozen=True)
class BackendTraits:
    key: str
    label: str
    tab_mark: str
    session_label: str
    resume_template: str
    shows_context_percent: bool
    supports_slash_commands: bool
    supports_resume: bool

    def as_json(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "tab_mark": self.tab_mark,
            "session_label": self.session_label,
            "resume_template": self.resume_template,
            "shows_context_percent": self.shows_context_percent,
            "supports_slash_commands": self.supports_slash_commands,
            "supports_resume": self.supports_resume,
        }


@dataclass(frozen=True)
class SessionView:
    session_id: str
    context_percent: float | None


class ChatBackend(ABC):
    """Drive one chat turn at a time per named session, backend-agnostic."""

    def __init__(self, book: TurnBook, permissions: PendingPermissionStore) -> None:
        self._book = book
        self._permissions = permissions
        self._inbox = HandoffInbox()

    async def run(self, name: str, command: ChatCommand) -> AsyncIterator[ChatEvent]:
        if command.kind == COMMAND_CLEAR:
            await self.retire(name)
            yield ChatEvent(kind=KIND_NOTICE, text="Chat cleared.")
            return
        if self._book.is_running(name):
            yield ChatEvent(kind=KIND_ERROR, text="A turn is already running.")
            return
        log = self._start_turn(name, command.text, announced=False)
        async for event in log.follow():
            yield event

    async def follow(self, name: str) -> AsyncIterator[ChatEvent]:
        log = self._book.log_of(name)
        if log is None:
            return
        async for event in log.follow():
            yield event

    def is_running(self, name: str) -> bool:
        return self._book.is_running(name)

    async def submit(self, name: str, text: str) -> None:
        """Start a turn for server-sent text, or queue it behind the running turn."""
        if self._book.is_running(name):
            self._book.enqueue(name, text)
            return
        self._start_turn(name, text, announced=True)

    def receive_handoff(self, name: str, block: str) -> None:
        """Keep a handoff block; the next turn of this chat hands it to the model."""
        self._inbox.put(name, block)

    async def stop(self, name: str) -> None:
        await self._interrupt(name)
        self._deny_holds(name)

    async def retire(self, name: str) -> None:
        """Kill a retired chat: stop its turn, drop its memory and queued text."""
        await self.stop(name)
        await self._forget(name)
        self._book.drop_queue(name)

    def _start_turn(self, name: str, prompt: str, announced: bool) -> TurnEventLog:
        log = TurnEventLog()
        if announced:
            log.append(ChatEvent(kind=KIND_USER, text=prompt))
        self._book.begin(name, log, asyncio.create_task(self._pump(name, prompt, log)))
        return log

    async def _pump(self, name: str, prompt: str, log: TurnEventLog) -> None:
        handoff = self._inbox.take(name)
        try:
            await self._turn(name, prompt, log, handoff)
        except Exception as exc:
            if handoff and not self._was_announced(log):
                self._inbox.put(name, handoff)
            log.append(ChatEvent(kind=KIND_ERROR, text=str(exc)))
        finally:
            log.finish()
            self._deny_holds(name)
            self._book.end(name)
            self._start_queued(name)

    def _announce_handoff(self, log: TurnEventLog, handoff: str) -> None:
        """Show the author's chat that the model received a handoff."""
        log.append(HandoffNoticeBuilder().build(handoff))

    def _was_announced(self, log: TurnEventLog) -> bool:
        return any(event.kind == KIND_HANDOFF for event in log.events())

    def _start_queued(self, name: str) -> None:
        text = self._book.dequeue(name)
        if text is not None:
            self._start_turn(name, text, announced=True)

    def _deny_holds(self, name: str) -> None:
        for request_id in self._book.take_holds(name):
            self._permissions.answer(request_id, False)

    @abstractmethod
    async def _turn(
        self, name: str, prompt: str, log: TurnEventLog, handoff: str
    ) -> None: ...

    @abstractmethod
    async def _interrupt(self, name: str) -> None: ...

    @abstractmethod
    async def _forget(self, name: str) -> None: ...

    @abstractmethod
    async def session(self, name: str) -> SessionView: ...

    @abstractmethod
    async def history(self, name: str) -> tuple[ChatEvent, ...]: ...

    @abstractmethod
    async def commands(self, name: str) -> tuple[SlashCommandInfo, ...]: ...

    @abstractmethod
    async def sessions(self, name: str, folder: str) -> tuple[SessionSummary, ...]: ...

    @abstractmethod
    async def resume_session(
        self, name: str, folder: str, session_id: str
    ) -> bool: ...

    @property
    @abstractmethod
    def traits(self) -> BackendTraits: ...
