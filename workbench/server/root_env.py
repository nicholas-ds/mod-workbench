"""Read the mod root folders from one environment variable."""

from __future__ import annotations

import os
from pathlib import Path


class RootEnv:
    """Read the mod root folders from one environment variable."""

    def __init__(self, name: str, default: str) -> None:
        self._name = name
        self._default = default

    def read(self) -> list[Path]:
        raw = os.environ.get(self._name, self._default)
        return [Path(part) for part in raw.split(os.pathsep) if part.strip()]
