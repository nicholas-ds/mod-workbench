"""Find the pane name of a wmux surface id in the repos' status files."""

from __future__ import annotations

from pathlib import Path


class PaneNameFinder:
    """Map a surface id to the stem of the status file that declares it."""

    def __init__(self, root: Path, patterns: tuple[str, ...]) -> None:
        self._root = root
        self._patterns = patterns

    def name_of(self, surface_id: str) -> str | None:
        """Return the first status file stem holding the surface id, else None."""
        for path in self._candidate_paths():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if f'wmux_surface = "{surface_id}"' in text:
                return path.stem
        return None

    def _candidate_paths(self) -> list[Path]:
        found = {path for pattern in self._patterns for path in self._root.glob(pattern)}
        return sorted(found)
