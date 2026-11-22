"""Contract: both backends build tool details with one shared rule."""

from __future__ import annotations

from dataclasses import dataclass

from workbench.chat_event import KIND_TOOL
from workbench.opencode_chat_translator import OpencodeChatTranslator
from workbench.session_history_translator import SessionHistoryTranslator

INPUTS = (
    {"command": "git status"},
    {"file_path": "workbench/chat_event.py"},
    {"filePath": "workbench/chat_event.py"},
    {"path": "web/message_dock.js"},
    {"description": "read the board", "pattern": "*.py"},
    {"command": "echo one\necho two  " + "x" * 200},
)


@dataclass(frozen=True)
class FakeMessage:
    type: str
    message: dict


def claude_detail(tool_input: dict) -> str:
    block = {"type": "tool_use", "name": "tool", "input": tool_input}
    message = FakeMessage(type="assistant", message={"content": [block]})
    events = SessionHistoryTranslator().translate([message])
    assert len(events) == 1
    assert events[0].kind == KIND_TOOL
    return events[0].detail


def opencode_detail(tool_input: dict) -> str:
    part = {
        "type": "tool",
        "id": "call_1",
        "name": "tool",
        "state": {"status": "completed", "input": tool_input},
    }
    message = {"id": "msg_1", "type": "assistant", "content": [part]}
    events = OpencodeChatTranslator().translate(message)
    assert len(events) == 1
    assert events[0].kind == KIND_TOOL
    return events[0].detail


def test_same_tool_input_gives_same_detail_on_both_backends() -> None:
    assert opencode_detail(INPUTS[0]) != ""
    for tool_input in INPUTS:
        assert claude_detail(tool_input) == opencode_detail(tool_input)


def test_both_backends_share_one_detail_length_limit() -> None:
    long_input = {"command": "y" * 300}
    assert len(claude_detail(long_input)) == len(opencode_detail(long_input)) == 100
