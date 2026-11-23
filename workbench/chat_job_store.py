"""<folder>/<chat>.json: load and save chat job rows atomically (Task T1).

A store without a folder is disabled: it loads nothing and saves nothing.
A missing or corrupt file loads as an empty tuple, never an error.
Unsafe chat names are mapped to a safe file name before touching the disk.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from workbench.chat_job import ChatJob

_JOBS_KEY = "jobs"
_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")
_TEXT_FIELDS = ("job_id", "kind", "chat", "started_by", "state", "result")
_MS_FIELDS = ("started_ms", "updated_ms")


class ChatJobStore:
    """Load and save the job list of one chat; a missing folder disables it."""

    def __init__(self, folder: Path | None) -> None:
        self._folder = folder

    def load(self, chat: str) -> tuple[ChatJob, ...]:
        path = self._path_of(chat)
        if path is None or not path.is_file():
            return ()
        data = self._read_json(path)
        if not isinstance(data, dict) or not isinstance(data.get(_JOBS_KEY), list):
            return ()
        jobs = (self._job(raw) for raw in data[_JOBS_KEY])
        return tuple(job for job in jobs if job is not None)

    def save(self, chat: str, jobs: tuple[ChatJob, ...]) -> None:
        path = self._path_of(chat)
        if path is None:
            return
        payload = {_JOBS_KEY: [asdict(job) for job in jobs]}
        self._write_json(path, payload)

    def _path_of(self, chat: str) -> Path | None:
        if self._folder is None:
            return None
        return self._folder / (_UNSAFE_NAME.sub("_", chat) + ".json")

    def _read_json(self, path: Path) -> object:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _job(self, raw: object) -> ChatJob | None:
        if not isinstance(raw, dict):
            return None
        for name in _TEXT_FIELDS:
            if not isinstance(raw.get(name), str):
                return None
        for name in _MS_FIELDS:
            value = raw.get(name)
            if not isinstance(value, int) or isinstance(value, bool):
                return None
        return ChatJob(**{name: raw[name] for name in _TEXT_FIELDS + _MS_FIELDS})

    # Path.replace is atomic on one volume, so a crash never leaves partial JSON.
    def _write_json(self, path: Path, payload: dict[str, list[dict[str, object]]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp.replace(path)
