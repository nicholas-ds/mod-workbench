"""Tests for ServerPidFile: write, read, remove."""

from pathlib import Path

from workbench.server.server_pid_file import ServerPidFile
from workbench.server.server_record import ServerRecord


def test_write_then_read_round_trips_record(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")
    record = ServerRecord(pid=123, port=8760, started="2026-11-23T10:00:00")

    pid_file.write(record)

    assert pid_file.read() == record


def test_read_returns_none_when_file_missing(tmp_path: Path) -> None:
    assert ServerPidFile(tmp_path / "missing.json").read() is None


def test_read_returns_none_when_file_invalid(tmp_path: Path) -> None:
    path = tmp_path / "server.json"
    path.write_text("{not json", encoding="utf-8")

    assert ServerPidFile(path).read() is None


def test_write_replaces_file_atomically_without_temp_leftover(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")
    pid_file.write(ServerRecord(pid=1, port=1, started="t"))

    pid_file.write(ServerRecord(pid=2, port=2, started="u"))

    read = pid_file.read()
    assert read is not None and read.pid == 2
    assert not (tmp_path / "server.tmp").exists()


def test_remove_deletes_file_and_tolerates_missing(tmp_path: Path) -> None:
    pid_file = ServerPidFile(tmp_path / "server.json")
    pid_file.write(ServerRecord(pid=5, port=5, started="t"))

    pid_file.remove()
    pid_file.remove()  # second call must not raise

    assert pid_file.read() is None
