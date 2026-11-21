"""Tests for the OpenCode chat backend permissions and stopping a live turn."""

from __future__ import annotations

import asyncio
from pathlib import Path

from workbench.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat_event import (
    ChatEvent,
    KIND_ERROR,
    KIND_PERMISSION,
    KIND_PERMISSION_SETTLED,
    KIND_TEXT,
    KIND_RESULT,
)
from workbench.pending_permission_store import PendingPermissionStore
from workbench.session_id_store import SessionIdStore

from opencode_fakes import (
    assistant_msg,
    collect,
    idle_msg,
    make_backend,
    perm_request,
    Poll,
    user_msg,
)


async def test_run_yields_events_and_second_run_is_rejected(tmp_path: Path) -> None:
    polls = [
        Poll(False),
        Poll(True, [user_msg("go")]),
        Poll(True, [user_msg("go")], permissions=[perm_request()]),
    ]
    permissions = PendingPermissionStore()
    runner, factory = make_backend(
        polls, SessionIdStore(tmp_path / "ids.json"), permissions
    )
    first: list[ChatEvent] = []
    got_card = asyncio.Event()

    async def consume() -> None:
        async for event in runner.run("coder", ChatCommand(COMMAND_PROMPT, "go")):
            first.append(event)
            if event.kind == KIND_PERMISSION:
                got_card.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_card.wait(), 2.0)
    assert runner.is_running("coder") is True
    second = await collect(runner, "coder", ChatCommand(COMMAND_PROMPT, "again"))
    assert second == (ChatEvent(kind=KIND_ERROR, text="A turn is already running."),)
    factory.clients[0].polls.append(
        Poll(False, [idle_msg("m-i"), assistant_msg("done", "m-a"), user_msg("go")])
    )
    permissions.answer(first[-1].detail, True)
    await asyncio.wait_for(task, 2.0)
    assert runner.is_running("coder") is False


async def test_permission_allow_answers_and_settles() -> None:
    polls = [
        Poll(False),
        Poll(True, [user_msg("go")]),
        Poll(True, [user_msg("go")], permissions=[perm_request()]),
    ]
    permissions = PendingPermissionStore()
    runner, factory = make_backend(polls, SessionIdStore(None), permissions)
    events: list[ChatEvent] = []
    got_card = asyncio.Event()

    async def consume() -> None:
        async for event in runner.run("coder", ChatCommand(COMMAND_PROMPT, "go")):
            events.append(event)
            if event.kind == KIND_PERMISSION:
                got_card.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_card.wait(), 2.0)
    card = events[-1]
    assert card.kind == KIND_PERMISSION
    assert card.tool_name == "write"
    assert card.detail in permissions.open_ids()
    factory.clients[0].polls.append(
        Poll(False, [idle_msg("m-i"), assistant_msg("ok", "m-t"), user_msg("go")])
    )
    assert permissions.answer(card.detail, True) is True
    await asyncio.wait_for(task, 2.0)
    assert factory.clients[0].answers == [("s-new", "p1", True)]
    assert events[1] == ChatEvent(
        kind=KIND_PERMISSION_SETTLED, text="allowed", detail=card.detail
    )
    assert [event.kind for event in events] == [
        KIND_PERMISSION,
        KIND_PERMISSION_SETTLED,
        KIND_TEXT,
        KIND_RESULT,
    ]


async def test_permission_deny_answers_reject() -> None:
    polls = [
        Poll(False),
        Poll(True, [user_msg("go")]),
        Poll(True, [user_msg("go")], permissions=[perm_request()]),
    ]
    permissions = PendingPermissionStore()
    runner, factory = make_backend(polls, SessionIdStore(None), permissions)
    events: list[ChatEvent] = []
    got_card = asyncio.Event()

    async def consume() -> None:
        async for event in runner.run("coder", ChatCommand(COMMAND_PROMPT, "go")):
            events.append(event)
            if event.kind == KIND_PERMISSION:
                got_card.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_card.wait(), 2.0)
    card = events[-1]
    factory.clients[0].polls.append(
        Poll(False, [idle_msg("m-i"), assistant_msg("ok", "m-t"), user_msg("go")])
    )
    assert permissions.answer(card.detail, False) is True
    await asyncio.wait_for(task, 2.0)
    assert factory.clients[0].answers == [("s-new", "p1", False)]
    assert events[1] == ChatEvent(
        kind=KIND_PERMISSION_SETTLED, text="denied", detail=card.detail
    )
    assert [event.kind for event in events] == [
        KIND_PERMISSION,
        KIND_PERMISSION_SETTLED,
        KIND_TEXT,
        KIND_RESULT,
    ]


async def test_stop_interrupts_running_session(tmp_path: Path) -> None:
    polls = [
        Poll(False),
        Poll(True, [user_msg("go")]),
        Poll(True, [user_msg("go")], permissions=[perm_request()]),
    ]
    permissions = PendingPermissionStore()
    runner, factory = make_backend(
        polls, SessionIdStore(tmp_path / "ids.json"), permissions
    )
    await runner.stop("ghost")  # no session stored: no client, no error
    assert factory.clients == []
    events: list[ChatEvent] = []
    got_card = asyncio.Event()

    async def consume() -> None:
        async for event in runner.run("coder", ChatCommand(COMMAND_PROMPT, "go")):
            events.append(event)
            if event.kind == KIND_PERMISSION:
                got_card.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_card.wait(), 2.0)
    await runner.stop("coder")
    assert factory.clients[0].interrupts == ["s-new"]
    factory.clients[0].polls.append(
        Poll(False, [idle_msg("m-i"), assistant_msg("ok", "m-t"), user_msg("go")])
    )
    permissions.answer(events[-1].detail, True)
    await asyncio.wait_for(task, 2.0)
