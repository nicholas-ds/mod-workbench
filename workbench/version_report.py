"""A comparison result between an installed version and the latest known version."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VersionReport:
    name: str
    installed: str
    latest: str
    update_available: bool
    note: str
