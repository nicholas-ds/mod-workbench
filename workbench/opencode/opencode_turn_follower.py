"""Follow one OpenCode turn: poll messages and permissions into a TurnEventLog.

Extracted from OpencodeChatBackend. The follower owns no session state: a
caller hands over a client, a session id, a log and the ids already seen, and
the poll loop runs until the turn ends, the deadline fires or an I/O error
propagates.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, replace
from typing import NoReturn

from workbench.opencode.opencode_chat_translator import OpencodeChatTranslator
from workbench.opencode.opencode_http_client import OpencodeHttpClient
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.permission_card_builder import PermissionCardBuilder
from workbench.chat.turn_book import TurnBook
from workbench.chat.turn_event_log import TurnEventLog


@dataclass(frozen=True)
class TurnProgress:
    """One poll's outcome: ids processed so far and what the turn waits for."""

    seen: frozenset[str]
    idle_message: dict | None
    tokens: dict | None
    idle_seen: bool
    pending_reply: bool
    prompt_seen: bool = False

    def is_finished(self, active: bool) -> bool:
        return self.idle_seen and not active and not self.pending_reply


class OpencodeTurnFollower:
    """Poll one session until its turn ends, translating messages into events."""

    def __init__(
        self,
        translator: OpencodeChatTranslator,
        permissions: PendingPermissionStore,
        cards: PermissionCardBuilder,
        book: TurnBook,
        timeout_seconds: float = 600.0,
        poll_seconds: float = 1.5,
    ) -> None:
        self._translator = translator
        self._permissions = permissions
        self._cards = cards
        self._book = book
        self._timeout_seconds = timeout_seconds
        self._poll_seconds = poll_seconds

    async def follow(
        self,
        name: str,
        client: OpencodeHttpClient,
        session_id: str,
        log: TurnEventLog,
        seen: frozenset[str],
    ) -> None:
        deadline = time.monotonic() + self._timeout_seconds
        progress = TurnProgress(
            seen=seen,
            idle_message=None,
            tokens=None,
            idle_seen=False,
            pending_reply=False,
        )
        while True:
            progress = await self._poll(name, client, session_id, log, progress)
            active = await client.is_active(session_id)
            if progress.is_finished(active):
                self._settle_idle(log, progress)
                return
            if time.monotonic() >= deadline:
                await self._fail_deadline(client, session_id)
            await asyncio.sleep(self._poll_seconds)

    async def _poll(
        self,
        name: str,
        client: OpencodeHttpClient,
        session_id: str,
        log: TurnEventLog,
        progress: TurnProgress,
    ) -> TurnProgress:
        messages = await client.messages(session_id)
        progress = self._absorb(log, progress, messages)
        return await self._handle_permissions(name, client, session_id, log, progress)

    def _absorb(
        self, log: TurnEventLog, progress: TurnProgress, messages: list[dict]
    ) -> TurnProgress:
        unseen = [
            message
            for message in reversed(messages)
            if self._message_id(message) not in progress.seen
        ]
        progress = replace(progress, pending_reply=False)
        for message in unseen:
            progress = self._absorb_one(log, progress, message)
        return progress

    def _absorb_one(
        self, log: TurnEventLog, progress: TurnProgress, message: dict
    ) -> TurnProgress:
        kind = message.get("type")
        # OpenCode writes the assistant row before its content, and fills the
        # parts while it streams. A row is final once it has a finish value.
        # After the idle marker the run is over, so a row without one is final.
        if kind == "assistant" and not self._is_final(message, progress):
            return replace(progress, pending_reply=True)
        if kind == "idle" and not progress.prompt_seen:
            # A stale idle marker of an earlier run (the handoff reply) can
            # land after the prompt was sent; it must not end this turn.
            return replace(progress, seen=progress.seen | {self._message_id(message)})
        if kind == "idle":
            # Hold the idle marker: its result event fires at turn end, after
            # every reply row carries text and final tokens.
            return replace(
                progress,
                idle_seen=True,
                idle_message=message,
                seen=progress.seen | {self._message_id(message)},
            )
        tokens = self._tokens_of(message) if kind == "assistant" else progress.tokens
        # The page shows the author's text itself, and submit() logs its own
        # user event, so the echoed user row is read but never emitted.
        if kind != "user":
            for event in self._translator.translate(message, tokens):
                log.append(event)
        return replace(
            progress,
            seen=progress.seen | {self._message_id(message)},
            tokens=tokens,
            prompt_seen=progress.prompt_seen or kind == "user",
        )

    async def _handle_permissions(
        self,
        name: str,
        client: OpencodeHttpClient,
        session_id: str,
        log: TurnEventLog,
        progress: TurnProgress,
    ) -> TurnProgress:
        for request in await client.permission_requests(session_id):
            request_id = str(request.get("id", ""))
            if not request_id or request_id in progress.seen:
                continue
            progress = await self._settle_request(
                name, client, session_id, log, progress, request, request_id
            )
        return progress

    async def _settle_request(
        self,
        name: str,
        client: OpencodeHttpClient,
        session_id: str,
        log: TurnEventLog,
        progress: TurnProgress,
        request: dict,
        request_id: str,
    ) -> TurnProgress:
        # Handled permission ids share `seen`: one frozenset of processed
        # entity ids keeps every poll step pure, with no mutable locals.
        progress = replace(progress, seen=progress.seen | {request_id})
        hold_id = self._permissions.hold()
        self._book.hold(name, hold_id)
        log.append(self._cards.build(
            hold_id,
            str(request.get("action", "")),
            {"command": "\n".join(self._resources_of(request))},
            None,
            None,
        ))
        outcome = await self._permissions.await_decision(
            hold_id, self._timeout_seconds
        )
        self._book.release(name, hold_id)
        await client.answer_permission(
            session_id, request_id, outcome == "allowed"
        )
        log.append(self._cards.settle(hold_id, outcome))
        return progress

    def _settle_idle(self, log: TurnEventLog, progress: TurnProgress) -> None:
        if progress.idle_message is not None:
            for event in self._translator.translate(
                progress.idle_message, progress.tokens
            ):
                log.append(event)

    async def _fail_deadline(
        self, client: OpencodeHttpClient, session_id: str
    ) -> NoReturn:
        # Stop the model before giving up, or the session keeps burning tokens.
        try:
            await client.interrupt(session_id)
        except OSError:
            pass
        raise TimeoutError(f"turn timed out after {self._timeout_seconds:g}s")

    @staticmethod
    def _is_final(message: dict, progress: TurnProgress) -> bool:
        if not message.get("content"):
            return False
        return bool(message.get("finish")) or progress.idle_seen

    @staticmethod
    def _tokens_of(message: dict) -> dict | None:
        tokens = message.get("tokens")
        return tokens if isinstance(tokens, dict) else None

    @staticmethod
    def _message_id(message: dict) -> str:
        value = message.get("id")
        return value if isinstance(value, str) else ""

    @staticmethod
    def _resources_of(request: dict) -> list[str]:
        resources = request.get("resources")
        if not isinstance(resources, list):
            return []
        return [str(item) for item in resources if isinstance(item, str)]
