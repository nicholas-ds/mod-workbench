"""Tests for the OpenCode chat message translator."""

from __future__ import annotations

from workbench.chat.chat_event import (
    ChatEvent,
    KIND_RESULT,
    KIND_TEXT,
    KIND_THINKING,
    KIND_TOOL,
    KIND_USER,
)
from workbench.opencode.opencode_chat_translator import OpencodeChatTranslator

TOKENS = {
    "input": 160,
    "output": 467,
    "reasoning": 27,
    "cache": {"read": 41920, "write": 0},
}


def test_user_message_becomes_one_user_event() -> None:
    message = {"id": "usr_1", "time": 1794.5, "text": "run the tests", "type": "user"}
    assert OpencodeChatTranslator().translate(message) == (
        ChatEvent(kind=KIND_USER, text="run the tests"),
    )


def test_user_empty_text_yields_nothing() -> None:
    message = {"id": "usr_2", "time": 1794.5, "text": "", "type": "user"}
    assert OpencodeChatTranslator().translate(message) == ()


def test_synthetic_message_yields_no_events() -> None:
    message = {
        "id": "syn_1",
        "type": "synthetic",
        "text": "handoff context",
        "time": {"created": 1794.5},
    }
    assert OpencodeChatTranslator().translate(message) == ()


def test_idle_with_tokens_uses_runner_token_counts() -> None:
    message = {
        "id": "msg_9",
        "time": {"created": 1794.5},
        "type": "idle",
        "outcome": "succeeded",
    }
    assert OpencodeChatTranslator().translate(message, TOKENS) == (
        ChatEvent(kind=KIND_RESULT, text="succeeded", detail="in 160 / out 467"),
    )


def test_idle_without_tokens_defaults_to_zero() -> None:
    message = {
        "id": "msg_9",
        "time": {"created": 1794.5},
        "type": "idle",
        "outcome": "succeeded",
    }
    assert OpencodeChatTranslator().translate(message) == (
        ChatEvent(kind=KIND_RESULT, text="succeeded", detail="in 0 / out 0"),
    )


def test_assistant_parts_translate_in_order() -> None:
    message = {
        "id": "msg_1",
        "type": "assistant",
        "model": {"id": "glm-5.3-flash"},
        "finish": "stop",
        "tokens": TOKENS,
        "content": [
            {"type": "reasoning", "text": "I should run the suite."},
            {"type": "text", "text": "All tests pass."},
            {
                "type": "tool",
                "id": "call_1",
                "name": "shell",
                "state": {
                    "status": "completed",
                    "input": {
                        "command": ".venv/Scripts/python -m pytest -q",
                        "timeout": 600000,
                        "workdir": "E:\\repos\\mods\\mod-workbench",
                    },
                    "metadata": {"exit": 0},
                },
            },
            {
                "type": "tool",
                "id": "call_2",
                "name": "read",
                "state": {
                    "status": "completed",
                    "input": {"filePath": "workbench/chat_event.py"},
                    "metadata": {},
                },
            },
        ],
    }
    assert OpencodeChatTranslator().translate(message) == (
        ChatEvent(kind=KIND_THINKING, text="I should run the suite."),
        ChatEvent(kind=KIND_TEXT, text="All tests pass."),
        ChatEvent(
            kind=KIND_TOOL,
            tool_name="shell",
            detail=".venv/Scripts/python -m pytest -q",
        ),
        ChatEvent(
            kind=KIND_TOOL,
            tool_name="read",
            detail="workbench/chat_event.py",
        ),
    )


def test_unknown_and_non_dict_parts_are_skipped() -> None:
    message = {
        "id": "msg_2",
        "type": "assistant",
        "content": [
            {"type": "step-start"},
            "not a dict",
            {"type": "text", "text": "kept"},
        ],
    }
    assert OpencodeChatTranslator().translate(message) == (
        ChatEvent(kind=KIND_TEXT, text="kept"),
    )


def test_unknown_or_missing_type_and_non_dict_yield_nothing() -> None:
    translator = OpencodeChatTranslator()
    assert translator.translate({"id": "msg_3", "type": "step-finish"}) == ()
    assert translator.translate({"id": "msg_4"}) == ()
    assert translator.translate("not a dict") == ()  # type: ignore[arg-type]


def test_tool_detail_flattens_newlines_and_caps_at_100() -> None:
    long_command = "echo one\necho two\r\necho three" + " x" * 60
    message = {
        "id": "msg_5",
        "type": "assistant",
        "content": [
            {
                "type": "tool",
                "id": "call_3",
                "name": "shell",
                "state": {"status": "completed", "input": {"command": long_command}},
            }
        ],
    }
    events = OpencodeChatTranslator().translate(message)
    assert len(events) == 1
    assert len(events[0].detail) == 100
    assert "\n" not in events[0].detail and "\r" not in events[0].detail
    assert events[0].detail.startswith("echo one echo two echo three")
