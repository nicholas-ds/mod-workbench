"""Tests for the shared chat backend ABC."""

import asyncio
from collections.abc import AsyncIterator

import pytest

from workbench.chat.chat_backend import BackendTraits, ChatBackend, SessionView
from workbench.chat.chat_command import COMMAND_CLEAR, COMMAND_PROMPT, ChatCommand
from workbench.chat.chat_event import (
    ChatEvent,
    KIND_ERROR,
    KIND_NOTICE,
    KIND_RESULT,
    KIND_TEXT,
    KIND_USER,
)
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.turn_book import TurnBook
from workbench.chat.turn_event_log import TurnEventLog


class SpyPermissions(PendingPermissionStore):
    def __init__(self) -> None:
        super().__init__()
        self.denied: list[str] = []

    def answer(self, request_id: str, allowed: bool) -> bool:
        if not allowed:
            self.denied.append(request_id)
        return super().answer(request_id, allowed)


class FakeBackend(ChatBackend):
    def __init__(
        self,
        permissions: PendingPermissionStore | None = None,
        gate: asyncio.Event | None = None,
        fail_text: str = "",
    ) -> None:
        store = permissions if permissions is not None else PendingPermissionStore()
        super().__init__(TurnBook(), store)
        self.gate = gate
        self.fail_text = fail_text
        self.prompts: list[str] = []
        self.handoffs: list[str] = []
        self.interrupted: list[str] = []
        self.forgotten: list[str] = []

    @property
    def traits(self) -> BackendTraits:
        return BackendTraits(
            key="fake",
            label="Fake",
            tab_mark="F",
            session_label="fake session",
            resume_template="",
            shows_context_percent=False,
            supports_slash_commands=False,
            supports_resume=False,
        )

    async def sessions(self, name: str, folder: str) -> tuple[object, ...]:
        return ()

    async def resume_session(
        self, name: str, folder: str, session_id: str
    ) -> bool:
        return False

    async def _turn(
        self, name: str, prompt: str, log: TurnEventLog, handoff: str
    ) -> None:
        self.prompts.append(prompt)
        self.handoffs.append(handoff)
        if self.fail_text:
            raise RuntimeError(self.fail_text)
        log.append(ChatEvent(kind=KIND_TEXT, text=f"echo:{prompt}"))
        if self.gate is not None:
            await self.gate.wait()
        log.append(ChatEvent(kind=KIND_RESULT))

    async def _interrupt(self, name: str) -> None:
        self.interrupted.append(name)

    async def _forget(self, name: str) -> None:
        self.forgotten.append(name)

    async def session(self, name: str) -> SessionView:
        return SessionView(session_id="s1", context_percent=None)

    async def history(self, name: str) -> tuple[ChatEvent, ...]:
        return ()

    async def commands(self, name: str) -> tuple[object, ...]:
        return ()

    def add_hold(self, name: str) -> str:
        request_id = self._permissions.hold()
        self._book.hold(name, request_id)
        return request_id


async def collect(stream: AsyncIterator[ChatEvent]) -> tuple[ChatEvent, ...]:
    return tuple([event async for event in stream])


async def test_run_streams_events_of_one_turn() -> None:
    backend = FakeBackend()
    events = await collect(backend.run("coder", ChatCommand(COMMAND_PROMPT, "hello")))
    assert events == (ChatEvent(KIND_TEXT, "echo:hello"), ChatEvent(KIND_RESULT))
    assert not backend.is_running("coder")


async def test_handoff_reaches_one_turn_only() -> None:
    backend = FakeBackend()
    backend.receive_handoff("coder", "[handoff]\nblock\n[/handoff]")
    await collect(backend.run("coder", ChatCommand(COMMAND_PROMPT, "first")))
    await collect(backend.run("coder", ChatCommand(COMMAND_PROMPT, "second")))
    assert backend.handoffs == ["[handoff]\nblock\n[/handoff]", ""]


async def test_second_run_during_a_turn_yields_busy_error() -> None:
    gate = asyncio.Event()
    backend = FakeBackend(gate=gate)
    stream = backend.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "echo:first")
    refused = await collect(backend.run("coder", ChatCommand(COMMAND_PROMPT, "second")))
    assert refused == (ChatEvent(KIND_ERROR, "A turn is already running."),)
    gate.set()
    assert tuple([event async for event in stream]) == (ChatEvent(KIND_RESULT),)


async def test_clear_forgets_and_yields_notice() -> None:
    backend = FakeBackend()
    events = await collect(backend.run("coder", ChatCommand(COMMAND_CLEAR, "")))
    assert events == (ChatEvent(KIND_NOTICE, "Chat cleared."),)
    assert backend.forgotten == ["coder"]


async def test_submit_while_running_queues_and_runs_after() -> None:
    gate = asyncio.Event()
    backend = FakeBackend(gate=gate)
    stream = backend.run("coder", ChatCommand(COMMAND_PROMPT, "first"))
    assert await stream.__anext__() == ChatEvent(KIND_TEXT, "echo:first")
    await backend.submit("coder", "second")
    gate.set()
    assert tuple([event async for event in stream]) == (ChatEvent(KIND_RESULT),)
    while backend.is_running("coder"):
        await asyncio.sleep(0)
    assert backend.prompts == ["first", "second"]


async def test_submit_when_idle_starts_announced_turn() -> None:
    gate = asyncio.Event()
    backend = FakeBackend(gate=gate)
    await backend.submit("coder", "hello")
    stream = backend.follow("coder")
    assert await stream.__anext__() == ChatEvent(KIND_USER, "hello")
    gate.set()
    rest = await collect(stream)
    assert rest == (ChatEvent(KIND_TEXT, "echo:hello"), ChatEvent(KIND_RESULT))


async def test_turn_failure_yields_one_error_and_clears_running() -> None:
    backend = FakeBackend(fail_text="boom")
    events = await collect(backend.run("coder", ChatCommand(COMMAND_PROMPT, "hello")))
    assert events == (ChatEvent(KIND_ERROR, "boom"),)
    assert not backend.is_running("coder")


async def test_stop_interrupts_and_denies_holds() -> None:
    permissions = SpyPermissions()
    backend = FakeBackend(permissions=permissions)
    request_id = backend.add_hold("coder")
    await backend.stop("coder")
    assert backend.interrupted == ["coder"]
    assert permissions.denied == [request_id]
    assert permissions.open_ids() == ()


def test_backend_cannot_be_instantiated_without_abstract_methods() -> None:
    with pytest.raises(TypeError):
        ChatBackend(TurnBook(), PendingPermissionStore())
