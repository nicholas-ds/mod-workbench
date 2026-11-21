"""Pipeline from a chat name to its saved conversation as chat events."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from workbench.chat_event import ChatEvent
from workbench.orchestrator_directory import OrchestratorDirectory
from workbench.session_history_reader import SessionHistoryReader
from workbench.session_id_store import SessionIdStore


class HistoryTranslator(Protocol):
    """Turn saved session messages into chat events."""

    def translate(self, messages: Sequence[object]) -> tuple[ChatEvent, ...]: ...


class ChatHistoryLoader:
    """Load the saved conversation and current session id of one named chat."""

    def __init__(self, store: SessionIdStore, directory: OrchestratorDirectory,
                 reader: SessionHistoryReader, translator: HistoryTranslator) -> None:
        self._store = store
        self._directory = directory
        self._reader = reader
        self._translator = translator

    def load(self, name: str) -> tuple[ChatEvent, ...]:
        session_id = self._store.load(name)
        folder = self._directory.folder_of(name)
        messages = self._reader.read(session_id, folder)
        return self._translator.translate(messages)

    def session_id(self, name: str) -> str:
        return self._store.load(name)
