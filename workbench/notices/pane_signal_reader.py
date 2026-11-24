"""Read the full status signal of a pane owner from its status file."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path

from workbench.notices.loop_types import OwnerSignal
from workbench.notices.owner_id import OwnerId

_SIGNAL_KEYS = (
    "prompt_notice",
    "prompt_at",
    "activity",
    "activity_at",
    "last_tool",
    "last_tool_at",
    "phase",
    "summary",
)


class PaneSignalReader:
    """Read an `OwnerSignal` from an owner's status TOML file."""

    def __init__(self, status_file_of: Callable[[OwnerId], Path | None]) -> None:
        self._status_file_of = status_file_of

    def read(self, owner: OwnerId) -> OwnerSignal | None:
        """Build the signal from the status file; None when unreadable."""
        path = self._status_file_of(owner)
        if path is None:
            return None
        data = self._load(path)
        if data is None:
            return None
        values = {key: str(data.get(key, "")) for key in _SIGNAL_KEYS}
        return OwnerSignal(**values)

    @staticmethod
    def _load(path: Path) -> dict[str, object] | None:
        try:
            with path.open("rb") as handle:
                return tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            return None
