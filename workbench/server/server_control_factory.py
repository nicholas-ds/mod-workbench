"""Build a ready-to-run ServerControlCommand for the mod-workbench repo."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from workbench.server.detached_server_launcher import DetachedServerLauncher
from workbench.server.server_checks import PidAliveCheck, PortAnswerCheck
from workbench.server.server_control_command import ServerControlCommand
from workbench.server.server_pid_file import ServerPidFile
from workbench.server.server_prober import ServerProber
from workbench.server.server_stopper import ServerStopper


def _clock() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


class ServerControlFactory:
    """Assemble the detached-server control pieces from a repo root."""

    POLL_SECONDS = 0.5
    POLL_LIMIT = 40  # 40 polls 0.5 s apart cover 20 s

    def __init__(
        self,
        clock: Callable[[], str] = _clock,
        sleep: Callable[[float], None] = _sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep

    def build(self, repo_root: Path) -> ServerControlCommand:
        """Return the command wired to the repo's status folder and venv."""
        pid_file = ServerPidFile(repo_root / "status" / "workbench_server.json")
        log_path = repo_root / "status" / "workbench_server.log"
        python_exe = repo_root / ".venv" / "Scripts" / "pythonw.exe"
        return ServerControlCommand(
            prober=ServerProber(pid_file, PidAliveCheck(), PortAnswerCheck()),
            launcher=DetachedServerLauncher(python_exe, log_path),
            stopper=ServerStopper(pid_file, self._run_command),
            pid_file=pid_file,
            working_dir=repo_root,
            now=self._clock,
            wait_until_up=self.wait_until_up,
        )

    def wait_until_up(self, port: int) -> bool:
        """Poll the port every half second for 20 s; True once it answers."""
        check = PortAnswerCheck()
        for _ in range(self.POLL_LIMIT):
            if check(port):
                return True
            self._sleep(self.POLL_SECONDS)
        return False

    def _run_command(self, command: list[str]) -> int:
        return subprocess.run(command, capture_output=True).returncode
