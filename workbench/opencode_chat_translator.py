"""Translate one OpenCode session message into chat events.

Pure translator: one message dict from ``GET /session/{id}/message`` in,
zero or more `ChatEvent` values out. No clock, no files, no network.
Unknown messages and unknown content parts yield nothing; never raises
on odd data.
"""

from __future__ import annotations

from workbench.handoff_notice import HandoffNoticeBuilder
from workbench.tool_input_detail import first_input_detail
from workbench.user_text_cleaner import UserTextCleaner
from workbench.chat_event import (
    ChatEvent,
    KIND_RESULT,
    KIND_TEXT,
    KIND_THINKING,
    KIND_TOOL,
    KIND_USER,
)


class OpencodeChatTranslator:
    """Translate one OpenCode message dict into chat events."""

    def translate(
        self, message: dict, tokens: dict | None = None
    ) -> tuple[ChatEvent, ...]:
        if not isinstance(message, dict):
            return ()
        message_type = message.get("type")
        if message_type == "user":
            return self._user_events(message)
        if message_type == "synthetic":
            return self._handoff_events(message)
        if message_type == "idle":
            return self._idle_events(message, tokens)
        if message_type == "assistant":
            return self._assistant_events(message)
        return ()

    def _handoff_events(self, message: dict) -> tuple[ChatEvent, ...]:
        text = self._string_field(message, "text")
        if not text.lstrip().startswith("[handoff]"):
            return ()
        return (HandoffNoticeBuilder().build(text),)

    def _user_events(self, message: dict) -> tuple[ChatEvent, ...]:
        text = UserTextCleaner().clean(self._string_field(message, "text"))
        if not text:
            return ()
        return (ChatEvent(kind=KIND_USER, text=text),)

    def _idle_events(self, message: dict, tokens: dict | None) -> tuple[ChatEvent, ...]:
        counts = tokens if isinstance(tokens, dict) else {}
        detail = (
            f"in {self._count_of(counts, 'input')}"
            f" / out {self._count_of(counts, 'output')}"
        )
        return (
            ChatEvent(
                kind=KIND_RESULT,
                text=self._string_field(message, "outcome"),
                detail=detail,
            ),
        )

    def _assistant_events(self, message: dict) -> tuple[ChatEvent, ...]:
        content = message.get("content")
        if not isinstance(content, list):
            return ()
        events: list[ChatEvent] = []
        for part in content:
            event = self._event_for_part(part)
            if event is not None:
                events.append(event)
        return tuple(events)

    def _event_for_part(self, part: object) -> ChatEvent | None:
        if not isinstance(part, dict):
            return None
        part_type = part.get("type")
        if part_type == "reasoning":
            text = self._string_field(part, "text")
            return ChatEvent(kind=KIND_THINKING, text=text) if text.strip() else None
        if part_type == "text":
            text = self._string_field(part, "text")
            return ChatEvent(kind=KIND_TEXT, text=text) if text.strip() else None
        if part_type == "tool":
            return self._tool_event(part)
        return None

    def _tool_event(self, part: dict) -> ChatEvent | None:
        state = part.get("state")
        tool_input = state.get("input", {}) if isinstance(state, dict) else {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        return ChatEvent(
            kind=KIND_TOOL,
            tool_name=self._string_field(part, "name"),
            detail=first_input_detail(tool_input),
        )

    def _count_of(self, tokens: dict, key: str) -> int:
        value = tokens.get(key, 0)
        return value if isinstance(value, int) else 0

    def _string_field(self, source: dict, key: str) -> str:
        value = source.get(key, "")
        return value if isinstance(value, str) else ""
