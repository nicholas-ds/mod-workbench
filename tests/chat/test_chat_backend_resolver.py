"""Tests for ChatBackendResolver."""

import asyncio
from pathlib import Path

from workbench.chat.chat_backend import BackendTraits, ChatBackend, SessionView
from workbench.chat.chat_backend_resolver import ChatBackendResolver, FlipResult
from workbench.chat.chat_backend_store import ChatBackendStore
from workbench.chat.chat_event import ChatEvent, KIND_RESULT
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.turn_book import TurnBook
from workbench.chat.turn_event_log import TurnEventLog


def traits_of(key: str) -> BackendTraits:
    return BackendTraits(
        key=key,
        label=key.title(),
        tab_mark=key[0].upper(),
        session_label=f"{key} session",
        resume_template="",
        shows_context_percent=False,
        supports_slash_commands=False,
        supports_resume=False,
    )


class FakeBackend(ChatBackend):
    def __init__(self, key: str, gate: asyncio.Event | None = None) -> None:
        super().__init__(TurnBook(), PendingPermissionStore())
        self._key = key
        self.gate = gate
        self.prompts: list[str] = []
        self.forgotten: list[str] = []
        self.history_events: tuple[ChatEvent, ...] = ()

    @property
    def traits(self) -> BackendTraits:
        return traits_of(self._key)

    async def _turn(
        self, name: str, prompt: str, log: TurnEventLog, handoff: str
    ) -> None:
        self.prompts.append(prompt)
        if self.gate is not None:
            await self.gate.wait()
        log.append(ChatEvent(kind=KIND_RESULT))

    async def _interrupt(self, name: str) -> None:
        return None

    async def _forget(self, name: str) -> None:
        self.forgotten.append(name)

    async def session(self, name: str) -> SessionView:
        return SessionView(session_id="s1", context_percent=None)

    async def history(self, name: str) -> tuple[ChatEvent, ...]:
        return self.history_events

    async def commands(self, name: str) -> tuple[str, ...]:
        return ()

    async def sessions(self, name: str, folder: str) -> tuple[object, ...]:
        return ()

    async def resume_session(
        self, name: str, folder: str, session_id: str
    ) -> bool:
        return False


class NoHandoff:
    def build(self, name: str, from_label: str, events: object) -> str:
        return ""


def make_resolver(backends: dict[str, ChatBackend],
                  path: Path | None = None) -> ChatBackendResolver:
    return ChatBackendResolver(backends, ChatBackendStore(path), NoHandoff())


def two_backends(path: Path | None = None) -> tuple[ChatBackendResolver, ChatBackend, ChatBackend]:
    claude = FakeBackend("claude")
    opencode = FakeBackend("opencode")
    resolver = make_resolver({"claude": claude, "opencode": opencode}, path)
    return resolver, claude, opencode


async def wait_idle(resolver: ChatBackendResolver, name: str) -> None:
    while resolver.is_running(name):
        await asyncio.sleep(0)


async def test_backend_of_defaults_to_claude_entry() -> None:
    resolver, claude, _opencode = two_backends()
    assert resolver.backend_of("coder") is claude


async def test_backend_of_uses_stored_key(tmp_path: Path) -> None:
    resolver, _claude, opencode = two_backends(tmp_path / "chat_backends.json")
    assert (await resolver.flip("coder", "opencode")).ok
    assert resolver.backend_of("coder") is opencode


async def test_backend_of_unknown_stored_key_falls_back_to_default(
        tmp_path: Path) -> None:
    claude = FakeBackend("claude")
    opencode = FakeBackend("opencode")
    store = ChatBackendStore(tmp_path / "chat_backends.json")
    store.save("coder", "mistral")
    resolver = ChatBackendResolver({"claude": claude, "opencode": opencode}, store, NoHandoff())
    assert resolver.backend_of("coder") is claude


async def test_submit_goes_to_the_stored_backend(tmp_path: Path) -> None:
    resolver, claude, opencode = two_backends(tmp_path / "chat_backends.json")
    assert (await resolver.flip("coder", "opencode")).ok
    await resolver.submit("coder", "hello")
    await wait_idle(resolver, "coder")
    assert opencode.prompts == ["hello"]
    assert claude.prompts == []


async def test_forget_retires_every_backend() -> None:
    resolver, claude, opencode = two_backends()
    await resolver.forget("coder")
    assert claude.forgotten == ["coder"]
    assert opencode.forgotten == ["coder"]


def test_all_traits_follow_dict_order() -> None:
    resolver, _claude, _opencode = two_backends()
    assert resolver.all_traits() == (traits_of("claude"), traits_of("opencode"))


async def test_flip_ok_persists_key(tmp_path: Path) -> None:
    path = tmp_path / "chat_backends.json"
    resolver = make_resolver(
        {"claude": FakeBackend("claude"), "opencode": FakeBackend("opencode")},
        path,
    )
    assert await resolver.flip("coder", "opencode") == FlipResult(ok=True, reason="")
    assert ChatBackendStore(path).load("coder") == "opencode"


async def test_flip_refused_while_any_backend_runs() -> None:
    gate = asyncio.Event()
    claude = FakeBackend("claude", gate=gate)
    opencode = FakeBackend("opencode")
    resolver = make_resolver({"claude": claude, "opencode": opencode})
    assert (await resolver.flip("coder", "opencode")).ok
    await resolver.submit("coder", "hello")
    result = await resolver.flip("coder", "claude")
    assert result == FlipResult(ok=False, reason="A turn is running. Stop it first.")
    gate.set()
    await wait_idle(resolver, "coder")


async def test_flip_unknown_key_is_refused() -> None:
    resolver, _claude, _opencode = two_backends()
    assert await resolver.flip("coder", "mistral") == FlipResult(
        ok=False, reason="Unknown backend.")
