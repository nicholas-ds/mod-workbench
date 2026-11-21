"""The handoff block rides into a GLM chat as one synthetic message.

Also: the handoff reply of a new chat must finish before the author's prompt.
"""

from pathlib import Path

import pytest

from opencode_fakes import (
    assistant_msg,
    collect,
    idle_msg,
    make_backend,
    Poll,
    user_msg,
)
from workbench.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat_event import ChatEvent, KIND_ERROR, KIND_RESULT, KIND_TEXT
from workbench.session_id_store import SessionIdStore

BLOCK = "[handoff]\nContext from the earlier chat.\n[/handoff]"
BUSY_TEXT = "This session is busy. Wait for it, then send again."


class _SettlingClient:
    def __init__(self, active_checks: int) -> None:
        self.active_checks = active_checks
        self.calls = 0

    async def is_active(self, session_id: str) -> bool:
        self.calls += 1
        return self.calls <= self.active_checks


async def test_handoff_reply_must_finish_before_the_prompt(tmp_path: Path) -> None:
    runner, _ = make_backend([Poll(False)], SessionIdStore(tmp_path / "ids.json"))
    runner._handoff_poll_seconds = 0.0
    client = _SettlingClient(active_checks=3)
    await runner._await_idle(client, "s-new")
    assert client.calls == 4


async def test_handoff_reply_that_never_finishes_raises(tmp_path: Path) -> None:
    runner, _ = make_backend([Poll(False)], SessionIdStore(tmp_path / "ids.json"))
    runner._handoff_poll_seconds = 0.0
    runner._handoff_settle_seconds = 0.0
    with pytest.raises(RuntimeError):
        await runner._await_idle(_SettlingClient(active_checks=99), "s-new")


async def test_handoff_rides_as_synthetic_before_the_prompt(tmp_path: Path) -> None:
    polls = [
        Poll(False),
        Poll(True, [user_msg("hello")]),
        Poll(False, [idle_msg("m-i"), assistant_msg("done", "m-a"), user_msg("hello")]),
    ]
    runner, factory = make_backend(polls, SessionIdStore(tmp_path / "ids.json"))
    runner.receive_handoff("coder", BLOCK)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    client = factory.clients[0]
    assert client.synthetics == [BLOCK]
    assert client.prompts == ["hello"]
    assert [event.kind for event in events] == ["handoff", KIND_TEXT, KIND_RESULT]


async def test_handoff_rides_on_an_existing_session_too(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    polls = [
        Poll(False, [idle_msg("m-old")]),
        Poll(True, [idle_msg("m-old"), user_msg("hello", "m-u2")]),
        Poll(
            False,
            [idle_msg("m-i"), assistant_msg("done", "m-a"), user_msg("hello", "m-u2")],
        ),
    ]
    runner, factory = make_backend(polls, store)
    runner.receive_handoff("coder", BLOCK)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    client = factory.clients[0]
    assert client.created == []
    assert client.synthetics == [BLOCK]
    assert client.prompts == ["hello"]
    assert [event.kind for event in events] == ["handoff", KIND_TEXT, KIND_RESULT]


async def test_busy_session_refuses_before_the_synthetic(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    runner, factory = make_backend([Poll(True)], store)
    runner.receive_handoff("coder", BLOCK)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert events == (ChatEvent(kind=KIND_ERROR, text=BUSY_TEXT),)
    assert factory.clients[0].synthetics == []
    assert factory.clients[0].prompts == []
    assert runner._inbox.take("coder") == BLOCK


async def test_empty_handoff_sends_no_synthetic(tmp_path: Path) -> None:
    polls = [
        Poll(False),
        Poll(True, [user_msg("go")]),
        Poll(False, [idle_msg("m-i"), user_msg("go")]),
    ]
    runner, factory = make_backend(polls, SessionIdStore(tmp_path / "ids.json"))
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "go"))
    assert factory.clients[0].synthetics == []
    assert factory.clients[0].prompts == ["go"]
    assert [event.kind for event in events] == [KIND_RESULT]
