"""Pick the backend of a chat in one place: stored key to backend instance.

backend_of reads the store and falls back to the default backend entry.
forget retires the chat on every backend, because a flipped chat may hold
state in the old one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from workbench.chat_backend import BackendTraits, ChatBackend
from workbench.chat_backend_store import DEFAULT_BACKEND, ChatBackendStore
from workbench.chat_event import ChatEvent
from workbench.handoff_builder import HandoffBuilder


@dataclass(frozen=True)
class FlipResult:
    """Outcome of a flip request: ok, or the reason the flip was refused."""

    ok: bool
    reason: str


class ChatBackendResolver:
    """Resolve a chat name to its backend, and flip the stored key."""

    def __init__(self, backends: Mapping[str, ChatBackend],
                 store: ChatBackendStore, builder: HandoffBuilder) -> None:
        self._backends = backends
        self._store = store
        self._builder = builder

    def backend_of(self, name: str) -> ChatBackend:
        """The backend of the stored key; an unknown key uses the default."""
        backend = self._backends.get(self._store.load(name))
        if backend is None:
            return self._backends[DEFAULT_BACKEND]
        return backend

    async def submit(self, name: str, text: str) -> None:
        await self.backend_of(name).submit(name, text)

    async def forget(self, name: str) -> None:
        """Retire the chat on every backend; old ones may hold state."""
        for backend in self._backends.values():
            await backend.retire(name)

    def is_running(self, name: str) -> bool:
        return any(backend.is_running(name) for backend in self._backends.values())

    async def flip(self, name: str, key: str) -> FlipResult:
        """Store a new backend key, refusing while a turn runs, and hand the
        conversation just left to the next turn of the new backend."""
        if self.is_running(name):
            return FlipResult(ok=False, reason="A turn is running. Stop it first.")
        if key not in self._backends:
            return FlipResult(ok=False, reason="Unknown backend.")
        leaving = self.backend_of(name)
        arriving = self._backends[key]
        if arriving is not leaving:
            block = await self._handoff_block(name, leaving)
            arriving.receive_handoff(name, block)
        self._store.save(name, key)
        return FlipResult(ok=True, reason="")

    async def _handoff_block(self, name: str, leaving: ChatBackend) -> str:
        events = await self._history_of(name, leaving)
        return self._builder.build(name, leaving.traits.label, events)

    async def _history_of(self, name: str, backend: ChatBackend) -> tuple[ChatEvent, ...]:
        try:
            return await backend.history(name)
        except Exception:
            return ()

    def all_traits(self) -> tuple[BackendTraits, ...]:
        return tuple(backend.traits for backend in self._backends.values())
