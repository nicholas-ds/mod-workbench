"""Tests for TurnEventLog."""

import asyncio

from workbench.chat.chat_event import KIND_RESULT, KIND_TEXT, ChatEvent
from workbench.chat.turn_event_log import TurnEventLog


def _event(text: str) -> ChatEvent:
    return ChatEvent(kind=KIND_TEXT, text=text)


async def _collect(log: TurnEventLog) -> list[ChatEvent]:
    return [event async for event in log.follow()]


async def test_late_follower_gets_replay_then_live_then_end() -> None:
    log = TurnEventLog()
    log.append(_event("one"))
    log.append(_event("two"))

    follow_task = asyncio.ensure_future(_collect(log))
    await asyncio.sleep(0)
    log.append(_event("three"))
    log.finish()

    received = await follow_task
    assert [event.text for event in received] == ["one", "two", "three"]
    assert log.is_finished()
    assert log.events() == (
        _event("one"),
        _event("two"),
        _event("three"),
    )


async def test_two_followers_both_get_all_events() -> None:
    log = TurnEventLog()
    log.append(_event("one"))

    first = asyncio.ensure_future(_collect(log))
    second = asyncio.ensure_future(_collect(log))
    await asyncio.sleep(0)
    log.append(_event("two"))
    log.finish()

    first_events = await first
    second_events = await second
    assert [event.text for event in first_events] == ["one", "two"]
    assert [event.text for event in second_events] == ["one", "two"]
    assert len(log._subscribers) == 0


async def test_follower_after_finish_gets_replay_only() -> None:
    log = TurnEventLog()
    log.append(_event("one"))
    log.append(_event("two"))
    log.finish()

    received = await _collect(log)
    assert [event.text for event in received] == ["one", "two"]
    assert len(log._subscribers) == 0


async def test_aclose_removes_queue_and_later_appends_are_safe() -> None:
    log = TurnEventLog()
    log.append(_event("one"))

    follower = log.follow()
    assert await follower.__anext__() == _event("one")
    assert len(log._subscribers) == 1

    await follower.aclose()
    assert len(log._subscribers) == 0

    log.append(_event("two"))
    log.finish()
    assert log.events() == (_event("one"), _event("two"))


async def test_append_after_finish_is_ignored() -> None:
    log = TurnEventLog()
    log.append(ChatEvent(kind=KIND_RESULT, text="done"))
    log.finish()
    log.append(_event("late"))

    assert log.events() == (ChatEvent(kind=KIND_RESULT, text="done"),)
    received = await _collect(log)
    assert [event.text for event in received] == ["done"]
