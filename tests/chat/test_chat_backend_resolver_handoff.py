"""A flip hands the conversation just left to the next turn of the new backend."""

from pathlib import Path

from test_chat_backend_resolver import FakeBackend
from workbench.chat.chat_backend_resolver import ChatBackendResolver
from workbench.chat.chat_backend_store import ChatBackendStore
from workbench.chat.chat_event import KIND_TEXT, ChatEvent


class RecordingBuilder:
    def __init__(self, block: str) -> None:
        self.block = block
        self.calls: list[tuple[str, str, int]] = []

    def build(self, name: str, from_label: str, events: tuple[ChatEvent, ...]) -> str:
        self.calls.append((name, from_label, len(events)))
        return self.block


def make(tmp_path: Path, block: str):
    claude = FakeBackend("claude")
    claude.history_events = (ChatEvent(kind=KIND_TEXT, text="we fixed the dock"),)
    opencode = FakeBackend("opencode")
    builder = RecordingBuilder(block)
    store = ChatBackendStore(tmp_path / "chat_backends.json")
    resolver = ChatBackendResolver({"claude": claude, "opencode": opencode}, store, builder)
    return resolver, claude, opencode, builder


async def test_flip_gives_the_arriving_backend_the_block(tmp_path: Path) -> None:
    resolver, _claude, opencode, builder = make(tmp_path, "[handoff] x [/handoff]")
    assert (await resolver.flip("coder", "opencode")).ok
    assert builder.calls == [("coder", "Claude", 1)]
    assert opencode._inbox.take("coder") == "[handoff] x [/handoff]"


async def test_flip_to_the_same_backend_hands_nothing(tmp_path: Path) -> None:
    resolver, claude, _opencode, builder = make(tmp_path, "block")
    assert (await resolver.flip("coder", "claude")).ok
    assert builder.calls == []
    assert claude._inbox.take("coder") == ""


async def test_flip_still_works_when_history_fails(tmp_path: Path) -> None:
    resolver, claude, opencode, _builder = make(tmp_path, "")

    async def broken(name: str):
        raise OSError("no session")

    claude.history = broken
    assert (await resolver.flip("coder", "opencode")).ok
    assert opencode._inbox.take("coder") == ""
