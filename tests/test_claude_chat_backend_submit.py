"""Tests for submitted turns and per-turn clients in the session runner."""

import asyncio
from pathlib import Path

from workbench.chat_command import COMMAND_CLEAR, COMMAND_PROMPT, ChatCommand
from workbench.chat_event import (
    KIND_ERROR,
    KIND_NOTICE,
    KIND_RESULT,
    KIND_TEXT,
    KIND_USER,
    ChatEvent,
)
from workbench.claude_chat_backend import ClaudeChatBackend
from workbench.session_id_store import SessionIdStore

from runner_fakes import make_held_runner, make_result, make_runner


async def collect(
    runner: ClaudeChatBackend, name: str, command: ChatCommand
) -> tuple[ChatEvent, ...]:
    return tuple([event async for event in runner.run(name, command)])


async def test_second_turn_reuses_the_open_client(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    runner, factory = make_runner(store, (make_result("s1"),))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "one"))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "two"))
    assert len(factory.clients) == 1
    assert "disconnect" not in factory.clients[0].calls
    assert factory.requested == [("coder", "")]


async def test_is_running_tracks_a_turn() -> None:
    release = asyncio.Event()
    runner, _factory = make_held_runner(release, (make_result("s1"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    assert runner.is_running("coder")
    release.set()
    rest = tuple([event async for event in stream])
    assert rest == (ChatEvent(KIND_RESULT),)
    assert not runner.is_running("coder")


async def test_submit_on_an_idle_chat_starts_a_turn() -> None:
    release = asyncio.Event()
    runner, _factory = make_held_runner(release, (make_result("s1"),))
    await runner.submit("coder", "server text")
    assert runner.is_running("coder")
    release.set()
    events = tuple([event async for event in runner.follow("coder")])
    assert events == (
        ChatEvent(KIND_USER, "server text"),
        ChatEvent(KIND_TEXT, "hi"),
        ChatEvent(KIND_RESULT),
    )


async def test_submit_during_a_running_turn_queues_behind_it() -> None:
    release = asyncio.Event()
    runner, factory = make_held_runner(release, (make_result("s1"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    await runner.submit("coder", "queued one")
    await runner.submit("coder", "queued two")
    assert len(factory.clients) == 1
    release.set()
    assert tuple([event async for event in stream]) == (ChatEvent(KIND_RESULT),)
    while runner.is_running("coder"):
        await asyncio.sleep(0)
    assert len(factory.clients) == 1
    assert factory.clients[0].calls == [
        "connect",
        "query:first",
        "query:queued one",
        "query:queued two",
    ]
    assert not runner.is_running("coder")


async def test_clear_drops_a_queued_text() -> None:
    release = asyncio.Event()
    runner, factory = make_held_runner(release, (make_result("s1"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    await runner.submit("coder", "queued")
    notice = await collect(runner, "coder", ChatCommand(COMMAND_CLEAR, ""))
    assert notice == (ChatEvent(KIND_NOTICE, "Chat cleared."),)
    release.set()
    error = ChatEvent(KIND_ERROR, "The Claude session ended before the turn finished.")
    assert tuple([event async for event in stream]) == (error,)
    assert not runner.is_running("coder")
    assert len(factory.clients) == 1
    assert factory.clients[0].calls == [
        "connect", "query:first", "interrupt", "disconnect"]
