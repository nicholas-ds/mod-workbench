"""Ask the pid file and two probe callables whether the server is up."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from workbench.server.server_pid_file import ServerPidFile


@dataclass(frozen=True)
class ServerStatus:
    """Result of a probe: what runs and on which port."""

    running: bool
    pid: int | None
    port: int | None


class ServerProber:
    """Combine record, pid liveness and port answer into a status."""

    def __init__(
        self,
        pid_file: ServerPidFile,
        pid_alive: Callable[[int], bool],
        port_answers: Callable[[int], bool],
    ) -> None:
        self._pid_file = pid_file
        self._pid_alive = pid_alive
        self._port_answers = port_answers

    def probe(self) -> ServerStatus:
        """Running only when a record exists and both probes agree."""
        record = self._pid_file.read()
        if record is None:
            return ServerStatus(running=False, pid=None, port=None)
        if not self._pid_alive(record.pid):
            return ServerStatus(running=False, pid=None, port=None)
        if not self._port_answers(record.port):
            return ServerStatus(running=False, pid=None, port=None)
        return ServerStatus(running=True, pid=record.pid, port=record.port)
