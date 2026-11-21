"""JSON records and table rows that the board routes return."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import HTTPException

from workbench.board_types import Answer, Board, BoardEntry, BoardError, BoardItem, Question
from workbench.config import ModConfig
from workbench.item_files import ItemKindDetector
from workbench.mod_registry import ModRegistry
from workbench.permanent_board import PermanentBoardRule
from workbench.queue import BlockingRule, QueueSorter
from workbench.tables import Table, TableBuilder


class BoardRecords:
    """Table rows and JSON records built from board entries."""

    def __init__(self, registry: ModRegistry, sorter: QueueSorter,
                 table_builder: TableBuilder, kinds: ItemKindDetector,
                 blocking: BlockingRule | None = None,
                 permanent: PermanentBoardRule | None = None) -> None:
        self._permanent = permanent if permanent is not None else PermanentBoardRule()
        self._registry, self._sorter, self._table_builder = registry, sorter, table_builder
        self._kinds = kinds
        self._blocking = blocking if blocking is not None else BlockingRule()

    def listed(self, cfg: ModConfig, state: str) -> dict[str, object]:
        return {"table": self._table(self._entries(cfg, state))}

    def board(self, name: str, entry: BoardEntry, state: str) -> dict[str, object]:
        board = entry.board
        return {"id": board.id, "title": board.title, "raised_by": board.raised_by,
                "created": board.created, "tags": list(board.tags), "state": state,
                "permanent": self._permanent.is_permanent(board),
                "stale": self._permanent.stale_note(board, time.time()),
                "body": board.body,
                "items": [self._item(name, board, item) for item in board.items],
                "questions": [self._question(q) for q in board.questions],
                "resolved": [vars(item) for item in board.resolved],
                "answers": [self.answer(answer) for answer in entry.answers]}

    def answer(self, answer: Answer) -> dict[str, object]:
        return {"question_id": answer.question_id, "picked": answer.picked,
                "text": answer.text, "comment": answer.comment,
                "answered_at": answer.answered_at}

    def _entries(self, cfg: ModConfig, state: str) -> list[BoardEntry | BoardError]:
        try:
            return self._registry.entries(cfg, state)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _table(self, listed: list[BoardEntry | BoardError]) -> Table:
        entries = [item for item in listed if isinstance(item, BoardEntry)]
        failures = [item for item in listed if isinstance(item, BoardError)]
        rows = [self._row(entry) for entry in self._sorter.sort(entries)]
        rows.extend(self._error_row(failure) for failure in failures)
        return self._table_builder.build(rows)

    def _row(self, entry: BoardEntry) -> dict[str, object]:
        board = entry.board
        return {"id": board.id, "title": board.title, "raised_by": board.raised_by,
                "created": board.created, "tags": self._row_tags(board),
                "blocking": self._blocking.is_blocking(entry)}

    def _row_tags(self, board: Board) -> list[str]:
        stale = self._permanent.stale_note(board, time.time())
        return [*board.tags, "stale"] if stale else list(board.tags)

    def _version(self, path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return 0

    def _error_row(self, failure: BoardError) -> dict[str, object]:
        return {"id": failure.folder.name, "error": failure.reason}

    def _item(self, name: str, board: Board, item: BoardItem) -> dict[str, object]:
        version = self._version(board.folder / item.file)
        return {"file": item.file, "caption": item.caption, "group": item.group,
                "url": f"/api/mods/{name}/boards/{board.id}/items/{item.file}?v={version}",
                "kind": self._kinds.detect(Path(item.file))}

    def _question(self, question: Question) -> dict[str, object]:
        return {"id": question.id, "type": question.type, "prompt": question.prompt,
                "options": [{"id": option.id, "label": option.label, "item": option.item}
                            for option in question.options],
                "default": question.default, "suggestion": question.suggestion,
                "blocking": question.blocking, "affects": list(question.affects)}
