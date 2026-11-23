"""Tests for ServerProber with fake pid and port callables."""

from pathlib import Path

from workbench.server.server_pid_file import ServerPidFile
from workbench.server.server_prober import ServerProber, ServerStatus
from workbench.server.server_record import ServerRecord


def _write_record(pid_file: ServerPidFile, pid: int = 100, port: int = 8760) -> None:
    pid_file.write(ServerRecord(pid=pid, port=port, started="2026-11-23T10:00:00"))


def test_probe_running_when_record_and_both_probes_pass(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")
    _write_record(pid_file)

    status = ServerProber(pid_file, lambda pid: True, lambda port: True).probe()

    assert status == ServerStatus(running=True, pid=100, port=8760)


def test_probe_not_running_when_pid_file_missing(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")

    status = ServerProber(pid_file, lambda pid: True, lambda port: True).probe()

    assert status == ServerStatus(running=False, pid=None, port=None)


def test_probe_not_running_when_pid_is_dead(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")
    _write_record(pid_file)

    status = ServerProber(pid_file, lambda pid: False, lambda port: True).probe()

    assert status.running is False and status.pid is None


def test_probe_not_running_when_port_is_silent(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")
    _write_record(pid_file)

    status = ServerProber(pid_file, lambda pid: True, lambda port: False).probe()

    assert status.running is False and status.port is None
