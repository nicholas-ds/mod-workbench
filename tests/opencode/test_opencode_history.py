"""Tests for OpencodeHistoryLoader: order, idle drop, empty store, down client."""

from __future__ import annotations

from pathlib import Path

from workbench.chat.chat_event import KIND_RESULT, KIND_TEXT, KIND_USER, ChatEvent
from workbench.opencode.opencode_history import OpencodeHistoryLoader
from workbench.chat.session_id_store import SessionIdStore

TOKENS_A = {"input": 10, "output": 20}
TOKENS_B = {"input": 30, "output": 40}


def user_msg(text: str) -> dict:
    return {"id": f"usr_{text}", "type": "user", "text": text}


def assistant_msg(text: str, tokens: dict | None = None) -> dict:
    message: dict = {"id": f"msg_{text}", "type": "assistant",
                     "content": [{"type": "text", "text": text}]}
    if tokens is not None:
        message["tokens"] = tokens
    return message


def idle_msg() -> dict:
    return {"id": "idle", "type": "idle", "outcome": "succeeded"}


class FakeClient:
    """Canned newest-first messages; raises OSError when down."""

    def __init__(self, messages: list[dict] | None = None,
                 down: bool = False) -> None:
        self._messages = messages if messages is not None else []
        self._down = down
        self.closed = False

    async def connect(self) -> None:
        if self._down:
            raise OSError("server down")

    async def close(self) -> None:
        self.closed = True

    async def messages(self, session_id: str) -> list[dict]:
        if self._down:
            raise OSError("server down")
        return self._messages


class FakeFactory:
    """Hands out one canned client; records creations."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client
        self.calls = 0

    def __call__(self) -> FakeClient:
        self.calls += 1
        return self._client


def make_loader(
    tmp_path: Path, client: FakeClient,
) -> tuple[OpencodeHistoryLoader, SessionIdStore, FakeFactory]:
    store = SessionIdStore(tmp_path / "ids.json")
    store.save("main", "ses_1")
    factory = FakeFactory(client)
    loader = OpencodeHistoryLoader(store, None, factory)  # type: ignore[arg-type]
    return loader, store, factory


async def test_reverses_order_drops_trailing_idle_and_translates(tmp_path: Path) -> None:
    messages = [  # newest first, as GET /session/{id}/message returns
        idle_msg(), assistant_msg("second", TOKENS_B), idle_msg(),
        assistant_msg("first", TOKENS_A), user_msg("hi"),
    ]
    loader, _, _ = make_loader(tmp_path, FakeClient(messages))
    events = await loader.load("main")
    assert events == (
        ChatEvent(kind=KIND_USER, text="hi"),
        ChatEvent(kind=KIND_TEXT, text="first"),
        # the idle of turn one keeps its nearest assistant's token counts
        ChatEvent(kind=KIND_RESULT, text="succeeded", detail="in 10 / out 20"),
        ChatEvent(kind=KIND_TEXT, text="second"),
        # the trailing idle marker is dropped: no result event here
    )


async def test_empty_store_yields_no_history_and_no_client(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "ids.json")
    factory = FakeFactory(FakeClient())
    loader = OpencodeHistoryLoader(store, None, factory)  # type: ignore[arg-type]
    assert await loader.load("main") == ()
    assert factory.calls == 0


async def test_down_client_yields_no_history(tmp_path: Path) -> None:
    loader, _, factory = make_loader(tmp_path, FakeClient(down=True))
    assert await loader.load("main") == ()
    assert factory.calls == 1


def test_session_id_reads_the_store(tmp_path: Path) -> None:
    loader, store, _ = make_loader(tmp_path, FakeClient())
    assert loader.session_id("main") == "ses_1"
    assert loader.session_id("other") == ""
    store.save("other", "ses_2")
    assert loader.session_id("other") == "ses_2"
