"""Read the mod's status file and extract its worker tables."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Status:
    values: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkspaceStatus:
    workspace: str
    values: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Worker:
    name: str
    fields: Mapping[str, object]


class StatusReader:
    """Read one TOML status file into a `Status`, empty when absent."""

    def read(self, path: Path) -> Status:
        if not path.is_file():
            return Status()
        try:
            return Status(values=tomllib.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            return Status()

    def read_all(self, path: Path) -> tuple[WorkspaceStatus, ...]:
        """Read a status file, or every `*.toml` in a folder, per workspace."""
        if path.is_file():
            return (self._read_workspace(path),)
        if path.is_dir():
            return tuple(self._read_workspace(entry) for entry in sorted(path.glob("*.toml")))
        return ()

    def _read_workspace(self, path: Path) -> WorkspaceStatus:
        try:
            values: Mapping[str, object] = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            values = {"error": "unreadable"}
        return WorkspaceStatus(workspace=path.stem, values=values)


class WorkerExtractor:
    """Turn the `workers` tables of a `Status` into `Worker` entries."""

    def extract(self, status: Status) -> list[Worker]:
        tables = status.values.get("workers", {})
        if not isinstance(tables, Mapping):
            return []
        return [
            Worker(name=name, fields=dict(fields))
            for name, fields in tables.items()
            if isinstance(fields, Mapping)
        ]
