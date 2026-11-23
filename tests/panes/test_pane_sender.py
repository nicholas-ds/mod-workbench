from pathlib import Path
"""Tests: PaneSender types a flattened line, the formatter builds the line."""

from workbench.panes.message_writer import MessageContext
from workbench.panes.pane_registry import OrchestratorPane
from workbench.panes.pane_sender import PaneMessageFormatter, PaneSender

PANE = OrchestratorPane(surface="surf-1")


class FakeRunner:
    """Record commands and return one fixed exit code."""

    def __init__(self, code: int) -> None:
        self._code = code
        self.commands: list[list[str]] = []

    def __call__(self, args: list[str]) -> int:
        self.commands.append(args)
        return self._code


def test_send_runs_send_then_enter_commands() -> None:
    runner = FakeRunner(code=0)
    assert PaneSender(runner).send(PANE, "hello") is True
    assert runner.commands == [
        ["wmux", "send", "--surface", "surf-1", "hello"],
        ["wmux", "send-key", "Enter", "--surface", "surf-1"],
    ]


def test_send_flattens_newlines_tabs_and_edges() -> None:
    runner = FakeRunner(code=0)
    PaneSender(runner).send(PANE, " one\ntwo\tthree ")
    assert runner.commands[0][-1] == "one two three"


def test_send_is_false_when_send_command_fails() -> None:
    assert PaneSender(FakeRunner(code=1)).send(PANE, "hello") is False


def test_send_is_false_when_enter_command_fails() -> None:
    codes = iter([0, 2])

    def runner(args: list[str]) -> int:
        return next(codes)

    assert PaneSender(runner).send(PANE, "hello") is False


def test_formatter_omits_missing_fields() -> None:
    line = PaneMessageFormatter().format("CityMod", MessageContext(view="board"),
                                         "Widen it", "m-1", Path("messages/replies/m-1.md"))
    assert line.startswith("[workbench] mod=CityMod view=board id=m-1 | Widen it | ")
    assert "messages" in line and "m-1.md" in line and "Do not answer only in chat" in line


def test_formatter_includes_all_fields() -> None:
    context = MessageContext(view="board", board="layout", item="shot.png",
                             question="Which layout?")
    line = PaneMessageFormatter().format("CityMod", context, "Widen it", "m-1",
                                         Path("messages/replies/m-1.md"))
    assert line.startswith("[workbench] mod=CityMod view=board board=layout "
                           "item=shot.png question=Which layout? id=m-1 | Widen it | ")


def test_resolver_runs_wmux_through_node_script() -> None:
    from workbench.panes.pane_sender import WmuxCommandResolver
    environ = {"WMUX_NODE": "node.exe", "WMUX_CLI": "wmux.js"}
    command = WmuxCommandResolver().resolve(["wmux", "send", "a & b"], environ)
    assert command == ["node.exe", "wmux.js", "send", "a & b"]


def test_resolver_leaves_other_commands_alone() -> None:
    from workbench.panes.pane_sender import WmuxCommandResolver
    assert WmuxCommandResolver().resolve(["echo", "x"], {}) == ["echo", "x"]
