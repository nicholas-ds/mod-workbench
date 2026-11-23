"""Read the context usage of a pane owner from its status file."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path

from workbench.notices.owner_id import OwnerId


class PaneContextReader:
    """Read `context_percent` from an owner's status TOML file."""

    def __init__(self, status_file_of: Callable[[OwnerId], Path | None]) -> None:
        self._status_file_of = status_file_of

    def read(self, owner: OwnerId) -> float | None:
        path = self._status_file_of(owner)
        if path is None:
            return None
        data = self._load(path)
        if data is None:
            return None
        return self._percent(data)

    def _load(self, path: Path) -> dict[str, object] | None:
        try:
            with path.open("rb") as handle:
                return tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            return None

    @staticmethod
    def _percent(data: dict[str, object]) -> float | None:
        percent = data.get("context_percent")
        if isinstance(percent, bool) or not isinstance(percent, (int, float)):
            return None
        return float(percent)
