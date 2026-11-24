"""Detect whether an owner raised a new board after a given time."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from workbench.notices.board_owner_store import BoardOwnerStore
from workbench.notices.owner_id import OwnerId


class NewBoardDetector:
    """Watch a boards-open folder for a freshly stamped board of an owner."""

    def __init__(self, owner_store: BoardOwnerStore) -> None:
        self._owner_store = owner_store

    def raised_since(
        self,
        boards_open_dir: Path,
        owner: OwnerId,
        since: datetime,
        ignore_board: str,
    ) -> bool:
        """True when a new board of this owner was stamped at or after `since`."""
        try:
            entries = list(boards_open_dir.iterdir())
        except OSError:
            return False
        for folder in entries:
            if not folder.is_dir() or folder.name == ignore_board:
                continue
            try:
                mtime = (folder / "owner.json").stat().st_mtime
            except OSError:
                continue
            if datetime.fromtimestamp(mtime, tz=timezone.utc) < since:
                continue
            if self._owner_store.read(folder) == owner:
                return True
        return False
