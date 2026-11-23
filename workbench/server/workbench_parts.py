"""Compose the default workbench parts."""

from __future__ import annotations

from pathlib import Path

from workbench.boards.answer_store import AnswerStore
from workbench.boards.board_builder import BoardBuilder
from workbench.boards.board_lifecycle import BoardLifecycle
from workbench.boards.board_repository import BoardRepository
from workbench.boards.front_matter import FrontMatterParser
from workbench.boards.item_files import ItemKindDetector, SafeItemResolver
from workbench.boards.note_writer import NoteWriter
from workbench.boards.queue import QueueSorter
from workbench.boards.rework import LogAppender, ReworkBriefWriter
from workbench.core.config import ModConfigLoader, ModDiscovery
from workbench.core.tables import TableBuilder
from workbench.core.watch import FileChangeWatcher
from workbench.mods.mod_registry import ModRegistry
from workbench.mods.status import StatusReader, WorkerExtractor
from workbench.panes.pane_sender import PaneSender
from workbench.web.api import ApiFactory


class WorkbenchParts:
    """Compose the default workbench parts."""

    def __init__(self, pane_sender: PaneSender) -> None:
        self.repository = BoardRepository(FrontMatterParser(), BoardBuilder())
        self.answers = AnswerStore()
        self.factory = ApiFactory(
            discovery=ModDiscovery(ModConfigLoader()),
            boards=self.repository,
            answers=self.answers,
            lifecycle=BoardLifecycle(),
            sorter=QueueSorter(),
            table_builder=TableBuilder(),
            rework_writer=ReworkBriefWriter(LogAppender()),
            note_writer=NoteWriter(),
            status_reader=StatusReader(),
            worker_extractor=WorkerExtractor(),
            resolver=SafeItemResolver(),
            kinds=ItemKindDetector(),
            watcher=FileChangeWatcher(),
            pane_sender=pane_sender,
        )

    def registry(self, roots: list[Path]) -> ModRegistry:
        return ModRegistry(ModDiscovery(ModConfigLoader()), roots,
                           self.repository, self.answers)
