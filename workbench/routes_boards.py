"""Board routes of one mod: list, detail, answers, lifecycle and notes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from workbench.answer_store import AnswerStore
from workbench.board_lifecycle import BoardLifecycle
from workbench.board_notifier import (ANSWERS_EVENT, CLOSED_EVENT, REOPENED_EVENT,
                                      BoardNotifier, NoteNotice)
from workbench.board_records import BoardRecords
from workbench.board_repository import DONE_STATE, OPEN_STATE
from workbench.board_types import Answer, Board, BoardEntry, BoardError
from workbench.config import ModConfig
from workbench.item_files import ItemKindDetector
from workbench.mod_registry import ModRegistry
from workbench.note_writer import NoteWriter
from workbench.queue import BlockingRule, QueueSorter
from workbench.rework import ReworkBriefWriter
from workbench.tables import TableBuilder


class AnswerPost(BaseModel):
    """Body of one answers post."""

    model_config = ConfigDict(frozen=True)

    question_id: str
    picked: str | None = None
    text: str | None = None
    comment: str | None = None


class NotePost(BaseModel):
    """Body of one notes post."""

    model_config = ConfigDict(frozen=True)

    item: str
    x: float
    y: float
    text: str


class BoardsRoutes:
    """Board routes of one mod: list, detail, answers, lifecycle and notes."""

    def __init__(self, registry: ModRegistry, sorter: QueueSorter,
                 table_builder: TableBuilder, answers: AnswerStore,
                 lifecycle: BoardLifecycle, rework_writer: ReworkBriefWriter,
                 note_writer: NoteWriter, kinds: ItemKindDetector,
                 blocking: BlockingRule | None = None,
                 notifier: BoardNotifier | None = None) -> None:
        self._registry, self._answers, self._lifecycle = registry, answers, lifecycle
        self._rework_writer, self._note_writer = rework_writer, note_writer
        self._notifier = notifier
        self._records = BoardRecords(registry, sorter, table_builder, kinds, blocking)
        self.routes = APIRouter()
        self.routes.add_api_route("/api/mods/{name}/boards", self.boards, methods=["GET"])
        self.routes.add_api_route("/api/mods/{name}/boards/{board_id}", self.board,
                                  methods=["GET"])
        self.routes.add_api_route("/api/mods/{name}/boards/{board_id}/answers", self.answer,
                                  methods=["POST"])
        self.routes.add_api_route("/api/mods/{name}/boards/{board_id}/send", self.send,
                                  methods=["POST"])
        self.routes.add_api_route("/api/mods/{name}/boards/{board_id}/close", self.close,
                                  methods=["POST"])
        self.routes.add_api_route("/api/mods/{name}/boards/{board_id}/reopen", self.reopen,
                                  methods=["POST"])
        self.routes.add_api_route("/api/mods/{name}/boards/{board_id}/notes", self.note,
                                  methods=["POST"])

    def boards(self, name: str, state: str = OPEN_STATE) -> dict[str, object]:
        return self._records.listed(self._registry.require(name), state)

    def board(self, name: str, board_id: str) -> dict[str, object]:
        cfg = self._registry.require(name)
        entry = self._registry.require_entry(cfg, board_id)
        return self._records.board(name, entry, self._state(entry))

    def answer(self, name: str, board_id: str, body: AnswerPost) -> dict[str, object]:
        cfg = self._registry.require(name)
        entry = self._in_state(cfg, board_id, OPEN_STATE, "answer a done board")
        self._reject_unknown(entry.board, body)
        return self._records.answer(self._save(entry.board.folder, body))

    def send(self, name: str, board_id: str) -> dict[str, object]:
        cfg = self._registry.require(name)
        entry = self._in_state(cfg, board_id, OPEN_STATE, "send a done board")
        return {"id": entry.board.id, "notified": self._notified(cfg, entry, ANSWERS_EVENT)}

    def close(self, name: str, board_id: str) -> dict[str, object]:
        cfg = self._registry.require(name)
        entry = self._in_state(cfg, board_id, OPEN_STATE, "close a done board")
        closed = self._moved(self._lifecycle.close, entry.board)
        notified = self._notified(cfg, entry, CLOSED_EVENT)
        return {"id": closed.id, "state": DONE_STATE, "notified": notified}

    def reopen(self, name: str, board_id: str) -> dict[str, object]:
        cfg = self._registry.require(name)
        entry = self._in_state(cfg, board_id, DONE_STATE, "reopen an open board")
        reopened = self._moved(self._lifecycle.reopen, entry.board)
        self._rework_writer.write(cfg, entry)
        notified = self._notified(cfg, entry, REOPENED_EVENT)
        return {"id": reopened.id, "state": OPEN_STATE, "notified": notified}

    def note(self, name: str, board_id: str, body: NotePost) -> dict[str, object]:
        cfg = self._registry.require(name)
        entry = self._registry.require_entry(cfg, board_id)
        now = datetime.now(UTC).isoformat(timespec="seconds")
        path = self._note_writer.write(cfg, entry.board, body.item, body.x, body.y,
                                       body.text, now)
        notice = NoteNotice(item=body.item, x=body.x, y=body.y, text=body.text, path=path)
        return {"file": path.name, "notified": self._note_notified(cfg, entry, notice)}

    def _note_notified(self, cfg: ModConfig, entry: BoardEntry, notice: NoteNotice) -> bool:
        if self._notifier is None:
            return False
        return self._notifier.notify_note(cfg, entry, notice)

    def _in_state(self, cfg: ModConfig, board_id: str, wanted: str,
                  conflict: str) -> BoardEntry:
        entry = self._registry.require_entry(cfg, board_id)
        state = self._state(entry)
        if state != wanted:
            raise HTTPException(status_code=409, detail=f"board is {state}: {conflict}")
        return entry

    def _notified(self, cfg: ModConfig, entry: BoardEntry, event: str) -> bool:
        if self._notifier is None:
            return False
        return self._notifier.notify(cfg, entry, event)

    @staticmethod
    def _state(entry: BoardEntry) -> str:
        return entry.board.folder.parent.name

    def _reject_unknown(self, board: Board, body: AnswerPost) -> None:
        question = next((q for q in board.questions if q.id == body.question_id), None)
        if question is None:
            raise HTTPException(status_code=400, detail=f"unknown question: {body.question_id}")
        known = {option.id for option in question.options}
        if question.type == "choice" and body.picked is not None and body.picked not in known:
            raise HTTPException(status_code=400, detail=f"unknown option: {body.picked}")

    def _save(self, folder: Path, body: AnswerPost) -> Answer:
        answer = Answer(question_id=body.question_id, picked=body.picked, text=body.text,
                        comment=body.comment,
                        answered_at=datetime.now(UTC).isoformat(timespec="seconds"))
        try:
            self._answers.write(folder, answer)
        except BoardError as exc:
            raise HTTPException(status_code=409, detail=exc.reason) from exc
        return answer

    def _moved(self, move: Callable[[Board], Board], board: Board) -> Board:
        try:
            return move(board)
        except BoardError as exc:
            raise HTTPException(status_code=409, detail=exc.reason) from exc
