"""Build permission card chat events from permission requests."""

from __future__ import annotations

from workbench.chat.chat_event import (
    KIND_PERMISSION,
    KIND_PERMISSION_SETTLED,
    ChatEvent,
)
from workbench.core.tool_input_detail import first_input_detail


class PermissionCardBuilder:
    """Build permission request and outcome chat events."""

    def build(
        self,
        request_id: str,
        tool_name: str,
        tool_input: dict,
        title: str | None,
        display_name: str | None,
    ) -> ChatEvent:
        return ChatEvent(
            kind=KIND_PERMISSION,
            text=self._card_text(tool_name, tool_input, title, display_name),
            tool_name=tool_name,
            detail=request_id,
        )

    def settle(self, request_id: str, outcome: str) -> ChatEvent:
        return ChatEvent(kind=KIND_PERMISSION_SETTLED, text=outcome, detail=request_id)

    def _card_text(
        self,
        tool_name: str,
        tool_input: dict,
        title: str | None,
        display_name: str | None,
    ) -> str:
        if title:
            return title
        name = display_name or tool_name
        detail = first_input_detail(tool_input)
        if detail:
            return f"{name}\n{detail}"
        return name
