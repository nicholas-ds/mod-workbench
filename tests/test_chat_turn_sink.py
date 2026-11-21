"""Tests: RunnerChatTurnSink hands a text to the chat runner."""

import anyio
import anyio.to_thread

from workbench.chat_turn_sink import RunnerChatTurnSink


class RecordingSubmitter:
    """Fake TurnSubmitter that records the turns it is asked to submit."""

    def __init__(self) -> None:
        self.submitted: list[tuple[str, str]] = []

    async def submit(self, name: str, text: str) -> None:
        self.submitted.append((name, text))


class FakeFolders:
    """Fake FolderLookup backed by a fixed name-to-folder map."""

    def __init__(self, folders: dict[str, str]) -> None:
        self._folders = folders

    def folder_of(self, name: str) -> str:
        return self._folders.get(name, "")


def test_send_submits_the_text_from_a_worker_thread() -> None:
    runner = RecordingSubmitter()
    sink = RunnerChatTurnSink(runner, FakeFolders({"main": "E:/x"}))

    async def scenario() -> bool:
        return await anyio.to_thread.run_sync(sink.send, "main", "hello")

    assert anyio.run(scenario) is True
    assert runner.submitted == [("main", "hello")]


def test_send_with_unknown_chat_is_false_and_submits_nothing() -> None:
    runner = RecordingSubmitter()
    sink = RunnerChatTurnSink(runner, FakeFolders({"main": "E:/x"}))

    assert sink.send("ghost", "hello") is False
    assert runner.submitted == []
