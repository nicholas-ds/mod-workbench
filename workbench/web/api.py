"""HTTP API of the workbench: assemble the FastAPI app from the parts."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from workbench.agents.agent_registry import AgentRegistry
from workbench.agents.agent_store import AgentStore
from workbench.boards.answer_store import AnswerStore
from workbench.boards.board_lifecycle import BoardLifecycle
from workbench.boards.board_repository import BoardRepository
from workbench.core.config import ModDiscovery
from workbench.agents.claude_translator import ClaudeEventTranslator
from workbench.web.chat_assembly import ChatAssembly
from workbench.notices.delivery_view import DeliveryViewBuilder
from workbench.notices.owner_inbox import OwnerInbox
from workbench.server.all_mods_retry_job import AllModsRetryJob
from workbench.server.chat_shutdown_job import ChatShutdownJob
from workbench.web.routes_notices import NoticesRoutes
from workbench.chat.chat_command import SlashCommandParser
from workbench.panes.chat_turn_sink import RunnerChatTurnSink
from workbench.chat.chat_upload_saver import ChatUploadSaver
from workbench.handoff.handoff_nudger import HandoffMessageComposer, HandoffNudger
from workbench.handoff.handoff_scanner import BoardTextReader, HandoffScanner, OpenRequestReader, TrackingTextReader, UnpickedFileFinder
from workbench.versions.installed_version_reader import InstalledVersionReader, run_process
from workbench.boards.item_files import ItemKindDetector, SafeItemResolver
from workbench.web.item_style import HtmlItemStyler
from workbench.versions.latest_version_fetcher import LatestVersionFetcher, fetch_json
from workbench.panes.message_writer import MessageWriter
from workbench.mods.mod_detail import ModDetailReader
from workbench.mods.mod_registry import ModRegistry
from workbench.web.local_request_guard import LocalRequestGuard
from workbench.web.no_cache_headers import NoCacheHeaders
from workbench.boards.note_writer import NoteWriter
from workbench.agents.opencode_translator import OpencodeEventTranslator
from workbench.chat.orchestrator_directory import OrchestratorDirectory
from workbench.mods.pane_directory import PaneDirectory
from workbench.notices.board_notice_sender import BoardNoticeSender
from workbench.notices.notice_dispatcher_factory import NoticeDispatcherFactory
from workbench.panes.pane_registry import PaneRegistry
from workbench.panes.pane_sender import PaneSender
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.permission_card_builder import PermissionCardBuilder
from workbench.boards.queue import QueueSorter
from workbench.boards.rework import ReworkBriefWriter
from workbench.web.routes_agents import AgentRoutes
from workbench.web.routes_boards import BoardsRoutes
from workbench.web.routes_chat import ChatRoutes
from workbench.web.routes_threads import ThreadRoutes
from workbench.web.routes_wake import WakeRoutes
from workbench.web.routes_handoff import HandoffRoutes
from workbench.chat.wake_broadcaster import WakeBroadcaster
from workbench.web.routes_detail import DetailRoutes
from workbench.web.routes_events import EventsRoutes
from workbench.web.routes_items import ItemsRoutes
from workbench.web.routes_messages import MessagesRoutes
from workbench.web.routes_mods import ModsRoutes
from workbench.web.routes_overview import OverviewRoutes
from workbench.web.routes_upload import UploadRoutes
from workbench.web.routes_versions import VersionRoutes
from workbench.mods.status import StatusReader, WorkerExtractor
from workbench.core.tables import TableBuilder
from workbench.mods.task_overview import TaskOverviewReader
from workbench.versions.version_cache import VersionCache
from workbench.versions.version_checker import VersionChecker
from workbench.versions.version_comparer import VersionComparer
from workbench.core.watch import FileChangeWatcher
from workbench.agents.worker_scanner import BusyWorkerCounter, OpencodePortFinder, OpencodeSessionClient


def _workbench_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _web_dir() -> Path:
    return _workbench_root() / "web"


def _orchestrator_pane_file() -> Path:
    return _workbench_root() / "status" / "main-orchestrator.toml"


def _agents_file() -> Path:
    return _workbench_root() / "status" / "agents.json"


def _clock_ms() -> int:
    return int(time.time() * 1000)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex


class ApiFactory:
    """Assemble the FastAPI app from the workbench parts."""

    def __init__(self, discovery: ModDiscovery, boards: BoardRepository, answers: AnswerStore,
                 lifecycle: BoardLifecycle, sorter: QueueSorter, table_builder: TableBuilder,
                 rework_writer: ReworkBriefWriter, note_writer: NoteWriter,
                 status_reader: StatusReader, worker_extractor: WorkerExtractor,
                 resolver: SafeItemResolver, kinds: ItemKindDetector,
                 watcher: FileChangeWatcher) -> None:
        self._discovery, self._boards, self._answers = discovery, boards, answers
        self._lifecycle, self._sorter = lifecycle, sorter
        self._table_builder, self._rework_writer = table_builder, rework_writer
        self._note_writer, self._status_reader = note_writer, status_reader
        self._worker_extractor, self._resolver = worker_extractor, resolver
        self._kinds, self._watcher = kinds, watcher

    def create_app(self, roots: list[Path]) -> FastAPI:
        registry = ModRegistry(self._discovery, roots, self._boards, self._answers)
        app = FastAPI(title="mod-workbench")
        for router in self._routers(app, registry, roots):
            app.include_router(router)
        app.add_middleware(NoCacheHeaders)
        app.add_middleware(LocalRequestGuard)
        self._mount_web(app)
        return app

    def _routers(self, app: FastAPI, registry: ModRegistry,
                 roots: list[Path]) -> list[APIRouter]:
        directory = OrchestratorDirectory(registry, roots[0])
        pane_directory = PaneDirectory(registry, _workbench_root())
        permissions = PendingPermissionStore()
        cards = PermissionCardBuilder()
        stack = ChatAssembly().build(
            directory, roots[0], _workbench_root() / "status", permissions, cards)
        sink = RunnerChatTurnSink(stack.resolver, directory)
        factory = NoticeDispatcherFactory(pane_directory, PaneSender(), sink,
                                          stack.threads, stack.resolver,
                                          _utc_now, _new_id)
        app.state.background_jobs = [
            ChatShutdownJob(stack.resolver),
            AllModsRetryJob(registry, factory, asyncio.sleep),
        ]
        scanner = HandoffScanner(registry, "StarfieldModResearch", OpenRequestReader(),
                                 UnpickedFileFinder(), BoardTextReader(), TrackingTextReader())
        groups = [
            ModsRoutes(registry, self._status_reader, self._worker_extractor,
                       BusyWorkerCounter(OpencodePortFinder(), OpencodeSessionClient())),
            BoardsRoutes(registry, self._sorter, self._table_builder, self._answers,
                         self._lifecycle, self._rework_writer, self._note_writer,
                         self._kinds, notifier=BoardNoticeSender(factory)),
            ItemsRoutes(registry, self._resolver, self._kinds, HtmlItemStyler(_web_dir())),
            MessagesRoutes(registry, MessageWriter(),
                           pane_registry=PaneRegistry(_orchestrator_pane_file()),
                           pane_sender=PaneSender(),
                           workbench_root=_workbench_root(),
                           pane_directory=pane_directory),
            NoticesRoutes(registry, lambda cfg: OwnerInbox.of_mod(cfg.repo),
                          factory.build, DeliveryViewBuilder()),
            DetailRoutes(registry, ModDetailReader()),
            OverviewRoutes(registry, TaskOverviewReader(), roots[0] / "tracking.md"),
            EventsRoutes(self._watcher, registry),
            AgentRoutes(AgentRegistry(AgentStore(_agents_file())),
                        ClaudeEventTranslator(), OpencodeEventTranslator(),
                        clock_ms=_clock_ms,
                        chat_session_ids=stack.claude_session_ids.known_ids),
            ChatRoutes(stack.resolver, SlashCommandParser(), directory,
                       permissions, threads=stack.threads),
            ThreadRoutes(directory, stack.threads, stack.resolver),
            WakeRoutes(WakeBroadcaster(directory, stack.resolver)),
            HandoffRoutes(scanner, HandoffNudger(scanner, HandoffMessageComposer(), stack.resolver)),
            UploadRoutes(directory, ChatUploadSaver()),
            VersionRoutes(
                VersionChecker(
                    InstalledVersionReader(run_process),
                    LatestVersionFetcher(fetch_json),
                    VersionComparer(),
                ),
                VersionCache(_workbench_root() / "status" / "versions.json", 6 * 3600, time.time),
            ),
        ]
        return [group.routes for group in groups]

    def _mount_web(self, app: FastAPI) -> None:
        web_dir = _web_dir()
        if web_dir.is_dir():
            app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
