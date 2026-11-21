"""One OpenCode server process for the whole workbench run (GLM chat WP3).

Starts `opencode serve --port 0` with a fresh OPENCODE_PASSWORD, parses the
listen url from stdout, and records url + pid + password in a state file.
A recorded server is reused while its pid is alive and its url answers.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

_LISTEN_PATTERN = re.compile(r"listening on \(?(https?://[^\s)]+)")
_START_TIMEOUT_SECONDS = 20.0
_POLL_SECONDS = 0.25
_ANSWER_TIMEOUT_SECONDS = 2.0
_STILL_ACTIVE = 259  # Windows STILL_ACTIVE exit code
_QUERY_LIMITED = 0x1000  # Windows PROCESS_QUERY_LIMITED_INFORMATION
_NPM_EXE = Path("AppData/Roaming/npm/node_modules/@opencode/cli/bin/opencode.exe")


def resolve_opencode_exe() -> str:
    """Find the opencode program: PATH first, then the npm install location."""
    for name in ("opencode.exe", "opencode.cmd", "opencode"):
        found = shutil.which(name)
        if found:
            return found
    npm = Path.home() / _NPM_EXE
    if npm.is_file():
        return str(npm)
    return "opencode"


def parse_listen_url(text: str) -> str | None:
    """Return the url after `listening on`, or None when the line is absent."""
    match = _LISTEN_PATTERN.search(text)
    return match.group(1) if match is not None else None


class OpencodeServerProcess:
    """Own the single opencode serve subprocess; reuse it while it lives."""

    def __init__(self, state_path: Path, exe: str | None = None) -> None:
        self._state_path = state_path
        self._exe = exe if exe else resolve_opencode_exe()

    def ensure(self, cwd: Path) -> tuple[str, str]:
        """Return (url, password); start a server when no live one is recorded."""
        state = self._read_state()
        if (
            state is not None
            and self._pid_alive(state["pid"])
            and self._url_answers(state["url"], state["password"])
        ):
            return state["url"], state["password"]
        return self._start(cwd)

    def stop(self) -> None:
        """Kill the recorded server and delete its state file."""
        state = self._read_state()
        if state is None:
            return
        self._kill(state["pid"])
        self._state_path.unlink(missing_ok=True)

    def _start(self, cwd: Path) -> tuple[str, str]:
        password = uuid4().hex
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path = self._state_path.parent / "opencode_server.log"
        stderr_path = self._state_path.parent / "opencode_server.err.log"
        env = dict(os.environ, OPENCODE_PASSWORD=password)
        with stdout_path.open("wb") as stdout, stderr_path.open("ab") as stderr:
            process = subprocess.Popen(
                [self._exe, "serve", "--port", "0"],
                cwd=str(cwd),
                env=env,
                stdout=stdout,
                stderr=stderr,
            )
        url = self._wait_for_url(stdout_path)
        if url is None:
            self._kill(process.pid)
            raise OSError(
                f"{self._exe} serve did not listen within {_START_TIMEOUT_SECONDS:g}s"
            )
        self._write_state(url, process.pid, password)
        return url, password

    def _wait_for_url(self, stdout_path: Path) -> str | None:
        deadline = time.monotonic() + _START_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            text = stdout_path.read_text(encoding="utf-8", errors="replace")
            url = parse_listen_url(text)
            if url is not None:
                return url
            time.sleep(_POLL_SECONDS)
        return None

    def _read_state(self) -> dict | None:
        try:
            state = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(state, dict):
            return None
        url, password, pid = state.get("url"), state.get("password"), state.get("pid")
        if not isinstance(url, str) or not isinstance(password, str):
            return None
        if not isinstance(pid, int):
            return None
        return {"url": url, "pid": pid, "password": password}

    def _write_state(self, url: str, pid: int, password: str) -> None:
        payload = json.dumps({"url": url, "pid": pid, "password": password}, indent=2)
        temp = self._state_path.with_name(self._state_path.name + ".tmp")
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, self._state_path)

    def _url_answers(self, url: str, password: str) -> bool:
        try:
            response = httpx.get(
                url.rstrip("/") + "/api/session",
                auth=("opencode", password),
                timeout=_ANSWER_TIMEOUT_SECONDS,
            )
        except (OSError, httpx.HTTPError):
            return False
        return 200 <= response.status_code < 300

    def _kill(self, pid: int) -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if sys.platform != "win32":
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            return True
        import ctypes
        from ctypes import wintypes  # kept local: wintypes is Windows-only

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(_QUERY_LIMITED, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
