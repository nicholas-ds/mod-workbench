"""Tests for ServerCommandLine registration and dispatch with a fake command."""

import argparse

import pytest

from workbench.server.server_command_line import ServerCommandLine


class FakeCommand:
    """Record the action calls and return a preset text per action."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def start(self, port: int) -> str:
        self.calls.append(f"start {port}")
        return "started on port %d (pid 1)" % port

    def stop(self) -> str:
        self.calls.append("stop")
        return "stopped"

    def restart(self, port: int) -> str:
        self.calls.append(f"restart {port}")
        return "started on port %d (pid 2)" % port

    def status(self) -> str:
        self.calls.append("status")
        return "running on port 8760 (pid 3)"


def _parsed(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    ServerCommandLine(FakeCommand()).register(sub)
    return parser.parse_args(argv)


def test_register_parses_action_and_optional_port() -> None:
    args = _parsed(["server", "start", "--port", "9000"])

    assert args.action == "start"
    assert args.port == 9000


def test_register_defaults_port_to_none() -> None:
    args = _parsed(["server", "status"])

    assert args.action == "status"
    assert args.port is None


def test_register_rejects_unknown_action() -> None:
    with pytest.raises(SystemExit):
        _parsed(["server", "pause"])


def test_run_dispatches_with_given_port(capsys: pytest.CaptureFixture[str]) -> None:
    command = FakeCommand()

    assert ServerCommandLine(command).run(_parsed(["server", "start", "--port", "9000"]), 8760) == 0

    assert command.calls == ["start 9000"]
    assert capsys.readouterr().out.strip() == "started on port 9000 (pid 1)"


def test_run_falls_back_to_default_port(capsys: pytest.CaptureFixture[str]) -> None:
    command = FakeCommand()

    assert ServerCommandLine(command).run(_parsed(["server", "restart"]), 8760) == 0

    assert command.calls == ["restart 8760"]
    assert capsys.readouterr().out.strip() == "started on port 8760 (pid 2)"


def test_run_dispatches_stop_and_status(capsys: pytest.CaptureFixture[str]) -> None:
    command = FakeCommand()
    command_line = ServerCommandLine(command)

    assert command_line.run(_parsed(["server", "stop"]), 8760) == 0
    assert command_line.run(_parsed(["server", "status"]), 8760) == 0

    assert command.calls == ["stop", "status"]
    assert capsys.readouterr().out.strip().splitlines() == ["stopped", "running on port 8760 (pid 3)"]
