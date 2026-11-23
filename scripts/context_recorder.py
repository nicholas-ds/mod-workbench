"""Statusline helper: write the pane's context percent into its status files."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from activity_hook import ActivityRecorder, _log_error


class ContextRecorder(ActivityRecorder):
    """Write `context_percent` into every status file of one surface."""

    def record(self, root: Path, surface_id: str, percent: float) -> int:
        """Return how many status files were updated."""
        updated = 0
        for path in self._candidate_paths(root):
            try:
                updated += self._record_in_file(path, surface_id, percent)
            except OSError:
                continue
        return updated

    def _record_in_file(self, path: Path, surface_id: str, percent: float) -> int:
        with path.open("r", encoding="utf-8", newline="") as handle:
            text = handle.read()
        if f'wmux_surface = "{surface_id}"' not in text:
            return 0
        lines = self._set_line(text.splitlines(), "context_percent",
                               f"context_percent = {percent:g}")
        self._write_atomically(path, self._join(lines, text))
        return 1


def read_percent(payload: dict[str, object]) -> float | None:
    window = payload.get("context_window")
    if isinstance(window, dict) and "used_percentage" in window:
        return float(window["used_percentage"])
    if "used_percentage" in payload:
        return float(payload["used_percentage"])
    return None


def main() -> int:
    try:
        percent = read_percent(json.loads(sys.stdin.read()))
        surface_id = os.environ.get("WMUX_SURFACE_ID")
        if percent is not None and surface_id:
            ContextRecorder().record(Path(__file__).resolve().parents[2], surface_id, percent)
    except Exception:
        _log_error()
    return 0


if __name__ == "__main__":
    sys.exit(main())
