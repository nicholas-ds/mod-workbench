"""Tests for the chat event type (rule R8)."""

import dataclasses
import json

from workbench.chat_event import ChatEvent, KIND_TOOL


def test_chat_event_asdict_is_str_only_and_json_round_trips() -> None:
    event = ChatEvent(kind=KIND_TOOL, text="t", tool_name="Bash", detail="git status")
    plain = dataclasses.asdict(event)
    assert all(isinstance(value, str) for value in plain.values())
    assert json.loads(json.dumps(plain)) == plain
