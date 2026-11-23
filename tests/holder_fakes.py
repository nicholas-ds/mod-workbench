"""Fakes and builders for the ClaudeSessionHolder tests."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from claude_agent_sdk import ResultMessage

from runner_fakes import make_assistant, make_result

from workbench.chat_event import ChatEvent, KIND_RESULT, KIND_TEXT
from workbench.chat_job import KIND_CLAUDE_AGENT, STATE_RUNNING, ChatJob
from workbench.chat_job_book import ChatJobBook
from workbench.chat_job_store import ChatJobStore
from workbench.claude_sdk_translator import ClaudeSdkTranslator
from workbench.claude_session_holder import ClaudeSessionHolder
from workbench.cli_pid_file import CliPidFile
from workbench.session_id_store import SessionIdStore
from workbench.turn_book import TurnBook
from workbench.turn_event_log import TurnEventLog

NAME = "coder"
IDLE = 0.01
PID = 4242


class FakeChatClient:
    """Fake client with a queue-fed stream and the pid chain of a real CLI."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._messages: asyncio.Queue[object] = asyncio.Queue()
        self._transport = SimpleNamespace(_process=SimpleNamespace(pid=PID))

    async def connect(self) -> None:
        self.calls.append("connect")

    async def query(self, prompt: str) -> None:
        self.calls.append(f"query:{prompt}")

    async def disconnect(self) -> None:
        self.calls.append("disconnect")

    async def receive_messages(self):
        while True:
            message = await self._messages.get()
            if message is None:
                return
            yield message

    def feed(self, message: object) -> None:
        self._messages.put_nowait(message)

    def end_stream(self) -> None:
        self._messages.put_nowait(None)


class FakeClientFactory:
    """Record requested sessions and hand out one fake client per call."""

    def __init__(self) -> None:
        self.requested: list[tuple[str, str]] = []
        self.clients: list[FakeChatClient] = []

    def __call__(self, name: str, resume: str, can_use_tool: object) -> FakeChatClient:
        self.requested.append((name, resume))
        client = FakeChatClient()
        self.clients.append(client)
        return client


class ResultRecorder:
    """Stand-in for the on_result hook of the backend."""

    def __init__(self) -> None:
        self.results: list[tuple[str, ResultMessage]] = []

    async def __call__(self, name: str, message: ResultMessage) -> None:
        self.results.append((name, message))


async def unused_permission(tool: object, context: object) -> None:
    """Stand-in for a CanUseTool callback; the holder never calls it."""


def make_holder(
    tmp_path: Path, idle_seconds: float = IDLE
) -> tuple[ClaudeSessionHolder, FakeClientFactory, ResultRecorder, ChatJobStore, TurnBook]:
    factory = FakeClientFactory()
    recorder = ResultRecorder()
    job_store = ChatJobStore(tmp_path / "jobs")
    book = TurnBook()
    holder = ClaudeSessionHolder(
        client_factory=factory,
        session_store=SessionIdStore(None),
        translator=ClaudeSdkTranslator(),
        book=book,
        job_book=ChatJobBook(),
        job_store=job_store,
        pid_file=CliPidFile(tmp_path / "pids"),
        on_result=recorder,
        idle_seconds=idle_seconds,
    )
    return holder, factory, recorder, job_store, book


def begin_turn(book: TurnBook, name: str) -> TurnEventLog:
    """Open a turn so book.offer has a log to append to, as the backend does."""
    log = TurnEventLog()
    pump = asyncio.create_task(asyncio.sleep(0))
    book.begin(name, log, pump)
    return log


def running_job() -> tuple[ChatJob, ...]:
    return (
        ChatJob(
            job_id="j1",
            kind=KIND_CLAUDE_AGENT,
            chat=NAME,
            started_by="test",
            state=STATE_RUNNING,
            result="",
            started_ms=1,
            updated_ms=1,
        ),
    )


async def wait_for(predicate: Callable[[], bool], timeout: float = 2.0) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.005)
    return predicate()
