"""Tests for the OpenCode turn follower (fake client, no HTTP)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest

from workbench.chat_event import (
    ChatEvent, KIND_PERMISSION, KIND_PERMISSION_SETTLED,
    KIND_RESULT, KIND_TEXT,
)
from workbench.opencode_chat_translator import OpencodeChatTranslator
from workbench.opencode_turn_follower import OpencodeTurnFollower, TurnProgress
from workbench.pending_permission_store import PendingPermissionStore
from workbench.permission_card_builder import PermissionCardBuilder
from workbench.turn_book import TurnBook
from workbench.turn_event_log import TurnEventLog


def user_msg(text: str, mid: str = "m-u") -> dict:
    return {"id": mid, "type": "user", "text": text}


def assistant_msg(text: str, mid: str, tokens: dict | None = None) -> dict:
    message = {
        "id": mid, "type": "assistant",
        "content": [{"type": "text", "text": text}], "finish": "stop",
    }
    if tokens is not None:
        message["tokens"] = tokens
    return message


def idle_msg(mid: str, outcome: str = "succeeded") -> dict:
    return {"id": mid, "type": "idle", "outcome": outcome}


def perm_request() -> dict:
    return {
        "id": "p1", "sessionID": "s-new", "action": "write",
        "resources": ["E:/repos/mods/x.txt"],
    }


EMPTY_ROW = {"id": "m-a", "type": "assistant", "content": []}


class Poll:
    """One scripted poll: the messages, active flag and permissions returned."""

    def __init__(
        self,
        active: bool,
        messages: Sequence[dict] = (),
        permissions: Sequence[dict] = (),
    ) -> None:
        self.active = active
        self.messages = list(messages)
        self.permissions = list(permissions)


class FakeClient:
    """Same async surface as OpencodeHttpClient, scripted per poll."""

    def __init__(self, polls: list[Poll], session_id: str = "s-new") -> None:
        self.polls = list(polls)
        self.session_id = session_id
        self._index = 0
        self.answers: list[tuple[str, str, bool]] = []
        self.interrupts: list[str] = []

    def _poll(self) -> Poll:
        poll = self.polls[min(self._index, len(self.polls) - 1)]
        self._index += 1
        return poll

    def _current(self) -> Poll:
        return self.polls[min(self._index - 1, len(self.polls) - 1)]

    async def messages(self, session_id: str) -> list[dict]:
        return list(self._poll().messages)

    async def is_active(self, session_id: str) -> bool:
        return self._current().active

    async def permission_requests(self, session_id: str) -> list[dict]:
        return list(self._current().permissions)

    async def answer_permission(
        self, session_id: str, request_id: str, allow: bool
    ) -> None:
        self.answers.append((session_id, request_id, allow))

    async def interrupt(self, session_id: str) -> None:
        self.interrupts.append(session_id)


def make_follower(
    permissions: PendingPermissionStore | None = None,
    timeout_seconds: float = 5.0, poll_seconds: float = 0.01,
) -> tuple[OpencodeTurnFollower, PendingPermissionStore, TurnBook]:
    store = permissions if permissions is not None else PendingPermissionStore()
    book = TurnBook()
    follower = OpencodeTurnFollower(
        OpencodeChatTranslator(), store, PermissionCardBuilder(), book,
        timeout_seconds=timeout_seconds, poll_seconds=poll_seconds,
    )
    return follower, store, book


async def run_follow(
    polls: list[Poll], seen: frozenset[str] = frozenset(),
    timeout_seconds: float = 5.0, poll_seconds: float = 0.01,
) -> tuple[FakeClient, TurnEventLog, PendingPermissionStore, TurnBook]:
    client = FakeClient(polls)
    follower, permissions, book = make_follower(
        timeout_seconds=timeout_seconds, poll_seconds=poll_seconds
    )
    log = TurnEventLog()
    await asyncio.wait_for(follower.follow("coder", client, "s-new", log, seen), 2.0)
    return client, log, permissions, book


async def wait_for_card(log: TurnEventLog) -> ChatEvent:
    while not any(event.kind == KIND_PERMISSION for event in log.events()):
        await asyncio.sleep(0.01)
    return next(event for event in log.events() if event.kind == KIND_PERMISSION)


def progress(idle_seen: bool, pending_reply: bool) -> TurnProgress:
    return TurnProgress(
        frozenset(), None, None, idle_seen=idle_seen, pending_reply=pending_reply
    )


def test_is_finished_truth_table() -> None:
    assert not progress(False, False).is_finished(False)
    assert not progress(False, False).is_finished(True)
    assert not progress(True, False).is_finished(True)
    assert not progress(True, True).is_finished(False)
    assert not progress(True, True).is_finished(True)
    assert progress(True, False).is_finished(False)


async def test_reply_text_reaches_log_in_order() -> None:
    newest_first = [
        idle_msg("m-i"),
        assistant_msg("a2", "m-2", tokens={"input": 160, "output": 467}),
        assistant_msg("a1", "m-1"),
        user_msg("q", "m-u"),
    ]
    _client, log, _permissions, _book = await run_follow(
        [Poll(False), Poll(False, newest_first)]
    )
    assert log.events() == (
        ChatEvent(kind=KIND_TEXT, text="a1"),
        ChatEvent(kind=KIND_TEXT, text="a2"),
        ChatEvent(kind=KIND_RESULT, text="succeeded", detail="in 160 / out 467"),
    )


async def test_empty_assistant_row_waits_for_filled_row() -> None:
    ready = assistant_msg("ready", "m-a", tokens={"input": 10, "output": 2})
    polls = [
        Poll(True, [EMPTY_ROW, user_msg("go")]),
        Poll(True, [EMPTY_ROW, user_msg("go")]),
        Poll(False, [idle_msg("m-i"), ready, user_msg("go")]),
    ]
    _client, log, _permissions, _book = await run_follow(polls)
    assert [event.kind for event in log.events()] == [KIND_TEXT, KIND_RESULT]
    assert log.events()[0].text == "ready"
    assert log.events()[1].detail == "in 10 / out 2"


async def test_turn_ends_only_after_idle_inactive_and_no_pending() -> None:
    late = assistant_msg("late", "m-a", tokens={"input": 12, "output": 4})
    polls = [
        Poll(True, [user_msg("go")]),
        Poll(True, [idle_msg("m-i"), user_msg("go")]),
        Poll(False, [idle_msg("m-i"), EMPTY_ROW, user_msg("go")]),
        Poll(False, [idle_msg("m-i"), late, user_msg("go")]),
    ]
    _client, log, _permissions, _book = await run_follow(polls)
    assert [event.kind for event in log.events()] == [KIND_TEXT, KIND_RESULT]
    assert log.events()[0].text == "late"
    assert log.events()[1].detail == "in 12 / out 4"


async def test_tokens_reach_translate() -> None:
    polls = [
        Poll(True, [user_msg("go")]),
        Poll(False, [
            idle_msg("m-i"),
            assistant_msg("done", "m-a", tokens={"input": 10, "output": 2}),
            user_msg("go"),
        ]),
    ]
    _client, log, _permissions, _book = await run_follow(polls)
    assert log.events()[-1] == ChatEvent(
        kind=KIND_RESULT, text="succeeded", detail="in 10 / out 2"
    )


async def test_permission_card_waits_answers_and_settles() -> None:
    polls = [
        Poll(True, [user_msg("go")]),
        Poll(True, [user_msg("go")], permissions=[perm_request()]),
    ]
    client = FakeClient(polls)
    follower, permissions, book = make_follower()
    log = TurnEventLog()
    task = asyncio.create_task(follower.follow("coder", client, "s-new", log, frozenset()))
    card = await asyncio.wait_for(wait_for_card(log), 2.0)
    assert card.tool_name == "write"
    assert card.detail in permissions.open_ids()
    assert book.take_holds("coder") == frozenset({card.detail})
    client.polls.append(
        Poll(False, [idle_msg("m-i"), assistant_msg("ok", "m-t"), user_msg("go")])
    )
    assert permissions.answer(card.detail, True) is True
    await asyncio.wait_for(task, 2.0)
    assert client.answers == [("s-new", "p1", True)]
    assert book.take_holds("coder") == frozenset()
    assert log.events() == (
        card,
        ChatEvent(kind=KIND_PERMISSION_SETTLED, text="allowed", detail=card.detail),
        ChatEvent(kind=KIND_TEXT, text="ok"),
        ChatEvent(kind=KIND_RESULT, text="succeeded", detail="in 0 / out 0"),
    )


@pytest.mark.parametrize("break_interrupt", [False, True])
async def test_deadline_interrupts_once_then_raises(break_interrupt: bool) -> None:
    class BrokenClient(FakeClient):
        async def interrupt(self, session_id: str) -> None:
            raise OSError("boom")

    polls = [Poll(True, [user_msg("go")])]
    client = BrokenClient(polls) if break_interrupt else FakeClient(polls)
    follower, _permissions, _book = make_follower(timeout_seconds=0.05, poll_seconds=0.001)
    with pytest.raises(TimeoutError, match="timed out"):
        await follower.follow("coder", client, "s-new", TurnEventLog(), frozenset())
    if not break_interrupt:
        assert client.interrupts == ["s-new"]
