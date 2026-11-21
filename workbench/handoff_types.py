"""Plain data for the research handoff notice."""

from __future__ import annotations

from dataclasses import dataclass

REQUESTS_KIND = "requests"
FILES_KIND = "files"


@dataclass(frozen=True)
class HandoffRow:
    """One group of waiting items and the chat that should act on them."""

    kind: str
    target: str
    label: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class HandoffReport:
    rows: tuple[HandoffRow, ...]
    total: int
