"""Move an app chat to the session id that replaced its old one after /clear in a terminal."""

from __future__ import annotations

import json
import os
from pathlib import Path


class SessionFollower:
    """Remember the session a surface cleared, then point the chat at the new session."""

    def __init__(self, status_dir: Path) -> None:
        self._status_dir = status_dir

    def remember_cleared(self, surface: str, old_id: str) -> None:
        if not old_id:
            return
        data = self._read_json(self._cleared_path)
        data[surface] = old_id
        self._write_json(self._cleared_path, data)

    def follow_new(self, surface: str, new_id: str) -> bool:
        if not new_id:
            return False
        old_id = self._pop_cleared(surface)
        if not old_id:
            return False
        return self._repoint(old_id, new_id)

    @property
    def _cleared_path(self) -> Path:
        return self._status_dir / "cleared_sessions.json"

    @property
    def _sessions_path(self) -> Path:
        return self._status_dir / "session_ids.json"

    def _pop_cleared(self, surface: str) -> str:
        data = self._read_json(self._cleared_path)
        if surface not in data:
            return ""
        old_id = data.pop(surface)
        self._write_json(self._cleared_path, data)
        return old_id

    def _repoint(self, old_id: str, new_id: str) -> bool:
        data = self._read_json(self._sessions_path)
        replaced = False
        for chat, session_id in data.items():
            if session_id == old_id:
                data[chat] = new_id
                replaced = True
        if not replaced:
            return False
        self._write_json(self._sessions_path, data)
        return True

    def _read_json(self, path: Path) -> dict[str, str]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict[str, str]) -> None:
        temp = path.with_name(f"{path.name}.tmp")
        with temp.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2))
        os.replace(temp, path)
