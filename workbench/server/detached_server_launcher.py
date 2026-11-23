"""Spawn a detached `workbench serve` process with output to a log file."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable


class DetachedServerLauncher:
    """Build the serve command and start it detached from this console."""

    def __init__(
        self,
        python_exe: Path,
        log_path: Path,
        spawn: Callable[..., subprocess.Popen] = subprocess.Popen,
    ) -> None:
        self._python_exe = python_exe
        self._log_path = log_path
        self._spawn = spawn

    def build_command(self, port: int) -> list[str]:
        """The command line that runs the server on the given port."""
        return [str(self._python_exe), "-m", "workbench", "serve", "--port", str(port)]

    def launch(self, port: int, working_dir: Path) -> int:
        """Start the server detached; return its pid."""
        command = self.build_command(port)
        flags = 0
        for name in ("CREATE_NO_WINDOW", "DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
            flags |= getattr(subprocess, name, 0)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("ab") as log:
            process = self._spawn(
                command,
                cwd=working_dir,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=flags,
            )
        return process.pid
