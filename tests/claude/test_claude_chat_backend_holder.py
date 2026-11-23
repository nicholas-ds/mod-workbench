"""Holder-backed session tests: one open client per chat (Task T3b)."""

from pathlib import Path

from workbench.chat.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat.chat_event import KIND_ERROR, KIND_TEXT, ChatEvent
from workbench.claude.claude_chat_backend import ClaudeChatBackend
from workbench.chat.session_id_store import SessionIdStore

from runner_fakes import make_assistant, make_result, make_runner


async def collect(
    runner: ClaudeChatBackend, name: str, command: ChatCommand
) -> tuple[ChatEvent, ...]:
    return tuple([event async for event in runner.run(name, command)])


async def test_client_stays_open_and_the_next_turn_reuses_it(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "session_ids.json")
    runner, factory = make_runner(store, (make_result("s1"),))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "one"))
    client = factory.clients[0]
    assert "disconnect" not in client.calls
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "two"))
    assert factory.clients == [client]
    assert factory.requested == [("coder", "")]
    assert client.calls.count("query:two") == 1


async def test_reader_end_mid_turn_logs_an_error() -> None:
    runner, factory = make_runner(SessionIdStore(None), (make_assistant("hi"),))
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "hi")
    await factory.clients[0].disconnect()
    error = await stream.__anext__()
    assert error == ChatEvent(
        KIND_ERROR, "The Claude session ended before the turn finished.")
    assert tuple([event async for event in stream]) == ()
    assert not runner.is_running("coder")
