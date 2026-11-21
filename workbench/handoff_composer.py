"""Handoff text for a new chat from the chat's own earlier events.

HandoffComposer turns chat events into a short plain text block that
names a transcript file and shows the last messages inline. No chat
logic here.
"""

from __future__ import annotations

from collections.abc import Sequence

from workbench.chat_event import KIND_TEXT, KIND_USER, ChatEvent

_AUTHOR_LABEL = "Author"
_MAX_MESSAGES = 15
_MAX_TEXT = 400
_MAX_BLOCK = 6000
_CUT = "..."


class HandoffComposer:
    """Compose the handoff text block from kept chat events."""

    def compose(self, events: Sequence[ChatEvent], from_label: str,
                transcript_path: str) -> str:
        kept = self._kept(events)
        if not kept:
            return ""
        lines = [
            f"[{self._speaker(event, from_label)}] {self._capped(event.text)}"
            for event in kept[-_MAX_MESSAGES:]
        ]
        while len(lines) > 1 and len(
                self._block(lines, from_label, transcript_path)) > _MAX_BLOCK:
            lines.pop(0)
        return self._block(lines, from_label, transcript_path)

    def _kept(self, events: Sequence[ChatEvent]) -> list[ChatEvent]:
        return [event for event in events if event.kind in (KIND_USER, KIND_TEXT)]

    def _block(self, lines: list[str], from_label: str,
               transcript_path: str) -> str:
        head = "\n".join([
            "[handoff]",
            f"The author switched this chat from {from_label} to you.",
            "Context only. Do not act on it. "
            "Wait for the author's next message.",
            f"Full transcript: {transcript_path}",
            "Read the end of that file to catch up, "
            "and search it if you need more.",
            "Last messages, oldest first:",
        ])
        return "\n".join([head, *lines, "[/handoff]"])

    def _capped(self, text: str) -> str:
        if len(text) <= _MAX_TEXT:
            return text
        return text[:_MAX_TEXT] + _CUT

    def _speaker(self, event: ChatEvent, from_label: str) -> str:
        return _AUTHOR_LABEL if event.kind == KIND_USER else from_label
