"""Read and write the owner.json stamp of a board folder."""

from __future__ import annotations

import json
import os
from pathlib import Path

from workbench.notices.owner_id import OwnerId


class BoardOwnerStore:
    """The owner file of one board, written once by the server."""

    def __init__(self) -> None:
        self._file_name = "owner.json"

    def read(self, board_folder: Path) -> OwnerId | None:
        """Return the stamped owner, or None when the file is missing or invalid."""
        try:
            data = json.loads((board_folder / self._file_name).read_text(encoding="utf-8"))
            return OwnerId.parse(str(data["owner"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def write_once(self, board_folder: Path, owner: OwnerId) -> bool:
        """Stamp the owner only when no owner file exists; True when written."""
        path = board_folder / self._file_name
        if path.exists():
            return False
        board_folder.mkdir(parents=True, exist_ok=True)
        payload = {"owner": owner.text()}
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temp, path)
        return True
