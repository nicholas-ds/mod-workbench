"""Note files pinned on one board item (design.md)."""

from __future__ import annotations

from pathlib import Path

import yaml

from workbench.board_types import Board
from workbench.config import ModConfig

_OPEN_MARKER = "---\n"
_CLOSE_MARKER = "---\n"


class NoteWriter:
    """Write one pinned note file into the mod repo notes folder."""

    def write(self, cfg: ModConfig, board: Board, item_file: str, x: float, y: float,
              text: str, now: str) -> Path:
        notes = self._notes_folder(cfg)
        number = self._next_number(notes, board.id)
        note_path = notes / f"{board.id}-{number}.md"
        note_path.write_text(self._text(board.id, item_file, x, y, text, now),
                             encoding="utf-8")
        return note_path

    def _notes_folder(self, cfg: ModConfig) -> Path:
        notes = cfg.repo / "notes"
        notes.mkdir(parents=True, exist_ok=True)
        return notes

    def _next_number(self, notes: Path, board_id: str) -> int:
        prefix = f"{board_id}-"
        numbers = [self._number_of(path, prefix) for path in notes.glob("*.md")]
        return max(numbers, default=0) + 1

    def _number_of(self, path: Path, prefix: str) -> int:
        suffix = path.stem.removeprefix(prefix)
        return int(suffix) if suffix.isdigit() else 0

    def _text(self, board_id: str, item_file: str, x: float, y: float, text: str,
              now: str) -> str:
        fields: dict[str, object] = {
            "board": board_id, "item": item_file, "x": x, "y": y, "created": now,
        }
        body = text if text.endswith("\n") else text + "\n"
        return (_OPEN_MARKER + yaml.safe_dump(fields, sort_keys=False, allow_unicode=True)
                + _CLOSE_MARKER + body)
