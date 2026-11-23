"""Send one author message line into a wmux pane."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from workbench.panes.message_writer import MessageContext
from workbench.panes.pane_registry import OrchestratorPane

Runner = Callable[[list[str]], int]


class WmuxCommandResolver:
    """Turn a leading `wmux` into node plus wmux.js, as the wmux.cmd shim does.

    The shim is a batch file. Windows cannot start it without cmd.exe, and cmd.exe
    would parse `&`, `%` and quotes in message text.
    """

    def resolve(self, args: list[str], environ: Mapping[str, str]) -> list[str]:
        if args[0] != "wmux":
            return args
        node = environ.get("WMUX_NODE") or shutil.which("node") or "node"
        return [node, self._script(environ), *args[1:]]

    @staticmethod
    def _script(environ: Mapping[str, str]) -> str:
        if environ.get("WMUX_CLI"):
            return environ["WMUX_CLI"]
        shim = shutil.which("wmux")
        if shim is None:
            return "wmux.js"
        return str(Path(shim).resolve().parent.parent / "cli" / "wmux.js")


def subprocess_runner(args: list[str]) -> int:
    """Run one command and return its exit code, 1 when it cannot run."""
    command = WmuxCommandResolver().resolve(args, os.environ)
    try:
        return subprocess.run(command, capture_output=True, timeout=10).returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 1


@dataclass(frozen=True)
class PaneMessageFormatter:
    """Format one author message as a single pane line."""

    def format(self, mod: str, context: MessageContext, text: str,
               message_id: str, reply_file: Path) -> str:
        head = f"mod={mod} view={context.view}{self._optional_fields(context)} id={message_id}"
        return f"[workbench] {head} | {text} | {self._reply_instruction(reply_file)}"

    @staticmethod
    def _reply_instruction(reply_file: Path) -> str:
        return (f"Reply in the workbench UI: write your answer to {reply_file} "
                f"(plain text), then move the message file to messages/done/. "
                f"Do not answer only in chat.")

    @staticmethod
    def _optional_fields(context: MessageContext) -> str:
        optional = (("board", context.board), ("item", context.item),
                    ("question", context.question))
        return "".join(f" {key}={value}" for key, value in optional
                       if value is not None)


class PaneSender:
    """Type one line into a wmux pane with send and send-key commands."""

    def __init__(self, run: Runner = subprocess_runner) -> None:
        self._run = run

    def send(self, pane: OrchestratorPane, text: str) -> bool:
        line = self._flat_line(text)
        typed = self._run(["wmux", "send", "--surface", pane.surface, line])
        entered = self._run(["wmux", "send-key", "Enter", "--surface", pane.surface])
        return typed == 0 and entered == 0

    @staticmethod
    def _flat_line(text: str) -> str:
        return text.replace("\n", " ").replace("\t", " ").strip()
