"""Send board event notices to the board owner through the notice pipeline."""

from __future__ import annotations

from workbench.boards.board_types import BoardEntry
from workbench.core.config import ModConfig
from workbench.notices.notice_dispatcher_factory import NoticeDispatcherFactory
from workbench.notices.notice_events import (ANSWERS_EVENT, CLOSED_EVENT,
                                             REOPENED_EVENT, NoteNotice)
from workbench.notices.notice_types import DeliveryState

NOTE_EVENT = "note"

ANSWERS_FILE = "answers.json"

GOOD_STATES = (DeliveryState.DELIVERED, DeliveryState.FRESH_STARTED)


class BoardNoticeSender:
    """Send board events to the board owner: the dispatcher decides the route."""

    def __init__(self, factory: NoticeDispatcherFactory) -> None:
        self._factory = factory

    def notify(self, cfg: ModConfig, entry: BoardEntry, event: str) -> bool:
        return self._send(cfg, entry, event, self._event_file(cfg, entry, event))

    def notify_note(self, cfg: ModConfig, entry: BoardEntry, notice: NoteNotice) -> bool:
        return self._send(cfg, entry, NOTE_EVENT, str(notice.path))

    def _send(self, cfg: ModConfig, entry: BoardEntry, event: str, file_path: str) -> bool:
        dispatcher = self._factory.build(cfg)
        record = dispatcher.dispatch(entry.board, event, file_path)
        return record.state in GOOD_STATES

    @staticmethod
    def _event_file(cfg: ModConfig, entry: BoardEntry, event: str) -> str:
        board = entry.board
        if event == REOPENED_EVENT:
            rework = cfg.briefs / f"rework-{board.id}.md"
            if rework.is_file():
                return str(rework)
            return str(board.folder / ANSWERS_FILE)
        if event == CLOSED_EVENT:
            return str(cfg.boards / "done" / board.id / ANSWERS_FILE)
        return str(board.folder / ANSWERS_FILE)
