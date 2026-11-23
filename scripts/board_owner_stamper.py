"""Stamp the owner of a board folder with the pane that wrote its board.md."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pane_name_finder import PaneNameFinder

OWNER_FILE = "owner.json"  # mirrors workbench/notices/board_owner_store.py; scripts/ cannot import workbench
BOARD_MARKERS = ("boards", "open")
BOARD_FILE = "board.md"


class BoardOwnerStamper:
    """Write owner.json next to an edited board.md, once, as pane:<name>."""

    def __init__(self, name_finder: PaneNameFinder) -> None:
        self._name_finder = name_finder

    def stamp(self, edited_file: str, surface_id: str) -> bool:
        """Write the owner stamp; True only when the file was written."""
        try:
            return self._stamp(edited_file, surface_id)
        except OSError:
            return False

    def _stamp(self, edited_file: str, surface_id: str) -> bool:
        board_folder = self._board_folder(edited_file)
        if board_folder is None:
            return False
        name = self._name_finder.name_of(surface_id)
        if name is None:
            return False
        return self._write_owner(board_folder, f"pane:{name}")

    def stamp_chat(self, edited_file: str, chat_name: str) -> bool:
        """Write the owner stamp as chat:<name>; True only when written."""
        try:
            board_folder = self._board_folder(edited_file)
            if board_folder is None:
                return False
            return self._write_owner(board_folder, f"chat:{chat_name}")
        except OSError:
            return False

    def _write_owner(self, board_folder: Path, owner: str) -> bool:
        target = board_folder / OWNER_FILE
        if target.exists():
            return False
        payload = {"owner": owner}  # same format as BoardOwnerStore
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temp, target)
        return True

    def _board_folder(self, edited_file: str) -> Path | None:
        parts = Path(edited_file.replace("\\", "/")).parts
        if len(parts) < 4 or parts[-4:-2] != BOARD_MARKERS or parts[-1] != BOARD_FILE:
            return None
        return Path(*parts[:-1])
