"""Tests for resume support in the Claude chat backend."""

import asyncio
from pathlib import Path

from workbench.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat_event import ChatEvent
from workbench.claude_chat_backend import ClaudeChatBackend
from workbench.session_id_store import SessionIdStore
from workbench.session_summary import SessionSummary

from runner_fakes import (
    FakeSessionLister,
    make_held_runner,
    make_result,
    make_runner,
)


async def collect(
    runner: ClaudeChatBackend, name: str, command: ChatCommand
) -> tuple[ChatEvent, ...]:
    return tuple([event async for event in runner.run(name, command)])


async def test_resume_saves_id_and_drops_client(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    lister = FakeSessionLister((SessionSummary("s9", "old chat", 1),))
    runner, _factory = make_runner(
        store, (make_result("s1"),), session_lister=lister)
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert runner.context_percent("coder") == 12.5
    client = await runner._connected_client("coder")
    assert await runner.resume_session("coder", "E:/m", "s9") is True
    assert store.load("coder") == "s9"
    assert "disconnect" in client.calls
    assert runner.context_percent("coder") is None
    assert lister.folders == ["E:/m"]


async def test_resume_refused_while_turn_runs() -> None:
    release = asyncio.Event()
    lister = FakeSessionLister((SessionSummary("s9", "old chat", 1),))
    runner, factory = make_held_runner(release, session_lister=lister)
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    await stream.__anext__()
    assert await runner.resume_session("coder", "E:/m", "s9") is False
    release.set()
    tuple([event async for event in stream])
    assert len(factory.clients) == 1
    assert lister.folders == []


async def test_resume_refused_for_unknown_id(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    lister = FakeSessionLister((SessionSummary("s9", "old chat", 1),))
    runner, factory = make_runner(store, session_lister=lister)
    assert await runner.resume_session("coder", "E:/m", "nope") is False
    assert store.load("coder") == ""
    assert factory.clients == []


async def test_resume_command_row_appears_once_and_sorted() -> None:
    runner, _factory = make_runner(SessionIdStore(None))
    rows = await runner.commands("coder")
    assert [row.name for row in rows] == ["clear", "resume"]
    assert rows[1].description == "Resume an earlier session"


def test_traits_json_carries_supports_resume() -> None:
    runner, _factory = make_runner(SessionIdStore(None))
    assert runner.traits.as_json()["supports_resume"] is True
