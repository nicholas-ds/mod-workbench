"""Tests for ServerControlCommand with fakes for launcher, stopper and probes."""

from pathlib import Path

from workbench.server.server_control_command import ServerControlCommand
from workbench.server.server_pid_file import ServerPidFile
from workbench.server.server_prober import ServerProber
from workbench.server.server_record import ServerRecord
from workbench.server.server_stopper import ServerStopper


class FakeLauncher:
    """Record launch calls and hand back pid 200."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, Path]] = []

    def launch(self, port: int, working_dir: Path) -> int:
        self.calls.append((port, working_dir))
        return 200


class FakeWaiter:
    """Record probed ports and return whether the server came up."""

    def __init__(self, up: bool) -> None:
        self.up = up
        self.ports: list[int] = []

    def __call__(self, port: int) -> bool:
        self.ports.append(port)
        return self.up


def _command(tmp_path: Path, running: bool = False, up: bool = True, stop_code: int = 0,
             ) -> tuple[ServerControlCommand, ServerPidFile, FakeLauncher, FakeWaiter]:
    pid_file = ServerPidFile(tmp_path / "server.json")
    if running:
        pid_file.write(ServerRecord(pid=100, port=8760, started="2026-11-23T10:00:00"))
    launcher, waiter = FakeLauncher(), FakeWaiter(up)
    command = ServerControlCommand(
        ServerProber(pid_file, lambda _pid: True, lambda _port: True),
        launcher, ServerStopper(pid_file, lambda _cmd: stop_code), pid_file, tmp_path,
        now=lambda: "2026-11-23T10:00:00", wait_until_up=waiter)
    return command, pid_file, launcher, waiter


def test_start_reports_already_running_without_launching(tmp_path: Path) -> None:
    command, _p, launcher, waiter = _command(tmp_path, running=True)

    assert command.start(9000) == "already running on port 8760 (pid 100)"
    assert launcher.calls == [] and waiter.ports == []


def test_start_launches_writes_record_and_answers(tmp_path: Path) -> None:
    command, pid_file, launcher, waiter = _command(tmp_path)

    assert command.start(9000) == "started on port 9000 (pid 200)"
    assert launcher.calls == [(9000, tmp_path)] and waiter.ports == [9000]
    record = pid_file.read()
    assert record is not None
    assert (record.pid, record.port, record.started) == (200, 9000, "2026-11-23T10:00:00")


def test_start_reports_silent_server(tmp_path: Path) -> None:
    command, _p, _l, _w = _command(tmp_path, up=False)
    assert command.start(9000) == "started but not answering: see the log"


def test_stop_reports_stopped_then_not_running(tmp_path: Path) -> None:
    command, pid_file, _l, _w = _command(tmp_path, running=True)

    assert command.stop() == "stopped" and pid_file.read() is None
    failing, _p, _l, _w = _command(tmp_path / "second", running=True, stop_code=1)
    assert failing.stop() == "not running"


def test_restart_stops_then_returns_start_text(tmp_path: Path) -> None:
    command, _p, launcher, waiter = _command(tmp_path, running=True)

    assert command.restart(9000) == "started on port 9000 (pid 200)"
    assert launcher.calls == [(9000, tmp_path)] and waiter.ports == [9000]


def test_status_reports_running_and_stopped(tmp_path: Path) -> None:
    running, _p, _l, _w = _command(tmp_path, running=True)
    assert running.status() == "running on port 8760 (pid 100)"
    stopped, _p, _l, _w = _command(tmp_path / "second", running=False)
    assert stopped.status() == "not running"
