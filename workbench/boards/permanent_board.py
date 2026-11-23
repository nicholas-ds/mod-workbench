"""The rule for boards tagged permanent: never closed, warn when the renders are old."""

from __future__ import annotations

from pathlib import Path

from workbench.boards.board_types import Board

PERMANENT_TAG = "permanent"
STALE_AFTER_SECONDS = 2 * 24 * 3600
_SECONDS_PER_DAY = 24 * 3600


class PermanentBoardRule:
    """Tell whether a board is permanent and whether its items are stale."""

    def is_permanent(self, board: Board) -> bool:
        return PERMANENT_TAG in board.tags

    def stale_note(self, board: Board, now: float) -> str | None:
        if not self.is_permanent(board):
            return None
        newest = self._newest_item_time(board)
        if newest is None or now - newest <= STALE_AFTER_SECONDS:
            return None
        return f"renders {int((now - newest) // _SECONDS_PER_DAY)} days old"

    def _newest_item_time(self, board: Board) -> float | None:
        times = [self._modified(board.folder / item.file) for item in board.items]
        known = [value for value in times if value is not None]
        return max(known) if known else None

    def _modified(self, path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except OSError:
            return None
