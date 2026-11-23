"""Shared fakes and factories for the Claude chat session runner tests."""

import asyncio
from collections.abc import AsyncIterator

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from workbench.chat.chat_event import ChatEvent
from workbench.claude.claude_sdk_translator import ClaudeSdkTranslator
from workbench.claude.claude_chat_backend import ClaudeChatBackend
from workbench.chat.permission_card_builder import PermissionCardBuilder
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.session_id_store import SessionIdStore
from workbench.chat.session_summary import SessionSummary
from workbench.chat.slash_command_lister import SlashCommandLister
from workbench.chat.turn_book import TurnBook


class StubHistoryLoader:
    """In-memory history loader: no saved conversation."""

    def load(self, name: str) -> tuple[ChatEvent, ...]:
        return ()


class FakeSessionLister:
    """Records folders; returns canned session summary rows."""

    def __init__(self, summaries: tuple[SessionSummary, ...] = ()) -> None:
        self.summaries = summaries
        self.folders: list[str] = []

    def list(self, folder: str) -> tuple[SessionSummary, ...]:
        self.folders.append(folder)
        return self.summaries


class FakeChatClient:
    """Fake SDK client: one message batch per query, stream stays open."""

    def __init__(self, messages: tuple[object, ...] = (), fail: bool = False) -> None:
        self.messages = messages
        self.fail = fail
        self.calls: list[str] = []
        self._turn_ready = asyncio.Event()
        self._closed = False

    async def connect(self) -> None:
        self.calls.append("connect")

    async def query(self, prompt: str) -> None:
        self.calls.append(f"query:{prompt}")
        if self.fail:
            raise RuntimeError("boom")
        self._turn_ready.set()

    async def receive_messages(self) -> AsyncIterator[object]:
        while True:
            await self._turn_ready.wait()
            if self._closed:
                return
            self._turn_ready.clear()
            for message in self.messages:
                yield message

    async def interrupt(self) -> None:
        self.calls.append("interrupt")

    async def disconnect(self) -> None:
        self.calls.append("disconnect")
        self._closed = True
        self._turn_ready.set()

    async def get_server_info(self) -> dict[str, object] | None:
        self.calls.append("server_info")
        return {"commands": [{"name": "clear", "description": "Clear"}]}

    async def get_context_usage(self) -> dict[str, object]:
        self.calls.append("context_usage")
        return {"percentage": 12.5}


class FakeClientFactory:
    def __init__(self, messages: tuple[object, ...] = (), fail: bool = False) -> None:
        self.messages = messages
        self.fail = fail
        self.clients: list[FakeChatClient] = []
        self.requested: list[tuple[str, str]] = []
        self.callbacks: list[object] = []

    def __call__(
        self, name: str, resume: str, can_use_tool: object = None
    ) -> FakeChatClient:
        self.requested.append((name, resume))
        self.callbacks.append(can_use_tool)
        client = FakeChatClient(messages=self.messages, fail=self.fail)
        self.clients.append(client)
        return client


def make_assistant(text: str) -> AssistantMessage:
    return AssistantMessage(content=[TextBlock(text=text)], model="m")


def make_result(session_id: str) -> ResultMessage:
    return ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
        num_turns=1, session_id=session_id, total_cost_usd=None, result="done",
    )


def make_runner(
    store: SessionIdStore,
    messages: tuple[object, ...] = (make_result("s1"),),
    fail: bool = False,
    session_lister: FakeSessionLister | None = None,
) -> tuple[ClaudeChatBackend, FakeClientFactory]:
    factory = FakeClientFactory(messages=messages, fail=fail)
    lister = session_lister if session_lister is not None else FakeSessionLister()
    runner = ClaudeChatBackend(
        TurnBook(),
        factory,
        store,
        ClaudeSdkTranslator(),
        PendingPermissionStore(),
        PermissionCardBuilder(),
        StubHistoryLoader(),
        SlashCommandLister(),
        lister,
    )
    return runner, factory


class HeldChatClient:
    """Fake client that holds each turn open until the test releases it."""

    def __init__(self, release: asyncio.Event, messages: tuple[object, ...]) -> None:
        self.release = release
        self.messages = messages
        self.calls: list[str] = []
        self._turn_ready = asyncio.Event()
        self._closed = False

    async def connect(self) -> None:
        self.calls.append("connect")

    async def query(self, prompt: str) -> None:
        self.calls.append(f"query:{prompt}")
        self._turn_ready.set()

    async def receive_messages(self) -> AsyncIterator[object]:
        while True:
            await self._turn_ready.wait()
            if self._closed:
                return
            self._turn_ready.clear()
            yield make_assistant("hi")
            await self.release.wait()
            for message in self.messages:
                yield message

    async def interrupt(self) -> None:
        self.calls.append("interrupt")

    async def disconnect(self) -> None:
        self.calls.append("disconnect")
        self._closed = True
        self._turn_ready.set()


class HeldClientFactory:
    def __init__(self, release: asyncio.Event, messages: tuple[object, ...] = ()) -> None:
        self.release = release
        self.messages = messages
        self.clients: list[HeldChatClient] = []

    def __call__(
        self, name: str, resume: str, can_use_tool: object = None
    ) -> HeldChatClient:
        client = HeldChatClient(self.release, self.messages)
        self.clients.append(client)
        return client


def make_held_runner(
    release: asyncio.Event,
    messages: tuple[object, ...] = (make_result("s1"),),
    session_lister: FakeSessionLister | None = None,
) -> tuple[ClaudeChatBackend, HeldClientFactory]:
    factory = HeldClientFactory(release, messages)
    lister = session_lister if session_lister is not None else FakeSessionLister()
    runner = ClaudeChatBackend(
        TurnBook(),
        factory,
        SessionIdStore(None),
        ClaudeSdkTranslator(),
        PendingPermissionStore(),
        PermissionCardBuilder(),
        StubHistoryLoader(),
        SlashCommandLister(),
        lister,
    )
    return runner, factory
