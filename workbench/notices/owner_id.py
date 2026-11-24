"""Identify the session that raised a board."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OwnerKind(Enum):
    """Surface the owner lives on."""

    PANE = "pane"
    CHAT = "chat"
    REPO = "repo"


@dataclass(frozen=True)
class OwnerId:
    """Name one pane or chat owner."""

    kind: OwnerKind
    key: str

    def text(self) -> str:
        return f"{self.kind.value}:{self.key}"

    @staticmethod
    def parse(text: str) -> OwnerId:
        if not text:
            raise ValueError("owner text is empty")
        if text.startswith("chat-"):
            return OwnerId(OwnerKind.CHAT, text.removeprefix("chat-"))
        kind, sep, key = text.partition(":")
        if sep and kind in tuple(kind.value for kind in OwnerKind):
            return OwnerId(OwnerKind(kind), key)
        return OwnerId(OwnerKind.PANE, text)
