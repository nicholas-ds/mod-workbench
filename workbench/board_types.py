"""Data types of the board model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class BoardError(Exception):
    """One board folder is missing, unreadable or has bad front matter."""

    def __init__(self, folder: Path, reason: str) -> None:
        self.folder = folder
        self.reason = reason
        super().__init__(f"{folder.name}: {reason}")


@dataclass(frozen=True)
class FrontMatter:
    fields: Mapping[str, object]
    body: str


@dataclass(frozen=True)
class Option:
    id: str
    label: str
    item: str | None = None


@dataclass(frozen=True)
class Question:
    id: str
    type: str
    prompt: str
    options: tuple[Option, ...] = ()
    default: str | None = None
    suggestion: str | None = None
    blocking: bool = False
    affects: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedItem:
    id: str
    prompt: str
    note: str
    date: str


@dataclass(frozen=True)
class BoardItem:
    file: str
    caption: str
    group: str | None = None


@dataclass(frozen=True)
class Board:
    id: str
    folder: Path
    title: str
    raised_by: str | None = None
    created: str | None = None
    tags: tuple[str, ...] = ()
    items: tuple[BoardItem, ...] = ()
    questions: tuple[Question, ...] = ()
    resolved: tuple[ResolvedItem, ...] = ()
    body: str = ""
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Answer:
    question_id: str
    picked: str | None = None
    text: str | None = None
    comment: str | None = None
    answered_at: str = ""


@dataclass(frozen=True)
class BoardEntry:
    board: Board
    answers: tuple[Answer, ...] = ()
