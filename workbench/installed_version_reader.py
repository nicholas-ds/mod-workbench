"""Read installed package versions from metadata and command output."""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version

VERSION_PATTERN = re.compile(r"v?(\d+(?:\.\d+)+)")


class InstalledVersionReader:
    """Read the installed version of a package by metadata or command."""

    def __init__(self, run_command: Callable[[tuple[str, ...]], str]) -> None:
        self._run_command = run_command

    def package(self, name: str) -> str:
        try:
            return version(name)
        except PackageNotFoundError:
            return ""

    def command(self, args: tuple[str, ...]) -> str:
        try:
            output = self._run_command(args)
        except Exception:
            return ""
        return self._first_version_token(output)

    def _first_version_token(self, output: str) -> str:
        for token in output.split():
            match = VERSION_PATTERN.fullmatch(token)
            if match:
                return match.group(1)
        return ""


def run_process(args: tuple[str, ...]) -> str:
    program = shutil.which(args[0])
    if program is None:
        return ""
    try:
        finished = subprocess.run((program, *args[1:]), capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return finished.stdout + finished.stderr
