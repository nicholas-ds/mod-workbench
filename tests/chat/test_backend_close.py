"""Tests: the base close is a no-op; resolver close_all survives failures."""

from __future__ import annotations

import pytest

from workbench.chat.chat_backend import BackendTraits, ChatBackend, SessionView
from workbench.chat.chat_backend_resolver import ChatBackendResolver
from workbench.chat.chat_backend_store import ChatBackendStore
from workbench.chat.chat_event import ChatEvent
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.session_summary import SessionSummary
from workbench.chat.slash_command_lister import SlashCommandInfo
from workbench.chat.turn_book import TurnBook
from workbench.chat.turn_event_log import TurnEventLog


class StubBackend(ChatBackend):
    """Implements only the abstract surface; close stays the inherited no-op."""

    @property
    def traits(self) -> BackendTraits:
        raise NotImplementedError

    async def _turn(
        self, name: str, prompt: str, log: TurnEventLog, handoff: str
    ) -> None:
        raise NotImplementedError

    async def _interrupt(self, name: str) -> None:
        raise NotImplementedError

    async def _forget(self, name: str) -> None:
        raise NotImplementedError

    async def session(self, name: str) -> SessionView:
        raise NotImplementedError

    async def history(self, name: str) -> tuple[ChatEvent, ...]:
        raise NotImplementedError

    async def commands(self, name: str) -> tuple[SlashCommandInfo, ...]:
        raise NotImplementedError

    async def sessions(
        self, name: str, folder: str
    ) -> tuple[SessionSummary, ...]:
        raise NotImplementedError

    async def resume_session(
        self, name: str, folder: str, session_id: str
    ) -> bool:
        raise NotImplementedError


class RecordingBackend(StubBackend):
    """Records close calls; raises the stored error when one is set."""

    def __init__(self, key: str, error: Exception | None = None) -> None:
        super().__init__(TurnBook(), PendingPermissionStore())
        self.key = key
        self.error = error
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1
        if self.error is not None:
            raise self.error


class NoHandoff:
    def build(self, name: str, from_label: str, events: object) -> str:
        return ""


def make_resolver(backends: dict[str, ChatBackend]) -> ChatBackendResolver:
    return ChatBackendResolver(backends, ChatBackendStore(None), NoHandoff())


async def test_base_close_is_a_noop() -> None:
    backend = StubBackend(TurnBook(), PendingPermissionStore())
    await backend.close()


async def test_close_all_closes_every_backend_once() -> None:
    claude = RecordingBackend("claude")
    opencode = RecordingBackend("opencode")
    resolver = make_resolver({"claude": claude, "opencode": opencode})
    await resolver.close_all()
    assert claude.close_calls == 1
    assert opencode.close_calls == 1


async def test_close_all_keeps_going_past_one_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    claude = RecordingBackend("claude", error=RuntimeError("boom"))
    opencode = RecordingBackend("opencode")
    resolver = make_resolver({"claude": claude, "opencode": opencode})
    await resolver.close_all()
    assert opencode.close_calls == 1
    assert "[Workbench] backend close failed: claude: boom" in (
        capsys.readouterr().err)
