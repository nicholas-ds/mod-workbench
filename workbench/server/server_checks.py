"""Concrete probe callables: is a pid alive, does a port answer HTTP."""

from __future__ import annotations

import os
import sys
import urllib.request


class PidAliveCheck:
    """True when a process with this pid exists (Windows safe)."""

    _STILL_ACTIVE = 259  # Windows STILL_ACTIVE exit code
    _QUERY_LIMITED = 0x1000  # Windows PROCESS_QUERY_LIMITED_INFORMATION

    def __call__(self, pid: int) -> bool:
        if sys.platform != "win32":
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            return True
        return self._windows_alive(pid)

    def _windows_alive(self, pid: int) -> bool:
        import ctypes
        from ctypes import wintypes  # kept local: wintypes is Windows-only

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(self._QUERY_LIMITED, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == self._STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)


class PortAnswerCheck:
    """True when http://127.0.0.1:<port>/ answers any HTTP response."""

    def __call__(self, port: int) -> bool:
        url = f"http://127.0.0.1:{port}/"
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            return False
