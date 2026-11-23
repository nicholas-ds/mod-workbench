"""Slash command parsing for the chat pane (Task: chat commands).

"/clear" becomes a clear command; everything else stays a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

COMMAND_PROMPT = "prompt"
COMMAND_CLEAR = "clear"

_CLEAR_TEXT = "/clear"


@dataclass(frozen=True)
class ChatCommand:
    kind: str
    text: str


class SlashCommandParser:
    """Turn raw chat input into a ChatCommand."""

    def parse(self, text: str) -> ChatCommand:
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty message")
        if stripped == _CLEAR_TEXT:
            return ChatCommand(kind=COMMAND_CLEAR, text="")
        return ChatCommand(kind=COMMAND_PROMPT, text=stripped)
