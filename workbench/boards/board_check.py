"""Check one board folder and report each problem as one line."""

from __future__ import annotations

from pathlib import Path

from workbench.boards.board_repository import BoardRepository
from workbench.boards.board_types import Board, BoardError
from workbench.boards.image_framing import ImageFramingChecker

BASE_STYLE_MARKER = "workbench-base-style"
STATUS_BOARD_ID = "mod-status"
CHAT_PREFIX = "chat-"


class BoardValidator:
    """Check one board folder against the board model and its item files."""

    def __init__(self, repository: BoardRepository, status_dir: Path | None = None,
                 mod_name: str | None = None) -> None:
        self._repository = repository
        self._status_dir = status_dir
        self._mod_name = mod_name
        self._framing_checker = ImageFramingChecker()

    def check(self, folder: Path) -> tuple[str, ...]:
        try:
            board = self._repository.load(folder)
        except BoardError as exc:
            return (self._error_line(exc),)
        return (self._missing_item_lines(board) + self._unstyled_html_lines(board)
                + self._off_center_image_lines(board)
                + self._wrong_status_chat_lines(board))

    def _error_line(self, exc: BoardError) -> str:
        return f"{exc.folder.name}: {exc.reason}"

    def _missing_item_lines(self, board: Board) -> tuple[str, ...]:
        return tuple(
            f"{board.id}: item file not found: {item.file}"
            for item in board.items
            if not (board.folder / item.file).is_file()
        )

    def _unstyled_html_lines(self, board: Board) -> tuple[str, ...]:
        return tuple(
            f"{board.id}: {item.file} lacks the clay base style marker. "
            "Copy docs/board-html-template.html."
            for item in board.items
            if item.file.endswith(".html") and (board.folder / item.file).is_file()
            and BASE_STYLE_MARKER not in (board.folder / item.file).read_text(encoding="utf-8")
        )

    def _off_center_image_lines(self, board: Board) -> tuple[str, ...]:
        return tuple(
            f"{board.id}: {item.file}: {problem}"
            for item in board.items
            if item.file.endswith(".png") and (board.folder / item.file).is_file()
            for problem in self._framing_checker.problems(board.folder / item.file)
        )

    def _wrong_status_chat_lines(self, board: Board) -> tuple[str, ...]:
        if board.id != STATUS_BOARD_ID or self._mod_name is None:
            return ()
        expected = f"{CHAT_PREFIX}{self._mod_name}"
        if board.raised_by == expected:
            return ()
        return (f"{board.id}: raised_by is '{board.raised_by}', expected '{expected}'. "
                "Notes on this board go to the wrong chat.",)
