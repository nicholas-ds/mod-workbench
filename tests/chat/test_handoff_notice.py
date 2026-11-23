from workbench.chat.chat_event import KIND_HANDOFF, KIND_TEXT, KIND_USER, ChatEvent
from workbench.chat.handoff_composer import HandoffComposer
from workbench.chat.handoff_notice import HandoffNoticeBuilder


def composed() -> str:
    events = [ChatEvent(kind=KIND_USER, text="fix the dock"),
              ChatEvent(kind=KIND_TEXT, text="done, anchor on font load")]
    return HandoffComposer().compose(events, "GLM", "E:/t/chat.md")


def test_card_names_the_source_count_and_path() -> None:
    event = HandoffNoticeBuilder().build(composed())
    assert event.kind == KIND_HANDOFF
    assert "**Handoff from GLM.**" in event.text
    assert "last 2 messages" in event.text
    assert "`E:/t/chat.md`" in event.text
    assert event.detail == "E:/t/chat.md"


def test_card_quotes_the_shared_messages_as_markdown() -> None:
    text = HandoffNoticeBuilder().build(composed()).text
    assert "> [Author] fix the dock" in text
    assert "> [GLM] done, anchor on font load" in text


def test_unknown_block_still_gives_a_card() -> None:
    event = HandoffNoticeBuilder().build("[handoff]\nhello\n[/handoff]")
    assert "the other agent" in event.text


def test_card_shows_only_the_last_four_messages_each_capped() -> None:
    events = [ChatEvent(kind=KIND_USER, text=f"m{n} " + "x" * 300) for n in range(6)]
    text = HandoffNoticeBuilder().build(
        HandoffComposer().compose(events, "GLM", "E:/t.md")).text
    assert "last 6 messages" in text
    assert "m2 " in text and "m1 " not in text
    assert "xxxxxxxxxx..." in text


def test_continuation_lines_stay_with_their_message() -> None:
    events = [ChatEvent(kind=KIND_TEXT, text="first line\nsecond line")]
    text = HandoffNoticeBuilder().build(
        HandoffComposer().compose(events, "GLM", "E:/t.md")).text
    assert "> [GLM] first line second line" in text
