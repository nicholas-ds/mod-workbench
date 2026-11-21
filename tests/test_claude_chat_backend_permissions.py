"""Tests for permission prompts in the Claude chat session runner."""

import asyncio
from collections.abc import AsyncIterator, Callable

from claude_agent_sdk import (
    AssistantMessage,
    CanUseTool,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    TextBlock,
)

from workbench.chat_command import COMMAND_PROMPT, ChatCommand
from workbench.chat_event import (
    KIND_PERMISSION,
    KIND_PERMISSION_SETTLED,
    KIND_TEXT,
    ChatEvent,
)
from workbench.claude_sdk_translator import ClaudeSdkTranslator
from workbench.claude_chat_backend import ClaudeChatBackend
from workbench.permission_card_builder import PermissionCardBuilder
from workbench.pending_permission_store import PendingPermissionStore
from workbench.session_id_store import SessionIdStore
from workbench.slash_command_lister import SlashCommandLister
from workbench.turn_book import TurnBook

from runner_fakes import StubHistoryLoader, FakeSessionLister


class FakeToolContext:
    def __init__(self) -> None:
        self.title = "Run git status?"
        self.display_name = "Run command"


class PermissionChatClient:
    def __init__(self, can_use_tool: CanUseTool | None = None) -> None:
        self.can_use_tool = can_use_tool
        self.permission_result: PermissionResult | None = None

    async def connect(self) -> None: ...

    async def query(self, prompt: str) -> None: ...

    async def receive_response(self) -> AsyncIterator[object]:
        if self.can_use_tool is not None:
            self.permission_result = await self.can_use_tool(
                "Bash", {"command": "git status"}, FakeToolContext()
            )
        yield AssistantMessage(content=[TextBlock(text="done")], model="m")

    async def interrupt(self) -> None: ...

    async def disconnect(self) -> None: ...


class PermissionClientFactory:
    def __init__(self) -> None:
        self.clients: list[PermissionChatClient] = []
        self.callbacks: list[CanUseTool | None] = []

    def __call__(
        self, name: str, resume: str, can_use_tool: CanUseTool | None = None
    ) -> PermissionChatClient:
        self.callbacks.append(can_use_tool)
        client = PermissionChatClient(can_use_tool=can_use_tool)
        self.clients.append(client)
        return client


def make_runner(
    timeout_seconds: float = 600.0,
    on_permission_wait: Callable[[str, str], None] = lambda name, tool_name: None,
    alert_after_seconds: float = 30.0,
) -> tuple[ClaudeChatBackend, PermissionClientFactory, PendingPermissionStore]:
    factory = PermissionClientFactory()
    permissions = PendingPermissionStore()
    runner = ClaudeChatBackend(
        TurnBook(),
        factory,
        SessionIdStore(None),
        ClaudeSdkTranslator(),
        permissions,
        PermissionCardBuilder(),
        StubHistoryLoader(),
        SlashCommandLister(),
        FakeSessionLister(),
        timeout_seconds,
        on_permission_wait=on_permission_wait,
        alert_after_seconds=alert_after_seconds,
    )
    return runner, factory, permissions


async def test_permission_card_is_streamed_before_the_reply() -> None:
    runner, _factory, permissions = make_runner()
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    card = await stream.__anext__()
    assert card.kind == KIND_PERMISSION
    assert card.text == "Run git status?"
    assert permissions.answer(card.detail, True)
    settled = await stream.__anext__()
    assert settled == ChatEvent(KIND_PERMISSION_SETTLED, "allowed", "", card.detail)
    text = await stream.__anext__()
    assert text == ChatEvent(KIND_TEXT, "done")
    assert tuple([event async for event in stream]) == ()


async def test_allow_gives_an_allow_result() -> None:
    runner, factory, permissions = make_runner()
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    card = await stream.__anext__()
    permissions.answer(card.detail, True)
    events = tuple([event async for event in stream])
    result = factory.clients[0].permission_result
    assert isinstance(result, PermissionResultAllow)
    assert ChatEvent(KIND_TEXT, "done") in events
    assert any(
        event.kind == KIND_PERMISSION_SETTLED and event.text == "allowed"
        for event in events
    )


async def test_deny_gives_a_deny_result_with_a_message() -> None:
    runner, factory, permissions = make_runner()
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    card = await stream.__anext__()
    permissions.answer(card.detail, False)
    tuple([event async for event in stream])
    result = factory.clients[0].permission_result
    assert isinstance(result, PermissionResultDeny)
    assert result.message == "The author denied this request."


async def test_timeout_settles_the_card_and_denies() -> None:
    runner, factory, permissions = make_runner(timeout_seconds=0.05)
    events = tuple(
        [event async for event in runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))]
    )
    settled = next(
        event for event in events if event.kind == KIND_PERMISSION_SETTLED
    )
    assert settled.text == "timed out"
    result = factory.clients[0].permission_result
    assert isinstance(result, PermissionResultDeny)
    assert result.message == "The author did not answer in time."
    assert permissions.open_ids() == ()
    assert ChatEvent(KIND_TEXT, "done") in events


async def test_stop_denies_open_requests_of_that_name_only() -> None:
    runner, _factory, permissions = make_runner()
    stream_a = runner.run("a", ChatCommand(COMMAND_PROMPT, "hello"))
    stream_b = runner.run("b", ChatCommand(COMMAND_PROMPT, "hello"))
    card_a = await stream_a.__anext__()
    card_b = await stream_b.__anext__()
    assert permissions.open_ids() == (card_a.detail, card_b.detail)
    await runner.stop("a")
    assert permissions.open_ids() == (card_b.detail,)
    rest_a = tuple([event async for event in stream_a])
    assert any(
        event.kind == KIND_PERMISSION_SETTLED and event.text == "denied"
        for event in rest_a
    )
    permissions.answer(card_b.detail, True)
    rest_b = tuple([event async for event in stream_b])
    assert ChatEvent(KIND_TEXT, "done") in rest_b


async def test_leaving_the_stream_keeps_open_requests() -> None:
    runner, _factory, permissions = make_runner()
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    card = await stream.__anext__()
    assert permissions.open_ids() == (card.detail,)
    await stream.aclose()
    assert permissions.open_ids() == (card.detail,)
    follower = runner.follow("coder")
    assert await follower.__anext__() == card
    permissions.answer(card.detail, True)
    rest = tuple([event async for event in follower])
    assert ChatEvent(KIND_TEXT, "done") in rest


async def test_answered_request_never_alerts() -> None:
    calls: list[tuple[str, str]] = []
    runner, _factory, permissions = make_runner(
        on_permission_wait=lambda name, tool_name: calls.append((name, tool_name)),
        alert_after_seconds=0.01,
    )
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    card = await stream.__anext__()
    permissions.answer(card.detail, True)
    tuple([event async for event in stream])
    await asyncio.sleep(0.05)
    assert calls == []


async def test_open_request_alerts_once_with_name_and_tool() -> None:
    calls: list[tuple[str, str]] = []
    runner, _factory, permissions = make_runner(
        on_permission_wait=lambda name, tool_name: calls.append((name, tool_name)),
        alert_after_seconds=0.01,
    )
    stream = runner.run("coder", ChatCommand(COMMAND_PROMPT, "hello"))
    card = await stream.__anext__()
    await asyncio.sleep(0.05)
    assert calls == [("coder", "Bash")]
    permissions.answer(card.detail, True)
    tuple([event async for event in stream])
