"""Types for the done-board archive.

Spec: docs/board-archive-design.md, revision 1. Frozen records describing
one board candidate and the result of archiving a board.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArchiveCandidate:
    board_dir: Path


@dataclass(frozen=True)
class BoardArchiveResult:
    board_dir: Path
    file_count: int
    total_bytes: int
    archived: bool
    error: str = ""


@dataclass(frozen=True)
class BoardArchiveJob:
    """One board to archive, paired with the boards_dir that owns it."""

    boards_dir: Path
    candidate: ArchiveCandidate
