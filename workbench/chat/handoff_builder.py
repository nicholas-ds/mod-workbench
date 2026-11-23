"""Handoff block for a chat switch: transcript file plus composer text.

HandoffBuilder writes the transcript of one chat, then composes the
handoff block that names that file. No chat logic here.
"""

from __future__ import annotations

from collections.abc import Sequence

from workbench.chat.chat_event import KIND_TEXT, KIND_USER, ChatEvent
from workbench.chat.handoff_composer import HandoffComposer
from workbench.chat.transcript_writer import TranscriptWriter


class HandoffBuilder:
    """Write the transcript of one chat, then compose the block naming it."""

    def __init__(self, composer: HandoffComposer,
                 writer: TranscriptWriter) -> None:
        self._composer = composer
        self._writer = writer

    def build(self, name: str, from_label: str,
              events: Sequence[ChatEvent]) -> str:
        if not self._has_talk(events):
            return ""
        path = self._writer.write(name, events)
        block = self._composer.compose(events, from_label, str(path))
        return block

    def _has_talk(self, events: Sequence[ChatEvent]) -> bool:
        return any(event.kind in (KIND_USER, KIND_TEXT) for event in events)
