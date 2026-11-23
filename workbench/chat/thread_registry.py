"""threads.json: orchestrator to chat threads, atomic save (Task: chat threads).

A registry without a path is disabled: it loads nothing and saves nothing.
A missing or corrupt file loads as empty, never an error.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

THREAD_SEPARATOR = "~"


@dataclass(frozen=True)
class ChatThread:
    """One chat thread owned by an orchestrator.

    Rows carry no backend: the ChatBackendStore keys a backend by the full
    thread name, so old files with a "backend" key load, and the key is
    ignored.
    """

    orchestrator: str
    thread_id: str
    label: str

    @property
    def name(self) -> str:
        return f"{self.orchestrator}{THREAD_SEPARATOR}{self.thread_id}"

    @staticmethod
    def split_name(name: str) -> tuple[str, str]:
        """Split at the last separator; a name with no separator gives (name, "")."""
        if THREAD_SEPARATOR not in name:
            return (name, "")
        orchestrator, _, thread_id = name.rpartition(THREAD_SEPARATOR)
        return (orchestrator, thread_id)


class ThreadRegistry:
    """Load and save the thread file; a missing path disables it."""

    def __init__(self, path: Path | None) -> None:
        self._path = path

    def list_threads(self, orchestrator: str) -> tuple[ChatThread, ...]:
        return tuple(self._read().get(orchestrator, []))

    def add(self, orchestrator: str) -> ChatThread:
        """Append t<N>, one more than the highest id still present; t1 first."""
        threads = self._read()
        existing = threads.get(orchestrator, [])
        highest = 0
        for thread in existing:
            digits = thread.thread_id[1:]
            if thread.thread_id.startswith("t") and digits.isdigit():
                highest = max(highest, int(digits))
        number = highest + 1
        thread = ChatThread(orchestrator, f"t{number}", f"thread {number}")
        threads[orchestrator] = [*existing, thread]
        self._write(threads)
        return thread

    def remove(self, name: str) -> bool:
        threads = self._read()
        orchestrator, thread_id = ChatThread.split_name(name)
        rows = threads.get(orchestrator, [])
        kept = [thread for thread in rows if thread.thread_id != thread_id]
        if len(kept) == len(rows):
            return False
        if kept:
            threads[orchestrator] = kept
        else:
            threads.pop(orchestrator)
        self._write(threads)
        return True

    def contains(self, name: str) -> bool:
        orchestrator, thread_id = ChatThread.split_name(name)
        return any(thread.thread_id == thread_id for thread in self._read().get(orchestrator, []))

    def _read(self) -> dict[str, list[ChatThread]]:
        if self._path is None or not self._path.is_file():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return self._parse(data)

    @staticmethod
    def _parse(data: object) -> dict[str, list[ChatThread]]:
        if not isinstance(data, dict):
            return {}
        threads: dict[str, list[ChatThread]] = {}
        for orchestrator, rows in data.items():
            if not isinstance(orchestrator, str) or not isinstance(rows, list):
                continue
            threads[orchestrator] = [
                ChatThread(orchestrator, row["id"], row["label"])
                for row in rows
                if isinstance(row, dict)
                and isinstance(row.get("id"), str)
                and isinstance(row.get("label"), str)
            ]
        return threads

    # os.replace is atomic on one volume, so a crash never leaves partial JSON.
    def _write(self, threads: dict[str, list[ChatThread]]) -> None:
        if self._path is None:
            return
        path = Path(self._path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            orchestrator: [{"id": row.thread_id, "label": row.label} for row in rows]
            for orchestrator, rows in threads.items()
        }
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(temp, path)
