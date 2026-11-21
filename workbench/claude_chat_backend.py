"""Run chat turns against one Claude client per named session (rule R8).

Each turn drops the previous client and connects a fresh one with the stored
session id, so the SDK session resumes. The turn lifecycle (pumps, queues,
permission holds) lives in the base ChatBackend; this subclass does only the
Claude SDK I/O: connect, query, translate, interrupt and the read views.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Protocol

from claude_agent_sdk import (
    CanUseTool,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    ToolPermissionContext,
)

from workbench.chat_backend import BackendTraits, ChatBackend, SessionView
from workbench.chat_event import ChatEvent
from workbench.chat_history_loader import ChatHistoryLoader
from workbench.claude_sdk_translator import ClaudeSdkTranslator
from workbench.permission_card_builder import PermissionCardBuilder
from workbench.pending_permission_store import PendingPermissionStore
from workbench.session_history_lister import SessionHistoryLister
from workbench.session_id_store import SessionIdStore
from workbench.session_summary import SessionSummary
from workbench.slash_command_lister import SlashCommandInfo, SlashCommandLister
from workbench.turn_book import TurnBook
from workbench.turn_event_log import TurnEventLog


class ChatClient(Protocol):
    async def connect(self) -> None: ...
    async def query(self, prompt: str) -> None: ...
    async def receive_response(self) -> AsyncIterator[object]: ...
    async def interrupt(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def get_server_info(self) -> dict[str, object] | None: ...
    async def get_context_usage(self) -> dict[str, object]: ...


ClientFactory = Callable[[str, str, CanUseTool], ChatClient]


class ClaudeChatBackend(ChatBackend):
    """Drive one chat turn at a time per named session."""

    def __init__(
        self,
        book: TurnBook,
        client_factory: ClientFactory,
        store: SessionIdStore,
        translator: ClaudeSdkTranslator,
        permissions: PendingPermissionStore,
        cards: PermissionCardBuilder,
        history_loader: ChatHistoryLoader,
        slash_lister: SlashCommandLister,
        session_lister: SessionHistoryLister,
        timeout_seconds: float = 600.0,
        on_permission_wait: Callable[[str, str], None] = lambda name, tool_name: None,
        alert_after_seconds: float = 30.0,
    ) -> None:
        super().__init__(book, permissions)
        self._client_factory = client_factory
        self._store = store
        self._translator = translator
        self._cards = cards
        self._timeout_seconds = timeout_seconds
        self._on_permission_wait = on_permission_wait
        self._alert_after_seconds = alert_after_seconds
        self._history_loader = history_loader
        self._slash_lister = slash_lister
        self._session_lister = session_lister
        self._clients: dict[str, ChatClient] = {}
        self._context_percent: dict[str, float] = {}

    @property
    def traits(self) -> BackendTraits:
        return BackendTraits(
            key="claude",
            label="Claude",
            tab_mark="",
            session_label="Session",
            resume_template="claude --resume {session_id}",
            shows_context_percent=True,
            supports_slash_commands=True,
            supports_resume=True,
        )

    def context_percent(self, name: str) -> float | None:
        """Return the context window percent measured after the last finished turn."""
        return self._context_percent.get(name)

    async def session(self, name: str) -> SessionView:
        return SessionView(self._store.load(name), self._context_percent.get(name))

    async def history(self, name: str) -> tuple[ChatEvent, ...]:
        return self._history_loader.load(name)

    async def commands(self, name: str) -> tuple[SlashCommandInfo, ...]:
        rows = self._slash_lister.list(await self.server_info(name))
        if any(row.name == "resume" for row in rows):
            return rows
        built_in = SlashCommandInfo(
            name="resume", description="Resume an earlier session")
        return tuple(sorted(rows + (built_in,), key=lambda row: row.name))

    async def sessions(self, name: str, folder: str) -> tuple[SessionSummary, ...]:
        return await asyncio.to_thread(self._session_lister.list, folder)

    async def resume_session(
        self, name: str, folder: str, session_id: str
    ) -> bool:
        if self._book.is_running(name):
            return False
        listed = await self.sessions(name, folder)
        if session_id not in {row.session_id for row in listed}:
            return False
        await self._drop_client(name)
        self._context_percent.pop(name, None)
        self._store.save(name, session_id)
        return True

    async def server_info(self, name: str) -> dict[str, object] | None:
        """Return the server init info. An idle client is dropped again so terminal turns stay visible."""
        client = await self._connected_client(name)
        info = await client.get_server_info()
        if not self._book.is_running(name):
            await self._drop_client(name)
        return info

    async def _turn(
        self, name: str, prompt: str, log: TurnEventLog, handoff: str
    ) -> None:
        try:
            client = await self._connected_client(name)
            if handoff:
                self._announce_handoff(log, handoff)
            await client.query(f"{handoff}\n\n{prompt}" if handoff else prompt)
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    self._store.save(name, message.session_id)
                    await self._remember_context_percent(name, client)
                for event in self._translator.translate(message):
                    log.append(event)
        except Exception:
            await self._drop_client(name)
            raise
        finally:
            await self._drop_client(name)

    async def _interrupt(self, name: str) -> None:
        client = self._clients.get(name)
        if client is None:
            return
        await client.interrupt()

    async def _forget(self, name: str) -> None:
        await self._drop_client(name)
        self._context_percent.pop(name, None)
        self._store.forget(name)

    async def _remember_context_percent(self, name: str, client: ChatClient) -> None:
        try:
            usage = await client.get_context_usage()
        except Exception:
            return
        self._context_percent[name] = float(usage["percentage"])

    def _permission_callback(self, name: str) -> CanUseTool:
        async def callback(
            tool_name: str, tool_input: dict, context: ToolPermissionContext
        ) -> PermissionResult:
            request_id = self._permissions.hold()
            self._book.hold(name, request_id)
            self._book.offer(name, self._cards.build(
                request_id, tool_name, tool_input, context.title, context.display_name))
            alert = asyncio.create_task(self._alert_later(name, tool_name))
            outcome = await self._permissions.await_decision(request_id, self._timeout_seconds)
            alert.cancel()
            self._book.release(name, request_id)
            self._book.offer(name, self._cards.settle(request_id, outcome))
            return self._result_of(outcome)

        return callback

    async def _alert_later(self, name: str, tool_name: str) -> None:
        await asyncio.sleep(self._alert_after_seconds)
        self._on_permission_wait(name, tool_name)

    def _result_of(self, outcome: str) -> PermissionResult:
        if outcome == "allowed":
            return PermissionResultAllow()
        if outcome == "timed out":
            return PermissionResultDeny(message="The author did not answer in time.")
        return PermissionResultDeny(message="The author denied this request.")

    async def _connected_client(self, name: str) -> ChatClient:
        client = self._clients.get(name)
        if client is None:
            client = self._client_factory(
                name, self._store.load(name), self._permission_callback(name)
            )
            await client.connect()
            self._clients[name] = client
        return client

    async def _drop_client(self, name: str) -> None:
        client = self._clients.pop(name, None)
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception:
            pass
