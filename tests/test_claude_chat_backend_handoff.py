"""Handoff tests: Claude receives the block and the prompt as one query."""

from pathlib import Path

from workbench.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat_event import ChatEvent, KIND_RESULT, KIND_TEXT
from workbench.claude_chat_backend import ClaudeChatBackend
from workbench.session_id_store import SessionIdStore

from runner_fakes import make_assistant, make_result, make_runner

BLOCK = "[handoff]\nContext from the earlier chat.\n[/handoff]"


async def collect(
    runner: ClaudeChatBackend, name: str, command: ChatCommand
) -> tuple[ChatEvent, ...]:
    return tuple([event async for event in runner.run(name, command)])


async def test_handoff_is_sent_before_the_prompt(tmp_path: Path) -> None:
    messages = (make_assistant("hi"), make_result("s1"))
    runner, factory = make_runner(SessionIdStore(tmp_path / "ids.json"), messages)
    runner.receive_handoff("coder", BLOCK)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert factory.clients[0].calls == [
        "connect",
        f"query:{BLOCK}\n\nhello",
        "context_usage",
        "disconnect",
    ]
    assert [event.kind for event in events] == ["handoff", KIND_TEXT, KIND_RESULT]


async def test_no_handoff_sends_the_bare_prompt() -> None:
    messages = (make_assistant("hi"), make_result("s1"))
    runner, factory = make_runner(SessionIdStore(None), messages)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert factory.clients[0].calls == [
        "connect",
        "query:hello",
        "context_usage",
        "disconnect",
    ]
    assert events == (ChatEvent(KIND_TEXT, "hi"), ChatEvent(KIND_RESULT))


async def test_handoff_is_taken_once() -> None:
    messages = (make_assistant("hi"), make_result("s1"))
    runner, factory = make_runner(SessionIdStore(None), messages)
    runner.receive_handoff("coder", BLOCK)
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "one"))
    await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "two"))
    assert factory.clients[0].calls == [
        "connect",
        f"query:{BLOCK}\n\none",
        "context_usage",
        "disconnect",
    ]
    assert factory.clients[1].calls == [
        "connect",
        "query:two",
        "context_usage",
        "disconnect",
    ]
