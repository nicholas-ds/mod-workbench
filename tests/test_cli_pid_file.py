"""Tests for the CLI pid file store."""

from pathlib import Path

from workbench.cli_pid_file import CliPidFile


def test_save_then_load_returns_the_pid(tmp_path: Path) -> None:
    pid_file = CliPidFile(tmp_path)
    pid_file.save("coder", 4242)
    assert pid_file.load("coder") == 4242


def test_save_creates_a_missing_folder(tmp_path: Path) -> None:
    folder = tmp_path / "nested" / "pids"
    CliPidFile(folder).save("coder", 4242)
    assert (folder / "coder.pid").is_file()


def test_unsafe_chat_name_maps_to_safe_file_name(tmp_path: Path) -> None:
    pid_file = CliPidFile(tmp_path)
    pid_file.save("orch one", 4242)
    assert (tmp_path / "orch_one.pid").is_file()
    assert pid_file.load("orch one") == 4242


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    assert CliPidFile(tmp_path).load("coder") is None


def test_load_corrupt_file_returns_none(tmp_path: Path) -> None:
    (tmp_path / "coder.pid").write_text("not-a-pid", encoding="utf-8")
    assert CliPidFile(tmp_path).load("coder") is None


def test_remove_deletes_the_pid_file(tmp_path: Path) -> None:
    pid_file = CliPidFile(tmp_path)
    pid_file.save("coder", 4242)
    pid_file.remove("coder")
    assert pid_file.load("coder") is None


def test_remove_missing_file_is_ignored(tmp_path: Path) -> None:
    CliPidFile(tmp_path).remove("coder")


def test_disabled_folder_does_nothing(tmp_path: Path) -> None:
    pid_file = CliPidFile(None)
    pid_file.save("coder", 4242)
    assert pid_file.load("coder") is None
    pid_file.remove("coder")
