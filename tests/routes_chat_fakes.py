"""Shared fakes and client builders for the chat route tests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.chat_backend import BackendTraits, ChatBackend, SessionView
from workbench.chat_backend_resolver import ChatBackendResolver
from workbench.chat_backend_store import ChatBackendStore
from workbench.chat_command import SlashCommandParser
from workbench.chat_event import ChatEvent
from workbench.orchestrator_directory import (
    OrchestratorDirectory,
    OrchestratorEntry,
)
from workbench.pending_permission_store import PendingPermissionStore
from workbench.routes_chat import ChatRoutes
from workbench.session_summary import SessionSummary
from workbench.slash_command_lister import SlashCommandInfo
from workbench.thread_registry import ThreadRegistry
from workbench.turn_book import TurnBook
from workbench.turn_event_log import TurnEventLog

STORE_FILE = "chat_backends.json"


class FakeBackend(ChatBackend):
    """Scripted backend for one key: canned events, recorded calls."""

    def __init__(self, key: str) -> None:
        super().__init__(TurnBook(), PendingPermissionStore())
        self.key = key
        self.turns: list[tuple[str, str]] = []
        self.stop_calls: list[str] = []
        self.follow_calls: list[str] = []
        self.retired: list[str] = []
        self.history_calls: list[str] = []
        self.commands_calls: list[str] = []
        self.session_calls: list[str] = []
        self.is_running_calls: list[str] = []
        self.sessions_calls: list[tuple[str, str]] = []
        self.resume_calls: list[tuple[str, str, str]] = []
        self.turn_events = (ChatEvent(kind="text", text=f"{key} hello"),
                            ChatEvent(kind="result", text="done"))
        self.follow_events: tuple[ChatEvent, ...] = ()
        self.history_events: tuple[ChatEvent, ...] = ()
        self.command_rows: tuple[SlashCommandInfo, ...] = (
            SlashCommandInfo(name="clear", description="Clear the chat"),)
        self.session_ids: dict[str, str] = {}
        self.context_percent: float | None = 42.5
        self.running_names: set[str] = set()
        self.session_rows: dict[str, tuple[SessionSummary, ...]] = {}
        self.resume_ok: set[str] = set()

    async def _turn(
        self, name: str, prompt: str, log: TurnEventLog, handoff: str
    ) -> None:
        self.turns.append((name, prompt))
        for event in self.turn_events:
            log.append(event)

    async def _interrupt(self, name: str) -> None:
        self.stop_calls.append(name)

    async def _forget(self, name: str) -> None:
        self.retired.append(name)

    def is_running(self, name: str) -> bool:
        self.is_running_calls.append(name)
        return super().is_running(name) or name in self.running_names

    async def follow(self, name: str) -> AsyncIterator[ChatEvent]:
        self.follow_calls.append(name)
        for event in self.follow_events:
            yield event

    async def session(self, name: str) -> SessionView:
        self.session_calls.append(name)
        session_id = self.session_ids.get(name, f"ses_{self.key}")
        return SessionView(session_id=session_id,
                           context_percent=self.context_percent)

    async def sessions(self, name: str,
                       folder: str) -> tuple[SessionSummary, ...]:
        self.sessions_calls.append((name, folder))
        return self.session_rows.get(name, ())

    async def resume_session(self, name: str, folder: str,
                             session_id: str) -> bool:
        self.resume_calls.append((name, folder, session_id))
        return session_id in self.resume_ok

    async def history(self, name: str) -> tuple[ChatEvent, ...]:
        self.history_calls.append(name)
        return self.history_events

    async def commands(self, name: str) -> tuple[SlashCommandInfo, ...]:
        self.commands_calls.append(name)
        return self.command_rows

    @property
    def traits(self) -> BackendTraits:
        return BackendTraits(
            key=self.key,
            label=self.key.capitalize(),
            tab_mark=self.key[:2],
            session_label=f"{self.key} session",
            resume_template=f"resume {self.key}",
            supports_resume=True,
            shows_context_percent=True,
            supports_slash_commands=True)


class FakeDirectory:
    """Two orchestrator entries: main and Logistics."""

    def __init__(self) -> None:
        self._entries = (
            OrchestratorEntry(name="main", folder="E:/m"),
            OrchestratorEntry(name="Logistics", folder="E:/l"),
        )

    def entries(self) -> tuple[OrchestratorEntry, ...]:
        return self._entries

    def folder_of(self, name: str) -> str:
        for entry in self._entries:
            if entry.name == name:
                return entry.folder
        return ""


class ThreadDirectory:
    """folder_of strips the thread suffix like the real directory."""

    def folder_of(self, name: str) -> str:
        return "E:/m"


class RecordingStore:
    """Records answer calls; returns a canned result."""

    def __init__(self, result: bool = True) -> None:
        self.calls: list[tuple[str, bool]] = []
        self._result = result

    def answer(self, request_id: str, allowed: bool) -> bool:
        self.calls.append((request_id, allowed))
        return self._result


class NoHandoff:
    def build(self, name: str, from_label: str, events: object) -> str:
        return ""


def make_resolver(tmp_path: Path,
                  ) -> tuple[ChatBackendResolver, dict[str, FakeBackend]]:
    """A real resolver over two fakes, backed by a tmp-path store."""
    fakes = {key: FakeBackend(key) for key in ("claude", "opencode")}
    store = ChatBackendStore(tmp_path / STORE_FILE)
    return ChatBackendResolver(fakes, store, NoHandoff()), fakes


def thread_registry(tmp_path: Path,
                    orchestrator: str = "Workbench") -> ThreadRegistry:
    """One fresh thread row for the orchestrator."""
    registry = ThreadRegistry(tmp_path / "threads.json")
    registry.add(orchestrator)
    return registry


def sse_events(body: str) -> list[dict[str, str]]:
    chunks = body.split("\n\n")
    return [json.loads(chunk.removeprefix("data: ")) for chunk in chunks if chunk]


def make_chat_client(
    tmp_path: Path,
    saved: dict[str, str] | None = None,
    permissions: PendingPermissionStore | RecordingStore | None = None,
    directory: OrchestratorDirectory | ThreadDirectory | None = None,
    threads: ThreadRegistry | None = None,
) -> tuple[TestClient, dict[str, FakeBackend], ChatBackendResolver]:
    """A ChatRoutes app over the shared fakes; flip saves entries first."""
    resolver, fakes = make_resolver(tmp_path)
    for name, key in (saved or {}).items():
        assert asyncio.run(resolver.flip(name, key)).ok
    routes = ChatRoutes(resolver, SlashCommandParser(),
                        directory or FakeDirectory(),
                        permissions or PendingPermissionStore(),
                        threads=threads)
    app = FastAPI()
    app.include_router(routes.routes)
    return TestClient(app), fakes, resolver


def make_app(permissions: PendingPermissionStore | RecordingStore,
             tmp_path: Path) -> TestClient:
    client, _, _ = make_chat_client(tmp_path, permissions=permissions)
    return client
