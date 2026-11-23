"""Message files the author sends to the agents (design.md)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_OPEN_MARKER = "---\n"
_CLOSE_MARKER = "---\n"


@dataclass(frozen=True)
class MessageContext:
    """Where the author stood when the message was written."""

    view: str
    board: str | None = None
    item: str | None = None
    question: str | None = None


class MessageWriter:
    """Write one author message file into the mod repo messages folder."""

    def write(self, repo: Path, text: str, context: MessageContext, now: str) -> str:
        self._require_text(text)
        messages = self._messages_folder(repo)
        message_id = self._next_id(messages, now)
        (messages / f"{message_id}.md").write_text(
            self._file_text(text, context, now), encoding="utf-8")
        return message_id

    def _require_text(self, text: str) -> None:
        if not text.strip():
            raise ValueError("message text is empty")

    def _messages_folder(self, repo: Path) -> Path:
        messages = repo / "messages"
        messages.mkdir(parents=True, exist_ok=True)
        return messages

    def _next_id(self, messages: Path, now: str) -> str:
        prefix = self._compact(now)
        number = 1
        while (messages / f"{prefix}-{number}.md").exists():
            number += 1
        return f"{prefix}-{number}"

    def _compact(self, now: str) -> str:
        return now.replace("-", "").replace(":", "")

    def _file_text(self, text: str, context: MessageContext, now: str) -> str:
        body = text if text.endswith("\n") else text + "\n"
        return (_OPEN_MARKER + yaml.safe_dump(self._fields(context, now), sort_keys=False,
                                              allow_unicode=True)
                + _CLOSE_MARKER + body)

    def _fields(self, context: MessageContext, now: str) -> dict[str, str]:
        fields: dict[str, str] = {"created": now, "view": context.view}
        optional = {"board": context.board, "item": context.item,
                    "question": context.question}
        return fields | {key: value for key, value in optional.items() if value is not None}
