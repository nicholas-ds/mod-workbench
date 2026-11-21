"""Move a board folder between the open and done states."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from workbench.board_repository import DONE_STATE, OPEN_STATE
from workbench.board_types import Board, BoardError
from workbench.permanent_board import PermanentBoardRule


class BoardLifecycle:
    """Close a board into done and reopen it into open."""

    def __init__(self, rule: PermanentBoardRule | None = None) -> None:
        self._rule = rule if rule is not None else PermanentBoardRule()

    def close(self, board: Board) -> Board:
        if self._rule.is_permanent(board):
            raise BoardError(board.folder, "this board is permanent and cannot be closed")
        return self._move(board, DONE_STATE)

    def reopen(self, board: Board) -> Board:
        return self._move(board, OPEN_STATE)

    def _move(self, board: Board, state: str) -> Board:
        target = self._target_folder(board.folder, state)
        if target.exists():
            raise BoardError(board.folder, f"target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        board.folder.rename(target)
        return replace(board, folder=target)

    def _target_folder(self, folder: Path, state: str) -> Path:
        return folder.parent.parent / state / folder.name
