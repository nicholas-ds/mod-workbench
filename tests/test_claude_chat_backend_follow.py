"""Follow and stream-lifecycle tests for the Claude chat session runner."""

import asyncio

from workbench.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat_event import KIND_RESULT, KIND_TEXT, ChatEvent
from workbench.session_id_store import SessionIdStore

from runner_fakes import make_held_runner, make_result, make_runner


async def test_closing_the_stream_does_not_stop_the_turn() -> None:
    release = asyncio.Event()
    runner, _factory = make_held_runner(release, (make_result("s1"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    await stream.aclose()
    release.set()
    events = tuple([event async for event in runner.follow("coder")])
    assert events == (ChatEvent(KIND_TEXT, "hi"), ChatEvent(KIND_RESULT))
    again = tuple(
        [event async for event in runner.run("coder", ChatCommand(COMMAND_PROMPT, "again"))]
    )
    assert again == (ChatEvent(KIND_TEXT, "hi"), ChatEvent(KIND_RESULT))


async def test_follow_replays_a_running_turn_then_follows_it_to_the_end() -> None:
    release = asyncio.Event()
    runner, _factory = make_held_runner(release, (make_result("s1"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    follower = runner.follow("coder")
    assert await follower.__anext__() == ChatEvent(KIND_TEXT, "hi")
    release.set()
    assert tuple([event async for event in follower]) == (ChatEvent(KIND_RESULT),)
    await stream.aclose()


async def test_follow_without_a_running_turn_yields_nothing() -> None:
    runner, _factory = make_runner(SessionIdStore(None))
    assert tuple([event async for event in runner.follow("coder")]) == ()
