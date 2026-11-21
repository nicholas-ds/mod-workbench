"""agents.json at the workbench root: load records, save atomically (Task T1b).

A store without a path is disabled: it loads nothing and saves nothing.
A missing or corrupt file loads as an empty list, never an error.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from workbench.agent_registry import AgentRecord

_AGENTS_KEY = "agents"


class AgentStore:
    """Load and save the agent record file; a missing path disables it."""

    def __init__(self, path: Path | None) -> None:
        self._path = path

    def load(self) -> list[AgentRecord]:
        if self._path is None or not self._path.is_file():
            return []
        return self._parse(self._read_json())

    def save(self, records: list[AgentRecord]) -> None:
        if self._path is None:
            return
        payload = {_AGENTS_KEY: [asdict(record) for record in records]}
        self._write_json(payload)

    def _read_json(self) -> object:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _parse(self, data: object) -> list[AgentRecord]:
        if not isinstance(data, dict) or not isinstance(data.get(_AGENTS_KEY), list):
            return []
        records = [self._record(raw) for raw in data[_AGENTS_KEY]]
        return [record for record in records if record is not None]

    def _record(self, raw: object) -> AgentRecord | None:
        if not isinstance(raw, dict):
            return None
        try:
            return AgentRecord(**raw)
        except TypeError:
            return None

    # os.replace is atomic on one volume, so a crash never leaves partial JSON.
    def _write_json(self, payload: dict[str, list[dict[str, object]]]) -> None:
        path = Path(self._path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp, path)
