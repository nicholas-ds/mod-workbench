"""Shared fakes and factories for the OpenCode chat backend tests."""

from __future__ import annotations

from workbench.chat.chat_command import ChatCommand
from workbench.chat.chat_event import ChatEvent
from workbench.opencode.opencode_chat_backend import OpencodeChatBackend
from workbench.opencode.opencode_chat_translator import OpencodeChatTranslator
from workbench.opencode.opencode_turn_follower import OpencodeTurnFollower
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.permission_card_builder import PermissionCardBuilder
from workbench.chat.session_id_store import SessionIdStore
from workbench.chat.turn_book import TurnBook

DIRECTORY = "E:/repos/mods/fake-repo"


def user_msg(text: str, mid: str = "m-u") -> dict:
    return {"id": mid, "type": "user", "text": text}


def assistant_msg(text: str, mid: str, tokens: dict | None = None) -> dict:
    message = {
        "id": mid,
        "type": "assistant",
        "content": [{"type": "text", "text": text}],
        "finish": "stop",
    }
    if tokens is not None:
        message["tokens"] = tokens
    return message


def idle_msg(mid: str, outcome: str = "succeeded") -> dict:
    return {"id": mid, "type": "idle", "outcome": outcome}


def perm_request() -> dict:
    return {
        "id": "p1",
        "sessionID": "s-new",
        "action": "write",
        "resources": ["E:/repos/mods/x.txt"],
    }


class Poll:
    """One scripted poll: the messages, active flag and permissions returned."""

    def __init__(self, active: bool, messages=(), permissions=()) -> None:
        self.active = active
        self.messages = list(messages)
        self.permissions = list(permissions)


class FakeClient:
    """Same async surface as OpencodeHttpClient, scripted per poll."""

    def __init__(self, polls: list[Poll], session_id: str = "s-new") -> None:
        self.polls = list(polls)
        self.session_id = session_id
        self._index = 0
        self.prompts: list[str] = []
        self.created: list[tuple[str, str]] = []
        self.synthetics: list[str] = []
        self.answers: list[tuple[str, str, bool]] = []
        self.interrupts: list[str] = []
        self.deleted: list[str] = []
        self.closed = False

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        self.closed = True

    async def create_session(self, title: str, directory: str) -> str:
        self.created.append((title, directory))
        return self.session_id

    async def prompt(self, session_id: str, text: str) -> None:
        self.prompts.append(text)

    async def add_synthetic(self, session_id: str, text: str) -> None:
        self.synthetics.append(text)

    def _poll(self) -> Poll:
        poll = self.polls[min(self._index, len(self.polls) - 1)]
        self._index += 1
        return poll

    def _current(self) -> Poll:
        index = min(self._index - 1, len(self.polls) - 1)
        return self.polls[max(index, 0)]

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

    async def delete_session(self, session_id: str) -> None:
        self.deleted.append(session_id)


class FakeFactory:
    def __init__(self, polls: list[Poll], session_id: str = "s-new") -> None:
        self.polls = polls
        self.session_id = session_id
        self.clients: list[FakeClient] = []

    def __call__(self) -> FakeClient:
        client = FakeClient(self.polls, self.session_id)
        self.clients.append(client)
        return client


class FakeDirectory:
    def folder_of(self, name: str) -> str:
        return DIRECTORY


class StubHistoryLoader:
    """In-memory history loader handing back one canned event tuple."""

    def __init__(self, events: tuple[ChatEvent, ...] = ()) -> None:
        self.events = events
        self.requested: list[str] = []

    async def load(self, name: str) -> tuple[ChatEvent, ...]:
        self.requested.append(name)
        return self.events


class FakeServerProcess:
    """Stands in for the opencode serve child process; records stop calls."""

    def __init__(self) -> None:
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


def make_backend(
    polls: list[Poll],
    store: SessionIdStore,
    permissions: PendingPermissionStore | None = None,
    session_id: str = "s-new",
    events: tuple[ChatEvent, ...] = (),
    timeout_seconds: float = 5.0,
    poll_seconds: float = 0.01,
) -> tuple[OpencodeChatBackend, FakeFactory]:
    factory = FakeFactory(polls, session_id)
    permissions = permissions if permissions is not None else PendingPermissionStore()
    book = TurnBook()
    follower = OpencodeTurnFollower(
        OpencodeChatTranslator(),
        permissions,
        PermissionCardBuilder(),
        book,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    backend = OpencodeChatBackend(
        book,
        factory,
        store,
        permissions,
        FakeDirectory(),
        follower,
        StubHistoryLoader(events),
        FakeServerProcess(),
    )
    return backend, factory


async def collect(
    backend: OpencodeChatBackend, name: str, command: ChatCommand
) -> tuple[ChatEvent, ...]:
    return tuple([event async for event in backend.run(name, command)])
