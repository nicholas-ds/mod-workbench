"""<folder>/<chat>.pid: the pid of the Claude CLI process of one chat (Task T3).

A file without a folder is disabled: it saves, loads and removes nothing.
A missing or corrupt file loads as None, never an error.
Unsafe chat names are mapped to a safe file name before touching the disk.
"""

from __future__ import annotations

import re
from pathlib import Path

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


class CliPidFile:
    """Save, load and remove the CLI pid file of one chat; no folder disables it."""

    def __init__(self, folder: Path | None) -> None:
        self._folder = folder

    def save(self, chat: str, pid: int) -> None:
        path = self._path_of(chat)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(pid), encoding="utf-8")

    def load(self, chat: str) -> int | None:
        path = self._path_of(chat)
        if path is None or not path.is_file():
            return None
        return self._pid_of(path)

    def remove(self, chat: str) -> None:
        path = self._path_of(chat)
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def _path_of(self, chat: str) -> Path | None:
        if self._folder is None:
            return None
        return self._folder / (_UNSAFE_NAME.sub("_", chat) + ".pid")

    def _pid_of(self, path: Path) -> int | None:
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None
