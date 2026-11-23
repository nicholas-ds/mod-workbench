"""High-level server actions: start, stop, restart and status text."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from workbench.server.detached_server_launcher import DetachedServerLauncher
from workbench.server.server_pid_file import ServerPidFile
from workbench.server.server_prober import ServerProber
from workbench.server.server_record import ServerRecord
from workbench.server.server_stopper import ServerStopper


class ServerControlCommand:
    """Run one server action and return the text to show the user."""

    def __init__(
        self,
        prober: ServerProber,
        launcher: DetachedServerLauncher,
        stopper: ServerStopper,
        pid_file: ServerPidFile,
        working_dir: Path,
        now: Callable[[], str],
        wait_until_up: Callable[[int], bool],
    ) -> None:
        self._prober = prober
        self._launcher = launcher
        self._stopper = stopper
        self._pid_file = pid_file
        self._working_dir = working_dir
        self._now = now
        self._wait_until_up = wait_until_up

    def start(self, port: int) -> str:
        """Launch the server unless it already runs; return the user text."""
        running = self._prober.probe()
        if running.running:
            return f"already running on port {running.port} (pid {running.pid})"
        pid = self._launcher.launch(port, self._working_dir)
        self._pid_file.write(ServerRecord(pid=pid, port=port, started=self._now()))
        if not self._wait_until_up(port):
            return "started but not answering: see the log"
        return f"started on port {port} (pid {pid})"

    def stop(self) -> str:
        """Stop the recorded server and report the outcome."""
        return "stopped" if self._stopper.stop() else "not running"

    def restart(self, port: int) -> str:
        """Stop then start; return the start text."""
        self.stop()
        return self.start(port)

    def status(self) -> str:
        """Report whether the server runs, with its port and pid."""
        running = self._prober.probe()
        if running.running:
            return f"running on port {running.port} (pid {running.pid})"
        return "not running"
