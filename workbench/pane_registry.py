"""Find the registered main-orchestrator pane of the workbench platform."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OrchestratorPane:
    """The wmux surface that holds the main orchestrator pane."""

    surface: str


class PaneRegistry:
    """Read the orchestrator pane from its status file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def find(self) -> OrchestratorPane | None:
        data = self._read()
        if data is None:
            return None
        surface = data.get("wmux_surface")
        if not isinstance(surface, str):
            return None
        return OrchestratorPane(surface=surface)

    def _read(self) -> dict[str, object] | None:
        try:
            with self._path.open("rb") as handle:
                return tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            return None
