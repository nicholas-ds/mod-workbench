"""A stale idle marker from the handoff run must not end the author's turn."""

from test_opencode_turn_follower import (
    KIND_RESULT, KIND_TEXT, Poll, assistant_msg, idle_msg, run_follow, user_msg,
)


async def test_idle_before_the_prompt_echo_is_ignored() -> None:
    stale = idle_msg("m-old")
    polls = [
        Poll(False, [stale]),
        Poll(False, [assistant_msg("pong", "m-a"), user_msg("ping"), stale]),
        Poll(False, [idle_msg("m-i"), assistant_msg("pong", "m-a"), user_msg("ping"), stale]),
    ]
    _client, log, _permissions, _book = await run_follow(polls)
    assert [event.kind for event in log.events()] == [KIND_TEXT, KIND_RESULT]
    assert log.events()[0].text == "pong"


async def test_row_with_empty_text_parts_is_read_again_when_finished() -> None:
    streaming = {"id": "m-a", "type": "assistant", "content": [{"type": "text", "text": ""}]}
    polls = [
        Poll(True, [user_msg("go")]),
        Poll(True, [streaming, user_msg("go")]),
        Poll(False, [idle_msg("m-i"), assistant_msg("final answer", "m-a"), user_msg("go")]),
    ]
    _client, log, _permissions, _book = await run_follow(polls)
    assert [event.text for event in log.events() if event.kind == KIND_TEXT] == ["final answer"]


async def test_row_without_finish_is_read_after_the_idle_marker() -> None:
    aborted = {"id": "m-a", "type": "assistant", "content": [{"type": "text", "text": "cut off"}]}
    polls = [
        Poll(True, [user_msg("go")]),
        Poll(False, [idle_msg("m-i"), aborted, user_msg("go")]),
        Poll(False, [idle_msg("m-i"), aborted, user_msg("go")]),
    ]
    _client, log, _permissions, _book = await run_follow(polls)
    assert [event.text for event in log.events() if event.kind == KIND_TEXT] == ["cut off"]
