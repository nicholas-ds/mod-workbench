"""Tests for ServerControlFactory wiring with a temp repo root."""

from pathlib import Path

from workbench.server.server_control_command import ServerControlCommand
from workbench.server.server_control_factory import ServerControlFactory


def test_build_returns_command_with_repo_pid_file(tmp_path: Path) -> None:
    command = ServerControlFactory().build(tmp_path)

    assert isinstance(command, ServerControlCommand)
    assert command._pid_file._path == tmp_path / "status" / "workbench_server.json"


def test_wait_until_up_gives_up_when_the_port_never_answers() -> None:
    sleeps: list[float] = []
    factory = ServerControlFactory(sleep=sleeps.append)

    answered = factory.wait_until_up(9)  # port 9 answers nothing on localhost

    assert answered is False
    assert sleeps == [0.5] * ServerControlFactory.POLL_LIMIT
