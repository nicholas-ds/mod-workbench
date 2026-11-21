"""Translate Claude Agent SDK messages into chat events.

Pure translator: one SDK message in, zero or more `ChatEvent` values out.
Unknown messages and unknown content blocks yield nothing.
"""

from __future__ import annotations

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)

from workbench.chat_event import (
    ChatEvent,
    KIND_ERROR,
    KIND_RESULT,
    KIND_TEXT,
    KIND_THINKING,
    KIND_TOOL,
)
from workbench.tool_input_detail import first_input_detail


class ClaudeSdkTranslator:
    """Translate one Claude Agent SDK message into chat events."""

    def translate(self, message: object) -> tuple[ChatEvent, ...]:
        if isinstance(message, AssistantMessage):
            return self._events_for_blocks(message.content)
        if isinstance(message, ResultMessage):
            return (self._event_for_result(message),)
        return ()

    def _events_for_blocks(self, blocks: list) -> tuple[ChatEvent, ...]:
        events: list[ChatEvent] = []
        for block in blocks:
            event = self._event_for_block(block)
            if event is not None:
                events.append(event)
        return tuple(events)

    def _event_for_block(self, block: object) -> ChatEvent | None:
        if isinstance(block, TextBlock):
            return ChatEvent(kind=KIND_TEXT, text=block.text)
        if isinstance(block, ThinkingBlock):
            return ChatEvent(kind=KIND_THINKING)
        if isinstance(block, ToolUseBlock):
            return ChatEvent(
                kind=KIND_TOOL,
                tool_name=block.name,
                detail=first_input_detail(block.input),
            )
        return None

    def _event_for_result(self, message: ResultMessage) -> ChatEvent:
        if message.is_error:
            return ChatEvent(kind=KIND_ERROR, text=message.result or "error")
        return ChatEvent(kind=KIND_RESULT)
