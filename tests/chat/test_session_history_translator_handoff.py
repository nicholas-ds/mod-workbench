"""Tests: the session history translator hides a leading handoff block."""

from dataclasses import dataclass

from workbench.chat.chat_event import ChatEvent, KIND_USER
from workbench.chat.session_history_translator import SessionHistoryTranslator

BLOCK = "[handoff]\nContext from the earlier chat.\n[/handoff]"


@dataclass(frozen=True)
class FakeMessage:
    type: str
    message: dict


def user_message(content: object) -> FakeMessage:
    return FakeMessage(type="user", message={"content": content})


def translate(text: str) -> tuple[ChatEvent, ...]:
    return SessionHistoryTranslator().translate([user_message(text)])


def test_leading_handoff_block_is_hidden_and_typed_text_kept() -> None:
    events = translate(f"{BLOCK}\n\nhello again")
    assert [event.kind for event in events] == ["handoff", KIND_USER]
    assert events[1].text == "hello again"


def test_handoff_block_with_nothing_after_it_shows_only_the_card() -> None:
    assert [event.kind for event in translate(f"{BLOCK}\n")] == ["handoff"]
    assert [event.kind for event in translate(f"{BLOCK}\n\n")] == ["handoff"]


def test_handoff_block_inside_a_text_block_is_hidden() -> None:
    content = [{"type": "text", "text": f"{BLOCK}\n\nfirst"}]
    events = SessionHistoryTranslator().translate([user_message(content)])
    assert events == (ChatEvent(kind=KIND_USER, text="first"),)


def test_block_that_is_not_leading_is_shown() -> None:
    text = f"hello\n{BLOCK}"
    assert translate(text) == (ChatEvent(kind=KIND_USER, text=text),)


def test_unclosed_handoff_block_is_shown() -> None:
    text = "[handoff]\nno closing line"
    assert translate(text) == (ChatEvent(kind=KIND_USER, text=text),)
