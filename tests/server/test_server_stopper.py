"""Tests for ServerStopper with a fake run_command callable."""

from pathlib import Path

from workbench.server.server_pid_file import ServerPidFile
from workbench.server.server_record import ServerRecord
from workbench.server.server_stopper import ServerStopper


class FakeRunner:
    """Record the commands run and return a preset exit code."""

    def __init__(self, code: int) -> None:
        self.code = code
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> int:
        self.commands.append(command)
        return self.code


def _stopper(tmp_path: Path, code: int) -> tuple[ServerPidFile, FakeRunner]:
    pid_file = ServerPidFile(tmp_path / "server.json")
    pid_file.write(ServerRecord(pid=100, port=8760, started="2026-11-23T10:00:00"))
    runner = FakeRunner(code)
    return pid_file, runner


def test_stop_returns_false_when_no_record(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")
    runner = FakeRunner(0)

    assert ServerStopper(pid_file, runner).stop() is False
    assert runner.commands == []


def test_stop_kills_tree_and_removes_pid_file_on_zero(tmp_path: Path) -> None:
    pid_file, runner = _stopper(tmp_path, code=0)

    assert ServerStopper(pid_file, runner).stop() is True
    assert runner.commands == [["taskkill", "/PID", "100", "/T", "/F"]]
    assert pid_file.read() is None


def test_stop_accepts_128_as_already_gone(tmp_path: Path) -> None:
    pid_file, runner = _stopper(tmp_path, code=128)

    assert ServerStopper(pid_file, runner).stop() is True
    assert pid_file.read() is None


def test_stop_keeps_pid_file_on_other_exit_code(tmp_path: Path) -> None:
    pid_file, runner = _stopper(tmp_path, code=1)

    assert ServerStopper(pid_file, runner).stop() is False
    assert runner.commands == [["taskkill", "/PID", "100", "/T", "/F"]]
    record = pid_file.read()
    assert record is not None and record.pid == 100
