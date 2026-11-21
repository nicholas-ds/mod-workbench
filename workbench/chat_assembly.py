"""One builder for the whole chat stack (Task: WP6b).

ChatAssembly wires the parts api.py used to build inline: the Claude and
OpenCode backends, their session id stores, the history loaders, the
handoff callable, the thread registry, the backend store and the
resolver. build() runs once at app assembly; the OpenCode server is
started lazily by its client factory, never here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import get_session_messages

from workbench.alerts import PermissionWaitAlert, ToastNotifier, ToastSourceDetector
from workbench.chat_backend_resolver import ChatBackendResolver
from workbench.chat_backend_store import ChatBackendStore
from workbench.chat_history_loader import ChatHistoryLoader
from workbench.claude_chat_backend import ClaudeChatBackend
from workbench.claude_sdk_translator import ClaudeSdkTranslator
from workbench.handoff_composer import HandoffComposer
from workbench.handoff_builder import HandoffBuilder
from workbench.transcript_writer import TranscriptWriter
from workbench.opencode_chat_backend import OpencodeChatBackend
from workbench.opencode_chat_translator import OpencodeChatTranslator
from workbench.opencode_history import OpencodeHistoryLoader
from workbench.opencode_http_client import OpencodeHttpClient
from workbench.opencode_server_process import OpencodeServerProcess
from workbench.opencode_turn_follower import OpencodeTurnFollower
from workbench.orchestrator_directory import OrchestratorDirectory
from workbench.pending_permission_store import PendingPermissionStore
from workbench.permission_card_builder import PermissionCardBuilder
from workbench.sdk_client_factory import SdkClientFactory
from workbench.session_history_reader import SessionHistoryReader
from workbench.session_history_lister import SessionHistoryLister
from workbench.session_history_translator import SessionHistoryTranslator
from workbench.session_id_store import SessionIdStore
from workbench.slash_command_lister import SlashCommandLister
from workbench.thread_registry import ThreadRegistry
from workbench.turn_book import TurnBook


@dataclass(frozen=True)
class ChatStack:
    """The built chat parts: the resolver for every route, plus the
    thread registry and the Claude session ids the other routes need."""

    resolver: ChatBackendResolver
    threads: ThreadRegistry
    claude_session_ids: SessionIdStore


class ChatAssembly:
    """Build every chat part once and hand the stack to the app factory."""

    def build(self, directory: OrchestratorDirectory, work_root: Path,
              status_root: Path, permissions: PendingPermissionStore,
              cards: PermissionCardBuilder) -> ChatStack:
        session_ids = SessionIdStore(status_root / "session_ids.json")
        history_loader = self._claude_history(session_ids, directory)
        claude = self._claude_backend(
            session_ids, directory, history_loader, permissions, cards)
        opencode = self._opencode_backend(
            directory, work_root, status_root, permissions, cards)
        threads = ThreadRegistry(status_root / "chat_threads.json")
        store = ChatBackendStore(status_root / "chat_backends.json")
        builder = HandoffBuilder(
            HandoffComposer(), TranscriptWriter(status_root / "handoffs"))
        resolver = ChatBackendResolver(
            {"claude": claude, "opencode": opencode}, store, builder)
        return ChatStack(resolver=resolver, threads=threads,
                         claude_session_ids=session_ids)

    def _claude_history(self, session_ids: SessionIdStore,
                        directory: OrchestratorDirectory) -> ChatHistoryLoader:
        return ChatHistoryLoader(
            session_ids,
            directory,
            SessionHistoryReader(
                lambda session_id, folder:
                get_session_messages(session_id, directory=folder)),
            SessionHistoryTranslator(),
        )

    def _claude_backend(
        self, session_ids: SessionIdStore, directory: OrchestratorDirectory,
        history_loader: ChatHistoryLoader, permissions: PendingPermissionStore,
        cards: PermissionCardBuilder,
    ) -> ClaudeChatBackend:
        return ClaudeChatBackend(
            TurnBook(),
            SdkClientFactory(directory).create,
            session_ids,
            ClaudeSdkTranslator(),
            permissions,
            cards,
            history_loader,
            SlashCommandLister(),
            SessionHistoryLister(),
            on_permission_wait=PermissionWaitAlert(
                ToastNotifier(ToastSourceDetector().detect())).notify,
        )

    def _opencode_backend(
        self, directory: OrchestratorDirectory, work_root: Path,
        status_root: Path, permissions: PendingPermissionStore,
        cards: PermissionCardBuilder,
    ) -> OpencodeChatBackend:
        opencode_ids = SessionIdStore(status_root / "opencode_session_ids.json")
        opencode_server = OpencodeServerProcess(
            status_root / "opencode_server.json")

        def opencode_client() -> OpencodeHttpClient:
            # Lazily ensures the server: first GLM turn or history load,
            # never at app boot. The API lives under /api (session.ps1 calls
            # $Server/api/...); the client's paths start at /session.
            url, password = opencode_server.ensure(work_root)
            return OpencodeHttpClient(url.rstrip("/") + "/api", password)

        book = TurnBook()
        opencode_history = OpencodeHistoryLoader(
            opencode_ids, directory, opencode_client)
        follower = OpencodeTurnFollower(
            OpencodeChatTranslator(), permissions, cards, book)
        return OpencodeChatBackend(
            book,
            opencode_client,
            opencode_ids,
            permissions,
            directory,
            follower,
            opencode_history,
        )
