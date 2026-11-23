"""Tests for the session history translator."""

from dataclasses import dataclass

from workbench.chat.chat_event import (
    ChatEvent,
    KIND_TEXT,
    KIND_THINKING,
    KIND_TOOL,
    KIND_USER,
)
from workbench.chat.session_history_translator import SessionHistoryTranslator
from workbench.chat.user_text_cleaner import UserTextCleaner


@dataclass(frozen=True)
class FakeMessage:
    type: str
    message: dict


def user_message(content: object) -> FakeMessage:
    return FakeMessage(type="user", message={"content": content})


def assistant_message(content: object) -> FakeMessage:
    return FakeMessage(type="assistant", message={"content": content})


def translate(messages: list[object]) -> tuple[ChatEvent, ...]:
    return SessionHistoryTranslator().translate(messages)


def test_user_string_content_becomes_user_event() -> None:
    assert translate([user_message("hello")]) == (
        ChatEvent(kind=KIND_USER, text="hello"),
    )


def test_blank_user_string_is_skipped() -> None:
    assert translate([user_message("   ")]) == ()


def test_user_list_text_blocks_become_user_events_and_rest_is_skipped() -> None:
    content = [
        {"type": "text", "text": "first"},
        {"type": "tool_result", "content": "ignored"},
        {"type": "text", "text": "  "},
        {"type": "text", "text": "second"},
    ]
    assert translate([user_message(content)]) == (
        ChatEvent(kind=KIND_USER, text="first"),
        ChatEvent(kind=KIND_USER, text="second"),
    )


def test_assistant_blocks_become_events_in_block_order() -> None:
    content = [
        {"type": "thinking", "thinking": "hmm"},
        {"type": "text", "text": "answer"},
        {"type": "tool_use", "name": "Bash", "input": {"command": "git status"}},
    ]
    assert translate([assistant_message(content)]) == (
        ChatEvent(kind=KIND_THINKING),
        ChatEvent(kind=KIND_TEXT, text="answer"),
        ChatEvent(kind=KIND_TOOL, tool_name="Bash", detail="git status"),
    )


def test_blank_assistant_text_block_is_skipped() -> None:
    assert translate([assistant_message([{"type": "text", "text": " "}])]) == ()


def test_tool_use_with_non_dict_input_yields_empty_detail() -> None:
    content = [{"type": "tool_use", "name": "Read", "input": ["bad"]}]
    assert translate([assistant_message(content)]) == (
        ChatEvent(kind=KIND_TOOL, tool_name="Read", detail=""),
    )


def test_assistant_string_content_is_skipped() -> None:
    assert translate([assistant_message("plain")]) == ()


def test_unknown_message_types_and_shapes_are_skipped() -> None:
    messages: list[object] = [
        FakeMessage(type="result", message={"content": "x"}),
        FakeMessage(type="user", message="not-a-dict"),
        FakeMessage(type="user", message={"content": 42}),
        object(),
    ]
    assert translate(messages) == ()


def test_events_keep_message_and_block_order() -> None:
    messages: list[object] = [
        user_message("hi"),
        assistant_message([{"type": "text", "text": "hello"}]),
        user_message([{"type": "text", "text": "back"}]),
    ]
    assert [event.text for event in translate(messages)] == ["hi", "hello", "back"]


def test_slash_command_wrapper_shows_as_the_command() -> None:
    wrapped = "<command-name>/usage</command-name> <command-message>usage</command-message>"
    events = translate([user_message(wrapped)])
    assert [(event.kind, event.text) for event in events] == [(KIND_USER, "/usage")]


def test_local_command_output_is_hidden() -> None:
    events = translate([user_message("<local-command-stdout>x</local-command-stdout>")])
    assert events == ()


def test_handoff_block_stays_and_context_marker_is_cleaned() -> None:
    marker = UserTextCleaner.CONTEXT_PREFIX + "b, item i, question q. Leave out parts that are null.)"
    text = f"[handoff]\n{marker}\n[/handoff]\n{marker}\nhello"
    events = translate([user_message(text)])
    assert len(events) == 2
    assert events[1].kind == KIND_USER
    assert events[1].text == "hello"
