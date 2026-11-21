"""Handoff text waiting for the next turn of each chat; taken once."""

from __future__ import annotations


class HandoffInbox:
    """Hold one handoff block per chat name until its next turn takes it."""

    def __init__(self) -> None:
        self._blocks: dict[str, str] = {}

    def put(self, name: str, block: str) -> None:
        if block:
            self._blocks[name] = block

    def take(self, name: str) -> str:
        return self._blocks.pop(name, "")
