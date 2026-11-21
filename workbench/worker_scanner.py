"""Count busy OpenCode worker sessions per mod repo (Task B).

An `opencode serve` is an `opencode.exe` process listening on one localhost
TCP port. `/session/status` lists only busy sessions; `/session` maps ids to
directories and `time.updated` epoch milliseconds. A busy session whose
update is at most `active_seconds` old is active; an older one is stalled
(its client died). This module never raises: any error yields no workers.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.request import urlopen

_TASKLIST_COMMAND = ["tasklist", "/FI", "IMAGENAME eq opencode.exe",
                     "/FO", "CSV", "/NH"]
_NETSTAT_COMMAND = ["netstat", "-ano", "-p", "tcp"]
_SUBPROCESS_TIMEOUT_SECONDS = 5.0
_HTTP_TIMEOUT_SECONDS = 1.5
_ACTIVE_SECONDS = 180.0


@dataclass(frozen=True)
class BusySession:
    directory: str
    updated_ms: int


@dataclass(frozen=True)
class WorkerCounts:
    active: int = 0
    stalled: int = 0


class OpencodePortFinder:
    """Find the localhost TCP ports where `opencode serve` processes listen."""

    def find(self) -> list[int]:
        try:
            tasklist_text = self._run(_TASKLIST_COMMAND)
            netstat_text = self._run(_NETSTAT_COMMAND)
        except Exception:
            return []
        worker_pids = self._worker_pids(tasklist_text)
        listening = self._listening_ports(netstat_text)
        return sorted({port for port, pid in listening if pid in worker_pids})

    def _run(self, command: list[str]) -> str:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=_SUBPROCESS_TIMEOUT_SECONDS)
        return completed.stdout

    def _worker_pids(self, tasklist_text: str) -> set[int]:
        pids: set[int] = set()
        for line in tasklist_text.splitlines():
            fields = [field.strip().strip('"') for field in line.split('","')]
            if len(fields) < 2 or fields[0].lower() != "opencode.exe":
                continue
            try:
                pids.add(int(fields[1]))
            except ValueError:
                continue
        return pids

    def _listening_ports(self, netstat_text: str) -> list[tuple[int, int]]:
        entries: list[tuple[int, int]] = []
        for line in netstat_text.splitlines():
            fields = line.split()
            if len(fields) != 5 or fields[0] != "TCP" or fields[3] != "LISTENING":
                continue
            port = self._port_of(fields[1])
            if port is None:
                continue
            entries.append((port, int(fields[4])))
        return entries

    def _port_of(self, address: str) -> int | None:
        _, _, tail = address.rpartition(":")
        try:
            return int(tail)
        except ValueError:
            return None


class OpencodeSessionClient:
    """Read busy sessions with their last update from one OpenCode server."""

    def busy_sessions(self, port: int) -> list[BusySession]:
        try:
            status = self._get_json(f"http://127.0.0.1:{port}/session/status")
            sessions = self._get_json(f"http://127.0.0.1:{port}/session")
        except Exception:
            return []
        busy_ids = self._busy_ids(status)
        return self._sessions_of(sessions, busy_ids)

    def _busy_ids(self, status: object) -> set[str]:
        if not isinstance(status, dict):
            return set()
        return {session_id for session_id, value in status.items()
                if isinstance(value, dict) and value.get("type") == "busy"}

    def _sessions_of(self, sessions: object, busy_ids: set[str]) -> list[BusySession]:
        if not isinstance(sessions, list):
            return []
        found: list[BusySession] = []
        for session in sessions:
            busy = self._busy_session(session, busy_ids)
            if busy is not None:
                found.append(busy)
        return found

    def _busy_session(self, session: object, busy_ids: set[str]) -> BusySession | None:
        if not isinstance(session, dict) or session.get("id") not in busy_ids:
            return None
        directory, updated = session.get("directory"), self._updated_ms(session)
        if not isinstance(directory, str) or updated is None:
            return None
        return BusySession(directory=directory, updated_ms=updated)

    def _updated_ms(self, session: dict[str, object]) -> int | None:
        times = session.get("time")
        if not isinstance(times, dict):
            return None
        updated = times.get("updated")
        return updated if isinstance(updated, int) else None

    def _get_json(self, url: str) -> object:
        with urlopen(url, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())


class BusyWorkerCounter:
    """Sort busy OpenCode workers per repo into active and stalled."""

    def __init__(self, port_finder: OpencodePortFinder,
                 session_client: OpencodeSessionClient,
                 ttl_seconds: float = 5.0,
                 clock: Callable[[], float] = time.monotonic,
                 now_ms: Callable[[], int] = lambda: int(time.time() * 1000),
                 active_seconds: float = _ACTIVE_SECONDS) -> None:
        self._port_finder, self._session_client = port_finder, session_client
        self._ttl_seconds, self._clock = ttl_seconds, clock
        self._now_ms, self._active_seconds = now_ms, active_seconds
        self._cache: tuple[float, dict[str, WorkerCounts]] | None = None

    def count_by_repo(self, repos: list[str]) -> dict[str, WorkerCounts]:
        now = self._clock()
        if self._cache is not None and now - self._cache[0] < self._ttl_seconds:
            return self._cache[1]
        counts = self._count(repos)
        self._cache = (now, counts)
        return counts

    def _count(self, repos: list[str]) -> dict[str, WorkerCounts]:
        counts = {repo: WorkerCounts() for repo in repos}
        for port in self._port_finder.find():
            for session in self._session_client.busy_sessions(port):
                repo = self._repo_of(session.directory, repos)
                if repo is not None:
                    counts[repo] = self._bump(counts[repo], session)
        return counts

    def _bump(self, counts: WorkerCounts, session: BusySession) -> WorkerCounts:
        age_ms = self._now_ms() - session.updated_ms
        if age_ms <= self._active_seconds * 1000:
            return WorkerCounts(counts.active + 1, counts.stalled)
        return WorkerCounts(counts.active, counts.stalled + 1)

    def _repo_of(self, directory: str, repos: list[str]) -> str | None:
        normal = self._normalise(directory)
        for repo in repos:
            repo_normal = self._normalise(repo)
            if normal == repo_normal or normal.startswith(repo_normal + "\\"):
                return repo
        return None

    def _normalise(self, path: str) -> str:
        return path.replace("/", "\\").rstrip("\\").lower()
