"""Tests for DetachedServerLauncher with a fake spawn callable."""

import subprocess
from pathlib import Path
from typing import Any

from workbench.server.detached_server_launcher import DetachedServerLauncher


class FakeProcess:
    """Just enough of Popen for the launcher: a pid."""

    def __init__(self, pid: int) -> None:
        self.pid = pid


class FakeSpawn:
    """Record the spawn call and return a fake process."""

    def __init__(self, pid: int = 4321) -> None:
        self.pid = pid
        self.args: tuple[Any, ...] = ()
        self.kwargs: dict[str, Any] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> FakeProcess:
        self.args = args
        self.kwargs = kwargs
        return FakeProcess(self.pid)


def _expected_flags() -> int:
    flags = 0
    for name in ("CREATE_NO_WINDOW", "DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
        flags |= getattr(subprocess, name, 0)
    return flags


def test_build_command_uses_module_and_port() -> None:
    launcher = DetachedServerLauncher(Path("pythonw.exe"), Path("serve.log"))

    assert launcher.build_command(8760) == [
        "pythonw.exe",
        "-m",
        "workbench",
        "serve",
        "--port",
        "8760",
    ]


def test_launch_spawns_detached_with_log_and_returns_pid(tmp_path: Path) -> None:
    spawn = FakeSpawn(pid=4321)
    log_path = tmp_path / "logs" / "serve.log"
    launcher = DetachedServerLauncher(Path("pythonw.exe"), log_path, spawn=spawn)

    pid = launcher.launch(8760, working_dir=tmp_path)

    assert pid == 4321
    assert spawn.args == (["pythonw.exe", "-m", "workbench", "serve", "--port", "8760"],)
    assert spawn.kwargs["cwd"] == tmp_path
    assert spawn.kwargs["stdin"] == subprocess.DEVNULL
    assert spawn.kwargs["stderr"] == subprocess.STDOUT
    assert spawn.kwargs["creationflags"] == _expected_flags()
    log = spawn.kwargs["stdout"]
    assert getattr(log, "name", None) == str(log_path)


def test_launch_appends_to_existing_log(tmp_path: Path) -> None:
    log_path = tmp_path / "serve.log"
    log_path.write_bytes(b"old\n")
    launcher = DetachedServerLauncher(Path("pythonw.exe"), log_path, spawn=FakeSpawn())

    launcher.launch(8760, working_dir=tmp_path)

    assert log_path.read_bytes() == b"old\n"
