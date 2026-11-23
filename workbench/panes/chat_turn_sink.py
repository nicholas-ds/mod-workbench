"""Send one text to a named app chat as a turn."""

from __future__ import annotations

from typing import Protocol

import anyio.from_thread


class ChatTurnSink(Protocol):
    def send(self, name: str, text: str) -> bool: ...


class TurnSubmitter(Protocol):
    async def submit(self, name: str, text: str) -> None: ...


class FolderLookup(Protocol):
    def folder_of(self, name: str) -> str: ...


class RunnerChatTurnSink:
    """Hand a text to the chat runner from a worker thread of the server."""

    def __init__(self, runner: TurnSubmitter, directory: FolderLookup) -> None:
        self._runner = runner
        self._directory = directory

    def send(self, name: str, text: str) -> bool:
        if self._directory.folder_of(name) == "":
            return False
        anyio.from_thread.run(self._runner.submit, name, text)
        return True
