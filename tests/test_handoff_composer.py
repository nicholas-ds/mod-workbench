"""Tests for HandoffComposer: the handoff seed text."""

from workbench.chat_event import KIND_TEXT, KIND_THINKING, KIND_TOOL, KIND_USER, ChatEvent
from workbench.handoff_composer import HandoffComposer

FROM = "Claude"
PATH = "E:/workbench/transcripts/Workbench_t3.md"


def _user(text: str) -> ChatEvent:
    return ChatEvent(kind=KIND_USER, text=text)


def _text(text: str) -> ChatEvent:
    return ChatEvent(kind=KIND_TEXT, text=text)


def _compose(events: list[ChatEvent]) -> str:
    return HandoffComposer().compose(events, FROM, PATH)


def test_block_starts_and_ends_with_markers() -> None:
    lines = _compose([_user("hello")]).splitlines()
    assert lines[0] == "[handoff]"
    assert lines[-1] == "[/handoff]"


def test_block_names_labels_and_transcript_path() -> None:
    block = _compose([_user("hello")])
    assert f"The author switched this chat from {FROM} to you." in block
    assert "Context only. Do not act on it. " in block
    assert "Wait for the author's next message." in block
    assert f"Full transcript: {PATH}" in block
    assert "Read the end of that file to catch up, " in block
    assert "and search it if you need more." in block
    assert "Last messages, oldest first:" in block


def test_speaker_lines_use_author_and_from_label() -> None:
    block = _compose([_user("start the build"), _text("done, tests pass")])
    assert "[Author] start the build" in block
    assert f"[{FROM}] done, tests pass" in block


def test_composer_keeps_only_user_and_text_events() -> None:
    events = [
        _user("start the build"),
        ChatEvent(kind=KIND_THINKING, text="thinking out loud"),
        _text("done, tests pass"),
        ChatEvent(kind=KIND_TOOL, text="Bash", tool_name="Bash", detail="pytest"),
    ]
    block = _compose(events)
    assert "start the build" in block
    assert "done, tests pass" in block
    assert "thinking out loud" not in block
    assert "Bash" not in block


def test_composer_takes_last_15_kept_events() -> None:
    events = [_user(f"message {i:02d}") for i in range(18)]
    block = _compose(events)
    assert "message 02" not in block
    assert "message 03" in block
    assert "message 17" in block


def test_composer_caps_each_text_at_400_chars() -> None:
    long_text = "x" * 500
    block = _compose([_user(long_text)])
    assert "x" * 400 in block
    assert "x" * 401 not in block
    assert block.count("...") >= 1


def test_block_cap_drops_oldest_first() -> None:
    events = [_user(f"first-{i:02d} " + "y" * 400) for i in range(15)]
    block = _compose(events)
    assert len(block) <= 6000
    assert "first-00" not in block
    assert "first-14" in block
    assert block.splitlines()[-1] == "[/handoff]"


def test_empty_input_returns_empty_string() -> None:
    assert _compose([]) == ""


def test_events_without_user_or_text_return_empty_string() -> None:
    events = [ChatEvent(kind=KIND_TOOL, text="Bash", tool_name="Bash", detail="pytest")]
    assert _compose(events) == ""


def test_history_reader_hides_a_composed_block() -> None:
    from workbench.session_history_translator import SessionHistoryTranslator

    block = HandoffComposer().compose(
        [ChatEvent(kind=KIND_USER, text="old talk")], "GLM", "E:/t.md")

    class Message:
        type = "user"
        message = {"content": block + "\n\nwhat now?"}

    events = SessionHistoryTranslator().translate([Message()])
    assert [event.kind for event in events] == ["handoff", "user"]
    assert events[1].text == "what now?"
