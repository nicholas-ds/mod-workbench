"""Resolve mods, boards and entries against the repos found in the roots."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from workbench.answer_store import AnswerStore
from workbench.board_repository import DONE_STATE, OPEN_STATE, BoardRepository
from workbench.board_types import Board, BoardEntry, BoardError
from workbench.config import ModConfig, ModDiscovery, ModError


class ModRegistry:
    """Resolve mods, boards and entries against the repos found in the roots."""

    def __init__(self, discovery: ModDiscovery, roots: list[Path],
                 boards: BoardRepository, answers: AnswerStore) -> None:
        self._discovery, self._roots = discovery, roots
        self._boards, self._answers = boards, answers

    def all(self) -> list[ModConfig | ModError]:
        return self._discovery.discover(self._roots)

    def require(self, name: str) -> ModConfig:
        for result in self.all():
            if isinstance(result, ModConfig) and result.name == name:
                return result
        raise HTTPException(status_code=404, detail=f"unknown mod: {name}")

    def open_count(self, cfg: ModConfig) -> int:
        return sum(isinstance(result, BoardEntry) for result in self.entries(cfg, OPEN_STATE))

    def entries(self, cfg: ModConfig, state: str) -> list[BoardEntry | BoardError]:
        listed = self._boards.list_boards(cfg.boards, state)
        return [self._entry(result) for result in listed]

    def require_entry(self, cfg: ModConfig, board_id: str) -> BoardEntry:
        for state in (OPEN_STATE, DONE_STATE):
            found = self._entry_in(cfg, state, board_id)
            if found is not None:
                return found
        raise HTTPException(status_code=404, detail=f"unknown board: {board_id}")

    def _entry_in(self, cfg: ModConfig, state: str, board_id: str) -> BoardEntry | None:
        for entry in self.entries(cfg, state):
            if isinstance(entry, BoardEntry) and entry.board.id == board_id:
                return entry
        return None

    def _entry(self, result: Board | BoardError) -> BoardEntry | BoardError:
        if isinstance(result, BoardError):
            return result
        return self._entry_with_answers(result)

    def _entry_with_answers(self, board: Board) -> BoardEntry | BoardError:
        try:
            answers = self._answers.read(board.folder)
        except BoardError as exc:
            return BoardError(board.folder, exc.reason)
        return BoardEntry(board=board, answers=answers)
