"""Read author message files of one mod back into records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.boards.front_matter import FrontMatter, FrontMatterParser


@dataclass(frozen=True)
class MessageRecord:
    """One author message, with its reply text when one exists."""

    id: str
    created: str
    view: str
    board: str | None
    item: str | None
    question: str | None
    text: str
    reply: str | None
    done: bool


class MessageReader:
    """Read the author message files of one mod, newest first."""

    def __init__(self, parser: FrontMatterParser | None = None) -> None:
        self._parser = parser if parser is not None else FrontMatterParser()

    def read_all(self, repo: Path) -> tuple[MessageRecord, ...]:
        messages = repo / "messages"
        records = [self._read_file(messages, path)
                   for path in self._message_files(messages)]
        return tuple(sorted(records, key=lambda record: record.id, reverse=True))

    def _message_files(self, messages: Path) -> list[Path]:
        folders = [messages, messages / "done"]
        return [path for folder in folders if folder.is_dir()
                for path in sorted(folder.glob("*.md"))]

    def _read_file(self, messages: Path, path: Path) -> MessageRecord:
        front = self._parser.parse(path.read_text(encoding="utf-8"))
        return MessageRecord(
            id=path.stem,
            created=self._field(front, "created", ""),
            view=self._field(front, "view", ""),
            board=self._field(front, "board"),
            item=self._field(front, "item"),
            question=self._field(front, "question"),
            text=front.body.removesuffix("\n"),
            reply=self._reply(messages, path.stem),
            done=path.parent.name == "done",
        )

    def _field(self, front: FrontMatter, key: str,
               default: str | None = None) -> str | None:
        value = front.fields.get(key)
        return default if value is None else str(value)

    def _reply(self, messages: Path, message_id: str) -> str | None:
        reply = messages / "replies" / f"{message_id}.md"
        if not reply.is_file():
            return None
        return reply.read_text(encoding="utf-8").removesuffix("\n")
