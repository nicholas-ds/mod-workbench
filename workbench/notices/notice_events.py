"""Event names and value objects for board notices."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ANSWERS_EVENT = "answers"
CLOSED_EVENT = "closed"
REOPENED_EVENT = "reopened"


@dataclass(frozen=True)
class NoteNotice:
    """One pinned note to announce to the pane that raised the board."""

    item: str
    x: float
    y: float
    text: str
    path: Path
