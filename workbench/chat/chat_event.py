"""Chat event type for chat sessions (rule R8).

A frozen, JSON-safe record of one piece of a chat exchange. Every field is
`str`, so the event crosses the file/CLI boundary unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

KIND_TEXT = "text"
KIND_THINKING = "thinking"
KIND_TOOL = "tool"
KIND_RESULT = "result"
KIND_ERROR = "error"
KIND_NOTICE = "notice"
KIND_USER = "user"
KIND_HANDOFF = "handoff"
KIND_PERMISSION = "permission"
KIND_PERMISSION_SETTLED = "permission-settled"


@dataclass(frozen=True)
class ChatEvent:
    kind: str
    text: str = ""
    tool_name: str = ""
    detail: str = ""
