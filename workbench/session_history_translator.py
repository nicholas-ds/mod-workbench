"""Translate saved session messages into chat events.

Pure translator: one history message in, zero or more `ChatEvent` values
out. Unknown messages and unknown content blocks yield nothing.
"""

from __future__ import annotations

import re

from collections.abc import Callable, Sequence

from workbench.chat_event import (
    ChatEvent,
    KIND_TEXT,
    KIND_THINKING,
    KIND_TOOL,
    KIND_USER,
)
from workbench.handoff_notice import HandoffNoticeBuilder
from workbench.tool_input_detail import first_input_detail
from workbench.user_text_cleaner import UserTextCleaner

COMMAND_NAME = re.compile(r"<command-name>(.*?)</command-name>", re.DOTALL)
LOCAL_OUTPUT_PREFIX = "<local-command"
HANDOFF_OPEN = "[handoff]"
HANDOFF_CLOSE = "[/handoff]"
NEWLINE = "\n"


class SessionHistoryTranslator:
    """Translate saved session messages into chat events."""

    def translate(self, messages: Sequence[object]) -> tuple[ChatEvent, ...]:
        events: list[ChatEvent] = []
        for message in messages:
            events.extend(self._events_for_message(message))
        return tuple(events)

    def _events_for_message(self, message: object) -> tuple[ChatEvent, ...]:
        message_type = getattr(message, "type", None)
        content = self._content_of(message)
        if message_type == "user":
            return self._events_for_user_content(content)
        if message_type == "assistant":
            return self._collect_events(content, self._event_for_assistant_block)
        return ()

    def _content_of(self, message: object) -> object:
        message_body = getattr(message, "message", None)
        if isinstance(message_body, dict):
            return message_body.get("content")
        return None

    def _events_for_user_content(self, content: object) -> tuple[ChatEvent, ...]:
        if isinstance(content, str):
            return self._user_text_event(content)
        return self._collect_events(content, self._event_for_user_block)

    def _user_text_event(self, content: str) -> tuple[ChatEvent, ...]:
        block, rest = self._split_handoff(content)
        events: list[ChatEvent] = []
        if block:
            events.append(HandoffNoticeBuilder().build(block))
        shown = self._shown_user_text(rest)
        if shown:
            events.append(ChatEvent(kind=KIND_USER, text=shown))
        return tuple(events)

    def _shown_user_text(self, text: str) -> str:
        text = UserTextCleaner().clean(text)
        command = COMMAND_NAME.search(text)
        if command is not None:
            return command.group(1).strip()
        if text.startswith(LOCAL_OUTPUT_PREFIX):
            return ""
        return text

    def _split_handoff(self, text: str) -> tuple[str, str]:
        """Split a leading [handoff]..[/handoff] block from the typed text after it."""
        lines = text.split(NEWLINE)
        if not lines or lines[0].strip() != HANDOFF_OPEN:
            return "", text
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() != HANDOFF_CLOSE:
                continue
            rest = NEWLINE.join(lines[index + 1:])
            return NEWLINE.join(lines[:index + 1]), rest.removeprefix(NEWLINE)
        return "", text

    def _collect_events(
        self, content: object, event_for: Callable[[object], ChatEvent | None]
    ) -> tuple[ChatEvent, ...]:
        if not isinstance(content, list):
            return ()
        events: list[ChatEvent] = []
        for block in content:
            event = event_for(block)
            if event is not None:
                events.append(event)
        return tuple(events)

    def _event_for_user_block(self, block: object) -> ChatEvent | None:
        if not isinstance(block, dict) or block.get("type") != "text":
            return None
        shown = self._shown_user_text(self._split_handoff(self._string_field(block, "text"))[1])
        if shown:
            return ChatEvent(kind=KIND_USER, text=shown)
        return None

    def _event_for_assistant_block(self, block: object) -> ChatEvent | None:
        if not isinstance(block, dict):
            return None
        block_type = block.get("type")
        if block_type == "text":
            return self._assistant_text_event(block)
        if block_type == "thinking":
            return ChatEvent(kind=KIND_THINKING)
        if block_type == "tool_use":
            return self._tool_event(block)
        return None

    def _assistant_text_event(self, block: dict) -> ChatEvent | None:
        text = self._string_field(block, "text")
        if text.strip():
            return ChatEvent(kind=KIND_TEXT, text=text)
        return None

    def _tool_event(self, block: dict) -> ChatEvent:
        tool_input = block.get("input", {})
        if not isinstance(tool_input, dict):
            tool_input = {}
        return ChatEvent(
            kind=KIND_TOOL,
            tool_name=self._string_field(block, "name"),
            detail=first_input_detail(tool_input),
        )

    def _string_field(self, block: dict, key: str) -> str:
        value = block.get(key, "")
        return value if isinstance(value, str) else ""
