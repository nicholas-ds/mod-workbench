"""session_ids.json: name to chat session id, atomic save (Task: chat sessions).

A store without a path is disabled: it loads nothing and saves nothing.
A missing or corrupt file loads as an empty string, never an error.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class SessionIdStore:
    """Load and save the session id file; a missing path disables it."""

    def __init__(self, path: Path | None) -> None:
        self._path = path

    def load(self, name: str) -> str:
        if self._path is None or not self._path.is_file():
            return ""
        data = self._read_json()
        if not isinstance(data, dict):
            return ""
        session_id = data.get(name)
        return session_id if isinstance(session_id, str) else ""

    def known_ids(self) -> frozenset[str]:
        """Return the session id of every chat."""
        if self._path is None or not self._path.is_file():
            return frozenset()
        data = self._read_json()
        if not isinstance(data, dict):
            return frozenset()
        return frozenset(value for value in data.values() if isinstance(value, str) and value)

    def save(self, name: str, session_id: str) -> None:
        if self._path is None:
            return
        data = self._read_json()
        names: dict[str, str] = data if isinstance(data, dict) else {}
        names.update({name: session_id})
        self._write_json(names)

    def forget(self, name: str) -> None:
        if self._path is None or not self._path.is_file():
            return
        data = self._read_json()
        if not isinstance(data, dict):
            return
        if name not in data:
            return
        data.pop(name)
        self._write_json(data)

    def _read_json(self) -> object:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    # os.replace is atomic on one volume, so a crash never leaves partial JSON.
    def _write_json(self, names: dict[str, str]) -> None:
        path = Path(self._path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(json.dumps(names, indent=2), encoding="utf-8")
        os.replace(temp, path)
