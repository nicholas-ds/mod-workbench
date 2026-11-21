"""HTTP API of the workbench: assemble the FastAPI app from the parts."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from workbench.agent_registry import AgentRegistry
from workbench.agent_store import AgentStore
from workbench.answer_store import AnswerStore
from workbench.board_lifecycle import BoardLifecycle
from workbench.board_notifier import BoardNotifier
from workbench.board_repository import BoardRepository
from workbench.config import ModDiscovery
from workbench.claude_translator import ClaudeEventTranslator
from workbench.chat_assembly import ChatAssembly
from workbench.chat_command import SlashCommandParser
from workbench.chat_turn_sink import RunnerChatTurnSink
from workbench.chat_upload_saver import ChatUploadSaver
from workbench.handoff_nudger import HandoffMessageComposer, HandoffNudger
from workbench.handoff_scanner import BoardTextReader, HandoffScanner, OpenRequestReader, TrackingTextReader, UnpickedFileFinder
from workbench.installed_version_reader import InstalledVersionReader, run_process
from workbench.item_files import ItemKindDetector, SafeItemResolver
from workbench.item_style import HtmlItemStyler
from workbench.latest_version_fetcher import LatestVersionFetcher, fetch_json
from workbench.message_writer import MessageWriter
from workbench.mod_detail import ModDetailReader
from workbench.mod_registry import ModRegistry
from workbench.local_request_guard import LocalRequestGuard
from workbench.no_cache_headers import NoCacheHeaders
from workbench.note_writer import NoteWriter
from workbench.opencode_translator import OpencodeEventTranslator
from workbench.orchestrator_directory import OrchestratorDirectory
from workbench.pane_directory import PaneDirectory
from workbench.pane_registry import PaneRegistry
from workbench.pane_sender import PaneSender
from workbench.pending_permission_store import PendingPermissionStore
from workbench.permission_card_builder import PermissionCardBuilder
from workbench.queue import QueueSorter
from workbench.rework import ReworkBriefWriter
from workbench.routes_agents import AgentRoutes
from workbench.routes_boards import BoardsRoutes
from workbench.routes_chat import ChatRoutes
from workbench.routes_threads import ThreadRoutes
from workbench.routes_wake import WakeRoutes
from workbench.routes_handoff import HandoffRoutes
from workbench.wake_broadcaster import WakeBroadcaster
from workbench.routes_detail import DetailRoutes
from workbench.routes_events import EventsRoutes
from workbench.routes_items import ItemsRoutes
from workbench.routes_messages import MessagesRoutes
from workbench.routes_mods import ModsRoutes
from workbench.routes_overview import OverviewRoutes
from workbench.routes_upload import UploadRoutes
from workbench.routes_versions import VersionRoutes
from workbench.status import StatusReader, WorkerExtractor
from workbench.tables import TableBuilder
from workbench.task_overview import TaskOverviewReader
from workbench.version_cache import VersionCache
from workbench.version_checker import VersionChecker
from workbench.version_comparer import VersionComparer
from workbench.watch import FileChangeWatcher
from workbench.worker_scanner import BusyWorkerCounter, OpencodePortFinder, OpencodeSessionClient


def _workbench_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _web_dir() -> Path:
    return _workbench_root() / "web"


def _orchestrator_pane_file() -> Path:
    return _workbench_root() / "status" / "main-orchestrator.toml"


def _agents_file() -> Path:
    return Path(__file__).resolve().parents[1] / "status" / "agents.json"


def _clock_ms() -> int:
    return int(time.time() * 1000)


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
        for router in self._routers(registry, roots):
            app.include_router(router)
        app.add_middleware(NoCacheHeaders)
        app.add_middleware(LocalRequestGuard)
        self._mount_web(app)
        return app

    def _routers(self, registry: ModRegistry, roots: list[Path]) -> list[APIRouter]:
        directory = OrchestratorDirectory(registry, roots[0])
        permissions = PendingPermissionStore()
        cards = PermissionCardBuilder()
        stack = ChatAssembly().build(
            directory, roots[0], _workbench_root() / "status", permissions, cards)
        sink = RunnerChatTurnSink(stack.resolver, directory)
        scanner = HandoffScanner(registry, "StarfieldModResearch", OpenRequestReader(),
                                 UnpickedFileFinder(), BoardTextReader(), TrackingTextReader())
        groups = [
            ModsRoutes(registry, self._status_reader, self._worker_extractor,
                       BusyWorkerCounter(OpencodePortFinder(), OpencodeSessionClient())),
            BoardsRoutes(registry, self._sorter, self._table_builder, self._answers,
                         self._lifecycle, self._rework_writer, self._note_writer,
                         self._kinds, notifier=BoardNotifier(PaneSender(),
                                                             chat_sink=sink)),
            ItemsRoutes(registry, self._resolver, self._kinds, HtmlItemStyler(_web_dir())),
            MessagesRoutes(registry, MessageWriter(),
                           pane_registry=PaneRegistry(_orchestrator_pane_file()),
                           pane_sender=PaneSender(),
                           workbench_root=_workbench_root(),
                           pane_directory=PaneDirectory(registry, _workbench_root())),
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
