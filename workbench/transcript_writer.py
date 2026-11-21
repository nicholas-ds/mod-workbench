"""Markdown transcript of one chat, for the next agent to read and search.

TranscriptWriter keeps every user and text event of a chat in one file.
No chat logic here.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from workbench.chat_event import KIND_TEXT, KIND_USER, ChatEvent

_AUTHOR_LABEL = "Author"
_ASSISTANT_LABEL = "Assistant"
_SAFE = re.compile(r"[^A-Za-z0-9._-]")


class TranscriptWriter:
    """Write every user and text event of one chat to `<safe name>.md`."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def write(self, name: str, events: Sequence[ChatEvent]) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{self._safe(name)}.md"
        path.write_text(self._content(events), encoding="utf-8")
        return path.resolve()

    def _safe(self, name: str) -> str:
        return _SAFE.sub("_", name)

    def _content(self, events: Sequence[ChatEvent]) -> str:
        lines = [
            f"[{self._speaker(event)}] {event.text}"
            for event in events
            if event.kind in (KIND_USER, KIND_TEXT)
        ]
        return "\n\n".join(lines)

    def _speaker(self, event: ChatEvent) -> str:
        return _AUTHOR_LABEL if event.kind == KIND_USER else _ASSISTANT_LABEL
