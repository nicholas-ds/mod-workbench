"""Cached version reports: fresh within a TTL, saved atomically.

A cache without a path is disabled: it loads nothing and saves nothing.
A missing, corrupt, or stale file loads as None, meaning "run a fresh check".
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from workbench.versions.version_report import VersionReport

_SAVED_AT_KEY = "saved_at"
_REPORTS_KEY = "reports"


class VersionCache:
    """Load and save cached version reports; a missing path disables it."""

    def __init__(
        self,
        path: Path | None,
        ttl_seconds: int,
        clock: Callable[[], float],
    ) -> None:
        self._path = path
        self._ttl_seconds = ttl_seconds
        self._clock = clock

    def load(self) -> tuple[VersionReport, ...] | None:
        if self._path is None or not self._path.is_file():
            return None
        return self._parse(self._read_json())

    def save(self, reports: tuple[VersionReport, ...]) -> None:
        if self._path is None:
            return
        payload = {
            _SAVED_AT_KEY: self._clock(),
            _REPORTS_KEY: [asdict(report) for report in reports],
        }
        self._write_json(payload)

    def _read_json(self) -> object:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _parse(self, data: object) -> tuple[VersionReport, ...] | None:
        if not isinstance(data, dict):
            return None
        saved_at = data.get(_SAVED_AT_KEY)
        if not isinstance(saved_at, (int, float)):
            return None
        if self._clock() - saved_at > self._ttl_seconds:
            return None
        raw_reports = data.get(_REPORTS_KEY)
        if not isinstance(raw_reports, list):
            return None
        reports = tuple(self._report(raw) for raw in raw_reports)
        if any(report is None for report in reports):
            return None
        return reports

    def _report(self, raw: object) -> VersionReport | None:
        if not isinstance(raw, dict):
            return None
        try:
            return VersionReport(**raw)
        except TypeError:
            return None

    # os.replace is atomic on one volume, so a crash never leaves partial JSON.
    def _write_json(self, payload: dict[str, object]) -> None:
        path = Path(self._path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp, path)
