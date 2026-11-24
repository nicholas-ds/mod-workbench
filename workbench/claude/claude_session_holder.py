"""One open Claude client and one reader task per chat (Task T3).

The holder owns the session lifecycle of a chat: open, send, idle close, and
explicit close for /clear and restart. Stream messages are translated and
offered to the shared TurnBook; a ResultMessage hands the session id and the
context percent to the on_result hook, then arms the idle timer. The idle
close waits while background jobs of the chat are still running.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from claude_agent_sdk import CanUseTool, ResultMessage

from workbench.chat.chat_job_book import ChatJobBook
from workbench.chat.chat_job_store import ChatJobStore
from workbench.claude.claude_job_recorder import ClaudeJobRecorder
from workbench.claude.claude_sdk_translator import ClaudeSdkTranslator
from workbench.claude.cli_pid_file import CliPidFile
from workbench.chat.session_id_store import SessionIdStore
from workbench.chat.turn_book import TurnBook

if TYPE_CHECKING:
    from workbench.claude.claude_chat_backend import ChatClient


class ClaudeSessionHolder:
    """Keep one open Claude client and one reader task per named chat."""

    def __init__(
        self,
        client_factory: Callable[[str, str, CanUseTool], ChatClient],
        session_store: SessionIdStore,
        translator: ClaudeSdkTranslator,
        book: TurnBook,
        job_book: ChatJobBook,
        job_store: ChatJobStore,
        job_recorder: ClaudeJobRecorder,
        pid_file: CliPidFile,
        on_result: Callable[[str, ResultMessage], Awaitable[None]],
        idle_seconds: float = 300.0,
    ) -> None:
        self._client_factory = client_factory
        self._session_store = session_store
        self._translator = translator
        self._book = book
        self._job_book = job_book
        self._job_store = job_store
        self._job_recorder = job_recorder
        self._pid_file = pid_file
        self._on_result = on_result
        self._idle_seconds = idle_seconds
        self._clients: dict[str, ChatClient] = {}
        self._timers: dict[str, asyncio.Task[None]] = {}
        self._readers: dict[str, asyncio.Task[None]] = {}
        self._failures: dict[str, str] = {}

    async def open(self, name: str, permission_callback: CanUseTool) -> ChatClient:
        """Return the open client of the chat, or connect one new client and reader."""
        client = self._clients.get(name)
        if client is not None:
            return client
        return await self._connect_client(name, permission_callback)

    def client_of(self, name: str) -> ChatClient | None:
        return self._clients.get(name)

    async def send(self, name: str, prompt: str) -> None:
        """Cancel the idle timer and hand the prompt to the open client."""
        self._cancel_timer(name)
        client = self._clients.get(name)
        if client is None:
            raise RuntimeError(f"No open Claude session for chat '{name}'.")
        await client.query(prompt)

    async def close(self, name: str) -> None:
        """Drop the timer, reader, client and pid file of one chat; safe to call twice."""
        self._cancel_timer(name)
        self._cancel_reader(name)
        client = self._clients.pop(name, None)
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception:
            pass
        self._pid_file.remove(name)

    async def close_all(self) -> None:
        """Close every open chat; used at server shutdown."""
        for name in list(self._clients):
            await self.close(name)

    async def close_unless_busy(self, name: str) -> None:
        """Close the chat when no background job of it is running."""
        if not self._has_running_jobs(name):
            await self.close(name)

    def failure_of(self, name: str) -> str:
        """The reason the reader of the chat died, empty when it did not fail."""
        return self._failures.get(name, "")

    def reader_of(self, name: str) -> asyncio.Task[None] | None:
        return self._readers.get(name)

    def pid_of(self, name: str) -> int | None:
        return self._pid_file.load(name)

    async def _connect_client(self, name: str, permission_callback: CanUseTool) -> ChatClient:
        client = self._client_factory(name, self._session_store.load(name), permission_callback)
        await client.connect()
        self._clients[name] = client
        self._save_cli_pid(name, client)
        self._failures.pop(name, None)
        self._start_reader(name, client)
        return client

    def _start_reader(self, name: str, client: ChatClient) -> None:
        if name in self._readers:
            return
        self._readers[name] = asyncio.create_task(self._read(name, client))

    async def _read(self, name: str, client: ChatClient) -> None:
        try:
            async for message in client.receive_messages():
                self._record_jobs(name, message)
                self._offer_events(name, message)
                if isinstance(message, ResultMessage):
                    await self._on_result(name, message)
                    self._start_timer(name)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._failures[name] = str(error)
        finally:
            await self.close(name)

    def _record_jobs(self, name: str, message: object) -> None:
        jobs = self._job_store.load(name)
        updated = self._job_recorder.record(name, message, jobs)
        if updated != jobs:
            self._job_store.save(name, updated)

    def _offer_events(self, name: str, message: object) -> None:
        for event in self._translator.translate(message):
            self._book.offer(name, event)

    def _start_timer(self, name: str) -> None:
        self._cancel_timer(name)
        self._timers[name] = asyncio.create_task(self._close_when_idle(name))

    async def _close_when_idle(self, name: str) -> None:
        while True:
            await asyncio.sleep(self._idle_seconds)
            if not self._has_running_jobs(name):
                break
        await self.close(name)

    def _has_running_jobs(self, name: str) -> bool:
        return bool(self._job_book.running(self._job_store.load(name)))

    def _cancel_timer(self, name: str) -> None:
        timer = self._timers.pop(name, None)
        if timer is None or timer is asyncio.current_task():
            return
        timer.cancel()

    def _cancel_reader(self, name: str) -> None:
        reader = self._readers.pop(name, None)
        if reader is None or reader is asyncio.current_task():
            return
        reader.cancel()

    def _save_cli_pid(self, name: str, client: ChatClient) -> None:
        pid = self._cli_pid_of(client)
        if pid is not None:
            self._pid_file.save(name, pid)

    # The SDK exposes no public pid, so read it through the private transport chain.
    def _cli_pid_of(self, client: ChatClient) -> int | None:
        pid = getattr(getattr(getattr(client, "_transport", None), "_process", None), "pid", None)
        return pid if isinstance(pid, int) else None
