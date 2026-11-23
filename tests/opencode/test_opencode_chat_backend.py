"""Tests for the OpenCode chat backend turn flow (fake client, no HTTP)."""

from __future__ import annotations

from pathlib import Path


from workbench.chat.chat_command import COMMAND_CLEAR, COMMAND_PROMPT, ChatCommand
from workbench.chat.chat_event import (
    ChatEvent,
    KIND_ERROR,
    KIND_NOTICE,
    KIND_RESULT,
    KIND_TEXT,
)
from workbench.chat.session_id_store import SessionIdStore

from opencode_fakes import (
    assistant_msg,
    collect,
    idle_msg,
    make_backend,
    Poll,
    user_msg,
)

BUSY_TEXT = "This session is busy. Wait for it, then send again."


async def test_clear_forgets_session_and_stops_the_orphan(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    runner, factory = make_backend([Poll(False)], store)
    events = await collect(runner, "coder", ChatCommand(COMMAND_CLEAR, ""))
    assert events == (ChatEvent(kind=KIND_NOTICE, text="Chat cleared."),)
    assert store.load("coder") == ""
    # Clear retires the chat: the stored orphaned session is interrupted.
    assert factory.clients[0].interrupts == ["s-old"]
    assert factory.clients[0].closed is True


async def test_new_session_sends_a_bare_prompt(tmp_path: Path) -> None:
    polls = [
        Poll(False),
        Poll(True, [user_msg("hello")]),
        Poll(False, [idle_msg("m-i"), assistant_msg("done", "m-a"), user_msg("hello")]),
    ]
    store = SessionIdStore(tmp_path / "ids.json")
    runner, factory = make_backend(polls, store)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    client = factory.clients[0]
    assert client.created == [("coder", "E:/repos/mods/fake-repo")]
    assert client.synthetics == []
    assert client.prompts == ["hello"]
    assert store.load("coder") == "s-new"
    # The page shows the author's text itself; the follower emits no user event.
    assert [event.kind for event in events] == [KIND_TEXT, KIND_RESULT]


async def test_existing_session_sends_text_only(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    polls = [
        Poll(False, [idle_msg("m-old")]),
        Poll(True, [idle_msg("m-old"), user_msg("hello", "m-u2")]),
        Poll(
            False,
            [
                idle_msg("m-i"),
                assistant_msg("done", "m-a"),
                user_msg("hello", "m-u2"),
                idle_msg("m-old"),
            ],
        ),
    ]
    runner, factory = make_backend(polls, store)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert factory.clients[0].prompts == ["hello"]
    assert factory.clients[0].synthetics == []
    assert factory.clients[0].created == []
    assert [event.kind for event in events] == [KIND_TEXT, KIND_RESULT]


async def test_busy_session_raises_error_and_sends_no_prompt(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    runner, factory = make_backend([Poll(True)], store)
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "hello"))
    assert events == (ChatEvent(kind=KIND_ERROR, text=BUSY_TEXT),)
    assert factory.clients[0].prompts == []
    assert factory.clients[0].synthetics == []
    assert runner.is_running("coder") is False


async def test_newest_first_messages_emit_oldest_first() -> None:
    newest_first = [
        idle_msg("m-i"),
        assistant_msg("a2", "m-2", tokens={"input": 160, "output": 467}),
        assistant_msg("a1", "m-1"),
        user_msg("q", "m-u"),
    ]
    polls = [Poll(False), Poll(False, newest_first)]
    runner, _factory = make_backend(polls, SessionIdStore(None))
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "q"))
    assert events == (
        ChatEvent(kind=KIND_TEXT, text="a1"),
        ChatEvent(kind=KIND_TEXT, text="a2"),
        ChatEvent(kind=KIND_RESULT, text="succeeded", detail="in 160 / out 467"),
    )


async def test_idle_seen_while_active_still_finishes() -> None:
    polls = [
        Poll(False),
        Poll(True, [idle_msg("m-i"), user_msg("go")]),
        Poll(False, [idle_msg("m-i"), user_msg("go")]),
    ]
    runner, _factory = make_backend(polls, SessionIdStore(None))
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "go"))
    assert events == (
        ChatEvent(kind=KIND_RESULT, text="succeeded", detail="in 0 / out 0"),
    )
    assert runner.is_running("coder") is False


async def test_turn_timeout_appends_error_and_finishes() -> None:
    polls = [Poll(False), Poll(True, [user_msg("go")])]
    runner, _factory = make_backend(
        polls, SessionIdStore(None), timeout_seconds=0.05, poll_seconds=0.001
    )
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "go"))
    assert len(events) == 1
    assert events[-1].kind == KIND_ERROR
    assert "timed out" in events[-1].text
    assert runner.is_running("coder") is False


async def test_assistant_row_with_empty_content_waits_for_content() -> None:
    # OpenCode writes the assistant row before its content. The backend must
    # leave the empty row unseen and translate it when the content arrives.
    empty_row = {
        "id": "m-a", "type": "assistant", "content": [],
        "tokens": {"input": 10, "output": 2},
    }
    filled_row = {
        "id": "m-a", "type": "assistant",
        "content": [{"type": "text", "text": "ready"}],
        "tokens": {"input": 10, "output": 2},
    }
    polls = [
        Poll(False),
        Poll(True, [user_msg("go")]),
        Poll(True, [empty_row, user_msg("go")]),
        Poll(False, [idle_msg("m-i"), filled_row, user_msg("go")]),
    ]
    runner, _factory = make_backend(polls, SessionIdStore(None))
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "go"))
    assert [event.kind for event in events] == [KIND_TEXT, KIND_RESULT]
    assert events[0].text == "ready"
    assert events[1].detail == "in 10 / out 2"


async def test_empty_reply_row_in_idle_poll_waits_for_text() -> None:
    # The idle marker and a not-active flag can land in the same poll as the
    # still-empty assistant row. The turn must wait for the filled row.
    empty_row = {"id": "m-a", "type": "assistant", "content": []}
    filled_row = {
        "id": "m-a", "type": "assistant",
        "content": [{"type": "text", "text": "late"}],
        "tokens": {"input": 12, "output": 4},
    }
    polls = [
        Poll(False),
        Poll(True, [user_msg("go")]),
        Poll(False, [idle_msg("m-i"), empty_row, user_msg("go")]),
        Poll(False, [idle_msg("m-i"), filled_row, user_msg("go")]),
    ]
    runner, _factory = make_backend(polls, SessionIdStore(None))
    events = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "go"))
    assert [event.kind for event in events] == [KIND_TEXT, KIND_RESULT]
    assert events[0].text == "late"
    assert events[1].detail == "in 12 / out 4"


async def test_stop_without_session_does_nothing() -> None:
    runner, factory = make_backend([Poll(False)], SessionIdStore(None))
    await runner.stop("ghost")  # no client and no session: no error
    assert factory.clients == []


async def test_stop_with_no_running_client_interrupts_stored_session(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    runner, factory = make_backend([Poll(False)], store)
    await runner.stop("coder")  # orphaned run: stopped through a short client
    assert len(factory.clients) == 1
    assert factory.clients[0].interrupts == ["s-old"]
    assert factory.clients[0].closed is True


async def test_forget_deletes_the_server_session_and_the_id(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    runner, factory = make_backend([Poll(False)], store)
    await runner._forget("coder")
    assert factory.clients[0].deleted == ["s-old"]
    assert factory.clients[0].closed is True
    assert store.load("coder") == ""


async def test_forget_without_a_session_id_opens_no_client() -> None:
    runner, factory = make_backend([Poll(False)], SessionIdStore(None))
    await runner._forget("ghost")
    assert factory.clients == []


async def test_views_report_stored_session_and_none_context(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("coder", "s-old")
    runner, _factory = make_backend([Poll(False)], store)
    view = await runner.session("coder")
    assert view.session_id == "s-old"
    assert view.context_percent is None
    ghost = await runner.session("ghost")
    assert ghost.session_id == ""
    assert runner.context_percent("coder") is None
    assert await runner.server_info("coder") is None
    assert [row.name for row in await runner.commands("coder")] == ["clear"]


async def test_history_loads_through_the_history_loader() -> None:
    saved = (ChatEvent(KIND_TEXT, "old"),)
    runner, _factory = make_backend([Poll(False)], SessionIdStore(None), events=saved)
    assert await runner.history("coder") == saved


async def test_traits_key_is_opencode() -> None:
    runner, _factory = make_backend([Poll(False)], SessionIdStore(None))
    traits = runner.traits
    assert traits.key == "opencode"
    assert traits.label == "GLM"
    assert traits.tab_mark == "GLM"
    assert traits.session_label == "Session"
    assert traits.resume_template == "opencode --session {session_id}"
    assert traits.shows_context_percent is False
    assert traits.supports_slash_commands is True

