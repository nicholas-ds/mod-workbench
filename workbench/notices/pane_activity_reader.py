"""Read the activity state of a pane owner from its status file."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path

from workbench.notices.owner_id import OwnerId


class PaneActivityReader:
    """Read `activity` from an owner's status TOML file."""

    def __init__(self, status_file_of: Callable[[OwnerId], Path | None]) -> None:
        self._status_file_of = status_file_of

    def is_idle(self, owner: OwnerId) -> bool:
        """True only when the status file says `activity = "idle"`."""
        path = self._status_file_of(owner)
        if path is None:
            return False
        data = self._load(path)
        if data is None:
            return False
        return data.get("activity") == "idle"

    @staticmethod
    def _load(path: Path) -> dict[str, object] | None:
        try:
            with path.open("rb") as handle:
                return tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            return None
