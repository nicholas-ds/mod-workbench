"""chat_backends.json: bare chat name to backend, atomic save (Task: chat backends).

A store without a path is disabled: it loads nothing and saves nothing.
A missing or corrupt file loads as the default backend, never an error.
Any non-empty key is stored; saving the default removes the entry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_BACKEND = "claude"


class ChatBackendStore:
    """Load and save the chat backend file; a missing path disables it."""

    def __init__(self, path: Path | None) -> None:
        self._path = path

    def load(self, name: str) -> str:
        if self._path is None or not self._path.is_file():
            return DEFAULT_BACKEND
        data = self._read_json()
        if not isinstance(data, dict):
            return DEFAULT_BACKEND
        backend = data.get(name)
        if isinstance(backend, str) and backend != "":
            return backend
        return DEFAULT_BACKEND

    def save(self, name: str, backend: str) -> None:
        if self._path is None:
            return
        data = self._read_json()
        names: dict[str, str] = data if isinstance(data, dict) else {}
        if backend == DEFAULT_BACKEND:
            names.pop(name, None)
        else:
            names.update({name: backend})
        self._write_json(names)

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
