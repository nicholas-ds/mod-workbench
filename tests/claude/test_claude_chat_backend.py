"""Tests for the Claude chat session runner."""

import asyncio
from pathlib import Path

from workbench.chat.chat_command import COMMAND_CLEAR, COMMAND_PROMPT, ChatCommand
from workbench.chat.chat_event import (
    ChatEvent,
    KIND_ERROR,
    KIND_NOTICE,
    KIND_RESULT,
    KIND_TEXT,
)
from workbench.claude.claude_chat_backend import ClaudeChatBackend
from workbench.chat.session_id_store import SessionIdStore

from runner_fakes import make_assistant, make_held_runner, make_result, make_runner


async def collect(
    runner: ClaudeChatBackend, name: str, command: ChatCommand
) -> tuple[ChatEvent, ...]:
    return tuple([event async for event in runner.run(name, command)])


async def test_prompt_streams_events_from_fake_client() -> None:
    messages = (make_assistant("hi"), make_result("s1"))
    runner, _factory = make_runner(SessionIdStore(None), messages)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert events == (ChatEvent(KIND_TEXT, "hi"), ChatEvent(KIND_RESULT))


async def test_result_saves_session_id(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    runner, _factory = make_runner(store, (make_result("s1"),))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert store.load("coder") == "s1"


async def test_result_records_context_percent(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    runner, _factory = make_runner(store, (make_result("s1"),))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert runner.context_percent("coder") == 12.5


async def test_clear_forgets_context_percent(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    runner, _factory = make_runner(store, (make_result("s1"),))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    await collect(runner, "coder", ChatCommand(COMMAND_CLEAR, ""))
    assert runner.context_percent("coder") is None


async def test_second_turn_reuses_the_open_client() -> None:
    runner, factory = make_runner(SessionIdStore(None))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "one"))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "two"))
    assert len(factory.clients) == 1
    assert factory.clients[0].calls == [
        "connect", "query:one", "context_usage", "query:two", "context_usage"]


async def test_saved_session_id_is_passed_to_factory(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    store.save("coder", "old-id")
    runner, factory = make_runner(store)
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert factory.requested == [("coder", "old-id")]


async def test_factory_receives_the_orchestrator_name() -> None:
    runner, factory = make_runner(SessionIdStore(None))
    await collect(runner, "orch-1", ChatCommand(COMMAND_PROMPT, "hello"))
    assert factory.requested == [("orch-1", "")]


async def test_clear_forgets_session_id_and_disconnects(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    store.save("coder", "old-id")
    runner, factory = make_runner(store)
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    await collect(runner, "coder", ChatCommand(COMMAND_CLEAR, ""))
    assert store.load("coder") == ""
    assert "disconnect" in factory.clients[0].calls


async def test_clear_notice_event() -> None:
    runner, _factory = make_runner(SessionIdStore(None))
    events = await collect(runner, "coder", ChatCommand(COMMAND_CLEAR, ""))
    assert events == (ChatEvent(KIND_NOTICE, "Chat cleared."),)


async def test_stop_interrupts_client() -> None:
    release = asyncio.Event()
    runner, factory = make_held_runner(release, (make_result("s1"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    await runner.stop("coder")
    release.set()
    async for _event in stream:
        pass
    assert "interrupt" in factory.clients[0].calls


async def test_stop_without_client_does_nothing() -> None:
    runner, _factory = make_runner(SessionIdStore(None))
    await runner.stop("coder")


async def test_retire_forgets_session_and_drops_memory(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    runner, factory = make_runner(store, (make_result("s1"),))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert runner.context_percent("coder") == 12.5
    await runner.retire("coder")
    assert store.load("coder") == ""
    assert runner.context_percent("coder") is None
    assert "disconnect" in factory.clients[0].calls


async def test_retire_an_idle_chat_forgets_its_session(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    store.save("coder", "old-id")
    runner, _factory = make_runner(store)
    await runner.retire("coder")
    assert store.load("coder") == ""


async def test_failure_yields_error_event_and_drops_client() -> None:
    runner, factory = make_runner(SessionIdStore(None), fail=True)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert events[-1] == ChatEvent(KIND_ERROR, "boom")
    assert "disconnect" in factory.clients[0].calls
    await runner.stop("coder")
    assert "interrupt" not in factory.clients[0].calls


async def test_prompt_during_running_turn_is_refused() -> None:
    release = asyncio.Event()
    runner, _factory = make_held_runner(release, (make_result("s1"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    first = await stream.__anext__()
    assert first == ChatEvent(KIND_TEXT, "hi")
    refused = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "second"))
    assert refused == (ChatEvent(KIND_ERROR, "A turn is already running."),)
    release.set()
    rest = tuple([event async for event in stream])
    assert rest == (ChatEvent(KIND_RESULT),)

