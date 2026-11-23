"""Argparse registrar and runner for the `server` subcommand."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from workbench.server.server_control_command import ServerControlCommand

ACTIONS = ("start", "stop", "restart", "status")


class ServerCommandLine:
    """Register the `server` subparser and run one server action."""

    def __init__(self, command: ServerControlCommand) -> None:
        self._command = command

    def register(self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        """Add the `server` parser with one positional action and a port flag."""
        parser = subparsers.add_parser("server", help="control the detached workbench server")
        parser.add_argument("action", choices=list(ACTIONS), help="what to do with the server")
        parser.add_argument("--port", type=int, default=None,
                            help="TCP port the server listens on")

    def run(self, args: argparse.Namespace, default_port: int) -> int:
        """Run the requested action and print its text; always exit 0."""
        port = args.port if args.port is not None else default_port
        actions: dict[str, Callable[[], str]] = {
            "start": lambda: self._command.start(port),
            "stop": self._command.stop,
            "restart": lambda: self._command.restart(port),
            "status": self._command.status,
        }
        print(actions[str(args.action)]())
        return 0
