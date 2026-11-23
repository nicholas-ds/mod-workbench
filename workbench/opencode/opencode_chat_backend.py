"""Drive OpenCode chat turns over HTTP: connect, prompt and interrupt.

Mirrors ClaudeChatBackend for the HTTP side: the turn lifecycle (pumps,
queues, permission holds) lives in the base ChatBackend; this subclass
does the OpenCode I/O — session reuse or creation, the handoff synthetic,
the busy check, the poll loop handed to OpencodeTurnFollower, and the
server-side session delete when a chat is forgotten.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from workbench.chat.chat_backend import BackendTraits, ChatBackend, SessionView
from workbench.chat.chat_event import ChatEvent
from workbench.opencode.opencode_history import OpencodeHistoryLoader
from workbench.opencode.opencode_http_client import OpencodeHttpClient
from workbench.opencode.opencode_turn_follower import OpencodeTurnFollower
from workbench.chat.orchestrator_directory import OrchestratorDirectory
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.session_id_store import SessionIdStore
from workbench.chat.session_summary import SessionSummary
from workbench.chat.slash_command_lister import SlashCommandInfo
from workbench.chat.turn_book import TurnBook
from workbench.chat.turn_event_log import TurnEventLog


HANDOFF_SETTLE_SECONDS = 120.0
HANDOFF_POLL_SECONDS = 0.5


def _message_id(message: dict) -> str:
    value = message.get("id")
    return value if isinstance(value, str) else ""


class OpencodeChatBackend(ChatBackend):
    """Drive one chat turn at a time per named session over HTTP."""

    def __init__(
        self,
        book: TurnBook,
        client_factory: Callable[[], OpencodeHttpClient],
        store: SessionIdStore,
        permissions: PendingPermissionStore,
        directory: OrchestratorDirectory,
        follower: OpencodeTurnFollower,
        history_loader: OpencodeHistoryLoader,
        handoff_settle_seconds: float = HANDOFF_SETTLE_SECONDS,
        handoff_poll_seconds: float = HANDOFF_POLL_SECONDS,
    ) -> None:
        super().__init__(book, permissions)
        self._handoff_settle_seconds = handoff_settle_seconds
        self._handoff_poll_seconds = handoff_poll_seconds
        self._client_factory = client_factory
        self._store = store
        self._directory = directory
        self._follower = follower
        self._history_loader = history_loader
        self._clients: dict[str, OpencodeHttpClient] = {}

    @property
    def traits(self) -> BackendTraits:
        return BackendTraits(
            key="opencode",
            label="GLM",
            tab_mark="GLM",
            session_label="Session",
            resume_template="opencode --session {session_id}",
            shows_context_percent=False,
            supports_slash_commands=True,
            supports_resume=False,
        )

    def context_percent(self, name: str) -> float | None:
        """OpenCode exposes no context percent; always None."""
        return None

    async def server_info(self, name: str) -> dict[str, object] | None:
        """OpenCode has no server info payload for the chat pane yet."""
        return None

    async def session(self, name: str) -> SessionView:
        return SessionView(self._store.load(name), None)

    async def history(self, name: str) -> tuple[ChatEvent, ...]:
        return await self._history_loader.load(name)

    async def commands(self, name: str) -> tuple[SlashCommandInfo, ...]:
        return (SlashCommandInfo(name="clear", description="Clear this chat"),)

    async def sessions(
        self, name: str, folder: str
    ) -> tuple[SessionSummary, ...]:
        return ()

    async def resume_session(
        self, name: str, folder: str, session_id: str
    ) -> bool:
        return False

    async def _turn(
        self, name: str, prompt: str, log: TurnEventLog, handoff: str
    ) -> None:
        client: OpencodeHttpClient | None = None
        try:
            client = self._client_factory()
            self._clients[name] = client
            await client.connect()
            session_id = await self._session_for(name, client)
            if await client.is_active(session_id):
                raise RuntimeError(
                    "This session is busy. Wait for it, then send again."
                )
            if handoff:
                # The handoff rides in as its own synthetic message,
                # never glued onto the user's prompt text.
                await client.add_synthetic(session_id, handoff)
                self._announce_handoff(log, handoff)
                await self._await_idle(client, session_id)
            seen = frozenset(
                _message_id(message) for message in await client.messages(session_id)
            )
            await client.prompt(session_id, prompt)
            await self._follower.follow(name, client, session_id, log, seen)
        finally:
            self._clients.pop(name, None)
            if client is not None:
                try:
                    await client.close()
                except Exception:
                    pass

    async def _await_idle(self, client: OpencodeHttpClient, session_id: str) -> None:
        # A synthetic message makes the model reply. Its idle marker would end
        # the author's turn early, so the reply must finish before we prompt.
        deadline = time.monotonic() + self._handoff_settle_seconds
        while await client.is_active(session_id):
            if time.monotonic() >= deadline:
                raise RuntimeError("The handoff reply did not finish. Send again later.")
            await asyncio.sleep(self._handoff_poll_seconds)

    async def _session_for(self, name: str, client: OpencodeHttpClient) -> str:
        """Return the session id, stored or freshly created."""
        session_id = self._store.load(name)
        if session_id:
            return session_id
        session_id = await client.create_session(
            title=name, directory=self._directory.folder_of(name)
        )
        self._store.save(name, session_id)
        return session_id

    async def _interrupt(self, name: str) -> None:
        session_id = self._store.load(name)
        if not session_id:
            return
        client = self._clients.get(name)
        if client is not None:
            try:
                await client.interrupt(session_id)
            except OSError:
                pass
            return
        await self._interrupt_orphan(session_id)

    async def _interrupt_orphan(self, session_id: str) -> None:
        # No client of ours is running the turn; open a short-lived one so
        # an orphaned server-side run can still be stopped.
        client = self._client_factory()
        try:
            await client.connect()
            await client.interrupt(session_id)
        except OSError:
            pass
        finally:
            try:
                await client.close()
            except Exception:
                pass

    async def _forget(self, name: str) -> None:
        session_id = self._store.load(name)
        if session_id:
            await self._delete_session(session_id)
        self._store.forget(name)

    async def _delete_session(self, session_id: str) -> None:
        # A retired chat must not leave its conversation behind: the server
        # keeps sessions until deleted (OpenCode 2.3: DELETE /session/{id}),
        # so removing only our id would let a new chat load the old convo.
        client = self._client_factory()
        try:
            await client.connect()
            await client.delete_session(session_id)
        except OSError:
            pass
        finally:
            try:
                await client.close()
            except Exception:
                pass
