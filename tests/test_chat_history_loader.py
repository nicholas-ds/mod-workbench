"""Tests for ChatHistoryLoader: chat name to saved chat events, with fakes."""

from dataclasses import dataclass

from workbench.chat_event import ChatEvent
from workbench.chat_history_loader import ChatHistoryLoader
from workbench.session_history_reader import SessionHistoryReader


@dataclass(frozen=True)
class FakeMessage:
    """Stand-in for one saved SDK message."""

    text: str


class FakeStore:
    """Returns the canned session id for main, none for every other name."""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id

    def load(self, name: str) -> str:
        return self._session_id if name == "main" else ""


class FakeDirectory:
    """Maps main to a folder, every other name to none."""

    def folder_of(self, name: str) -> str:
        return "E:/m" if name == "main" else ""


class RecordingFetch:
    """Canned SDK messages; records fetch calls."""

    def __init__(self, messages: tuple[object, ...]) -> None:
        self._messages = messages
        self.calls: list[tuple[str, str]] = []

    def __call__(self, session_id: str, folder: str) -> tuple[object, ...]:
        self.calls.append((session_id, folder))
        return self._messages


class RecordingTranslator:
    """No events for no messages, one canned event otherwise; records input."""

    def __init__(self) -> None:
        self.received: tuple[object, ...] | None = None

    def translate(self, messages: tuple[object, ...]) -> tuple[ChatEvent, ...]:
        self.received = messages
        if messages == ():
            return ()
        return (ChatEvent(kind="text", text="hello"),)


def make_loader(
    session_id: str,
) -> tuple[ChatHistoryLoader, RecordingFetch, RecordingTranslator]:
    fetch = RecordingFetch((FakeMessage(text="hi"),))
    translator = RecordingTranslator()
    loader = ChatHistoryLoader(
        FakeStore(session_id),
        FakeDirectory(),
        SessionHistoryReader(fetch),
        translator,
    )
    return loader, fetch, translator


def test_empty_session_id_gives_no_events() -> None:
    loader, fetch, translator = make_loader("")
    assert loader.load("main") == ()
    assert fetch.calls == []
    assert translator.received == ()


def test_saved_session_id_passes_id_and_folder_to_the_reader() -> None:
    loader, fetch, translator = make_loader("ses-1")
    events = loader.load("main")
    assert fetch.calls == [("ses-1", "E:/m")]
    assert translator.received == (FakeMessage(text="hi"),)
    assert events == (ChatEvent(kind="text", text="hello"),)


def test_session_id_returns_stored_id_and_empty_for_unknown_name() -> None:
    loader, fetch, translator = make_loader("ses-1")
    assert loader.session_id("main") == "ses-1"
    assert loader.session_id("missing") == ""
    assert fetch.calls == []
    assert translator.received is None
