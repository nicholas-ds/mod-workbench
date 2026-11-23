"""Kill the recorded server process tree with taskkill."""

from __future__ import annotations

from typing import Callable

from workbench.server.server_pid_file import ServerPidFile


class ServerStopper:
    """Stop the server in the pid file and clean the file up afterwards."""

    def __init__(
        self,
        pid_file: ServerPidFile,
        run_command: Callable[[list[str]], int],
    ) -> None:
        self._pid_file = pid_file
        self._run_command = run_command

    def stop(self) -> bool:
        """Kill the recorded pid tree; True when killed or already gone."""
        record = self._pid_file.read()
        if record is None:
            return False
        code = self._run_command(["taskkill", "/PID", str(record.pid), "/T", "/F"])
        if code in (0, 128):
            self._pid_file.remove()
            return True
        return False
