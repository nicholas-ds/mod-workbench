"""Load a GLM chat's saved conversation from the OpenCode server as chat events.

Mirrors ChatHistoryLoader for the HTTP side: session id from the store,
messages from ``GET /session/{id}/message`` (newest first), reversed to
oldest first, the trailing idle marker dropped, one tuple of ChatEvent out.
"""

from __future__ import annotations

from collections.abc import Callable

from workbench.chat.chat_event import ChatEvent
from workbench.opencode.opencode_chat_translator import OpencodeChatTranslator
from workbench.opencode.opencode_http_client import OpencodeHttpClient
from workbench.chat.orchestrator_directory import OrchestratorDirectory
from workbench.chat.session_id_store import SessionIdStore


class OpencodeHistoryLoader:
    """Load the saved conversation and current session id of one named chat."""

    def __init__(self, store: SessionIdStore, directory: OrchestratorDirectory,
                 client_factory: Callable[[], OpencodeHttpClient]) -> None:
        self._store = store
        self._directory = directory
        self._client_factory = client_factory

    async def load(self, name: str) -> tuple[ChatEvent, ...]:
        session_id = self._store.load(name)
        if not session_id:
            return ()
        client = self._client_factory()
        try:
            await client.connect()
            messages = await client.messages(session_id)
        except OSError:
            return ()
        finally:
            try:
                await client.close()
            except Exception:
                pass
        return self._translate(list(reversed(messages)))

    def session_id(self, name: str) -> str:
        return self._store.load(name)

    def _translate(self, oldest_first: list[object]) -> tuple[ChatEvent, ...]:
        if self._is_idle(oldest_first[-1] if oldest_first else None):
            oldest_first.pop()
        translator = OpencodeChatTranslator()
        events: list[ChatEvent] = []
        tokens: dict | None = None
        for message in oldest_first:
            if not isinstance(message, dict):
                continue
            if message.get("type") == "assistant":
                candidate = message.get("tokens")
                tokens = candidate if isinstance(candidate, dict) else None
            events.extend(translator.translate(message, tokens))
        return tuple(events)

    @staticmethod
    def _is_idle(message: object) -> bool:
        return isinstance(message, dict) and message.get("type") == "idle"
