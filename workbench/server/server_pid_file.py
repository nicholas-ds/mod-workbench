"""Read, write and clear the JSON pid file of a detached server."""

from __future__ import annotations

import json
import os
from pathlib import Path

from workbench.server.server_record import ServerRecord


class ServerPidFile:
    """The pid file as an atomic JSON record."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, record: ServerRecord) -> None:
        """Write the record atomically via a temp file replace."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": record.pid,
            "port": record.port,
            "started": record.started,
        }
        temp = self._path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temp, self._path)

    def read(self) -> ServerRecord | None:
        """Return the record, or None when the file is missing or invalid."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return ServerRecord(
                pid=int(data["pid"]),
                port=int(data["port"]),
                started=str(data["started"]),
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def remove(self) -> None:
        """Delete the file; a missing file is not an error."""
        try:
            self._path.unlink()
        except OSError:
            pass
